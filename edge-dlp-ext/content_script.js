// content_script.js
// Lightweight prototype: attach to inputs/contenteditable, run quick regex detection,
// on submit escalate to native for heavier checks.

const SENSITIVE_PATTERNS = [
  // regex patterns for prototype (API keys, JWTs, SSN, emails)
  {type: 'API_KEY', re: /(?:api[_-]?key|secret|sk_live)[\s:=]*[A-Za-z0-9\-_]{20,}/ig},
  {type: 'EMAIL', re: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}/ig},
  {type: 'SSN', re: /\b\d{3}-\d{2}-\d{4}\b/g},
  {type: 'JWT', re: /\beyJ[0-9A-Za-z\-_]+\.[0-9A-Za-z\-_]+\.[0-9A-Za-z\-_]+\b/g}
];

function detectRegex(text) {
  const findings = [];
  for (const p of SENSITIVE_PATTERNS) {
    let m;
    while ((m = p.re.exec(text)) !== null) {
      findings.push({type: p.type, match: m[0], index: m.index});
    }
  }
  return findings;
}

function redactText(text, findings) {
  // simple replacement; for production use tokenization or reversible mapping
  let out = text;
  // sort by index desc so replacements don't shift
  findings.sort((a,b) => b.index - a.index);
  for (const f of findings) {
    const start = f.index;
    const end = start + f.match.length;
    out = out.slice(0, start) + '[REDACTED:' + f.type + ']' + out.slice(end);
  }
  return out;
}

function attachEditor(editor) {
  if (!editor || editor.__edgeAttached) return;
  editor.__edgeAttached = true;

  // helper to get/set text
  const getText = () => editor.isContentEditable ? editor.innerText : editor.value || '';
  const setText = (t) => { if (editor.isContentEditable) editor.innerText = t; else editor.value = t; };

  // on paste: immediately scan pasted content and replace if high-risk
  editor.addEventListener('paste', async (ev) => {
    const pasted = (ev.clipboardData || window.clipboardData).getData('text');
    const findings = detectRegex(pasted);
    if (findings.length) {
      ev.preventDefault();
      const red = redactText(pasted, findings);
      insertTextAtCursor(editor, red);
      showInlineNotice(editor, 'Pasted content contained sensitive data and was redacted.');
    }
  });

  // on Enter (send) - check and escalate if needed
  editor.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      const text = getText();
      const localFindings = detectRegex(text);
      if (localFindings.length) {
        // read policy
        const p = await chrome.storage.local.get('policyMode');
        const mode = p.policyMode || 'warn';
        if (mode === 'auto_redact') {
          e.preventDefault();
          setText(redactText(text, localFindings));
          showInlineNotice(editor, 'Message auto-redacted per policy.');
          return;
        } else if (mode === 'block') {
          e.preventDefault();
          showInlineNotice(editor, 'Message blocked per policy (sensitive data).');
          return;
        } else {
          // warn mode: escalate to native for verification
        }
      }
      // escalate to native for deep checks regardless to demo the flow
      const resp = await escalateToNative(text);
      if (resp && resp.action === 'replace') {
        e.preventDefault();
        setText(resp.replacement);
        showInlineNotice(editor, 'Content replaced by native DLP host.');
      } else if (resp && resp.action === 'block') {
        e.preventDefault();
        showInlineNotice(editor, 'Send blocked by native DLP host.');
      }
      // else proceed
    }
  });

  // attach light highlighting on input (optional)
  editor.addEventListener('input', debounce(() => {
    const text = getText();
    const findings = detectRegex(text);
    highlightLocal(editor, findings);
  }, 250));
}

// Utilities
function insertTextAtCursor(el, text) {
  if (el.isContentEditable) {
    const sel = window.getSelection();
    if (!sel.rangeCount) return;
    const range = sel.getRangeAt(0);
    range.deleteContents();
    range.insertNode(document.createTextNode(text));
    range.collapse(false);
  } else {
    const start = el.selectionStart || 0;
    const end = el.selectionEnd || 0;
    const val = el.value;
    el.value = val.slice(0,start) + text + val.slice(end);
    el.selectionStart = el.selectionEnd = start + text.length;
  }
}

function showInlineNotice(editor, text) {
  // small transient UI
  const n = document.createElement('div');
  n.textContent = text;
  n.style.position = 'absolute';
  n.style.background = '#222';
  n.style.color = 'white';
  n.style.padding = '6px';
  n.style.borderRadius = '6px';
  n.style.zIndex = 99999;
  document.body.appendChild(n);
  const rect = editor.getBoundingClientRect();
  n.style.left = (rect.left + window.scrollX) + 'px';
  n.style.top = (rect.top + window.scrollY - 36) + 'px';
  setTimeout(()=>n.remove(), 4000);
}

function highlightLocal(editor, findings) {
  // trivial: set red border if anything found
  if (findings.length) editor.style.outline = '2px solid rgba(255,0,0,0.5)';
  else editor.style.outline = '';
}

function debounce(fn, d) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(()=>fn(...args), d); };
}

// escalate to native
function escalateToNative(text) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({type: 'escalate-to-native', text}, (resp) => {
      // response might be 'sent' - actual verdicts will be delivered via chrome.runtime.onMessage listener
      // wait for the reply from native with tabId match
      const onNative = (msg, sender) => {
        if (msg && msg.type === 'native-verdict' && msg.payload && msg.payload.tabId === (window.tabId || null)) {
          chrome.runtime.onMessage.removeListener(onNative);
          resolve(msg.payload);
        }
      };
      // listen for direct response
      chrome.runtime.onMessage.addListener(onNative);
      // fallback timeout
      setTimeout(()=>resolve(null), 1500);
    });
  });
}

// we need to inject and attach to dynamic editors
const mo = new MutationObserver((mutations)=>{
  for (const m of mutations) {
    m.addedNodes.forEach(node=>{
      if (node.nodeType !== 1) return;
      if (node.matches && (node.matches('input') || node.matches('textarea') || node.isContentEditable)) attachEditor(node);
      node.querySelectorAll && node.querySelectorAll('[contenteditable="true"], input, textarea').forEach(attachEditor);
    });
  }
});
mo.observe(document.body, {childList:true, subtree:true});

// initial attach for existing editors
document.querySelectorAll('input, textarea, [contenteditable="true"]').forEach(attachEditor);

// attempt to set a pseudo tabId for native mapping (some browsers don't provide tab id to content script)
chrome.runtime.sendMessage({type: 'get-tab-id'}, (resp) => { if (resp && resp.tabId) window.tabId = resp.tabId; });
