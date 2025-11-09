// content_script.js
// Real-time PII protection for risky websites
// Only activates on high-risk domains (ChatGPT, etc.)

let isRiskyDomain = false;
let riskyDomains = [];
let typingTimeout = null;
let lastTypedText = '';

// Load risky domains
async function loadRiskyDomains() {
  try {
    const response = await fetch(chrome.runtime.getURL('risky_domains.json'));
    const data = await response.json();
    riskyDomains = data.high_risk_domains || [];
    checkCurrentDomain();
  } catch (e) {
    console.error('Failed to load risky domains:', e);
    // Fallback to hardcoded list
    riskyDomains = [
      'chat.openai.com',
      'chatgpt.com',
      'claude.ai',
      'gemini.google.com',
      'copilot.microsoft.com'
    ];
    checkCurrentDomain();
  }
}

let hasNotifiedInitialStatus = false;

function checkCurrentDomain() {
  const hostname = window.location.hostname;
  const wasRisky = isRiskyDomain;
  
  console.log('[EdgeDLP] Checking domain:', hostname);
  console.log('[EdgeDLP] Risky domains list:', riskyDomains);
  isRiskyDomain = riskyDomains.some(domain => 
    hostname === domain || hostname.endsWith('.' + domain)
  );
  
  // Always notify on initial load, or if status changed
  if (!hasNotifiedInitialStatus || isRiskyDomain !== wasRisky) {
    notifySystemMonitor(isRiskyDomain, hostname);
    hasNotifiedInitialStatus = true;
  }
  
  if (isRiskyDomain) {
    console.log('[EdgeDLP] ✓ Active on risky domain:', hostname);
    attachToAllEditors();
  } else {
    console.log('[EdgeDLP] ✗ Not active on:', hostname);
  }
}

// Notify system clipboard monitor about risky domain status
function notifySystemMonitor(isRisky, hostname) {
  chrome.runtime.sendMessage({
    type: 'notify-clipboard-monitor',
    isRiskyDomain: isRisky,
    hostname: hostname
  }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('[EdgeDLP] Error notifying system monitor:', chrome.runtime.lastError);
    } else {
      console.log('[EdgeDLP] Notified system monitor: risky =', isRisky, 'for', hostname);
    }
  });
}

// Real-time typing detection with debounce
function handleTyping(editor) {
  if (!isRiskyDomain) return;
  
  clearTimeout(typingTimeout);
  
  typingTimeout = setTimeout(async () => {
    const text = getText(editor);
    if (text === lastTypedText) return;
    lastTypedText = text;
    
    if (text.length < 10) return; // Skip short text
    
    // Quick regex check first
    const quickFindings = detectRegex(text);
    console.log('[EdgeDLP] Quick regex check found:', quickFindings.length, 'findings');
    if (quickFindings.length > 0) {
      console.log('[EdgeDLP] Escalating to native host...');
      // Escalate to native for full obfuscation
      const response = await escalateToNative(text);
      console.log('[EdgeDLP] Native response:', response);
      if (response && response.action === 'replace' && response.replacement) {
        console.log('[EdgeDLP] Replacing text with obfuscated version');
        replaceTextRealTime(editor, text, response.replacement);
      } else {
        console.log('[EdgeDLP] No replacement from native host');
      }
    }
  }, 500); // 500ms debounce
}

// Real-time text replacement (preserves cursor position)
function replaceTextRealTime(editor, originalText, obfuscatedText) {
  if (editor.isContentEditable) {
    const selection = window.getSelection();
    const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
    const cursorOffset = range ? range.startOffset : 0;
    
    editor.innerText = obfuscatedText;
    
    // Try to restore cursor position
    if (range) {
      try {
        const textNode = editor.firstChild;
        if (textNode && textNode.nodeType === Node.TEXT_NODE) {
          const newOffset = Math.min(cursorOffset, textNode.textContent.length);
          range.setStart(textNode, newOffset);
          range.setEnd(textNode, newOffset);
          selection.removeAllRanges();
          selection.addRange(range);
        }
      } catch (e) {
        // Ignore cursor restoration errors
      }
    }
  } else {
    const cursorPos = editor.selectionStart || 0;
    editor.value = obfuscatedText;
    // Try to restore cursor
    setTimeout(() => {
      editor.selectionStart = Math.min(cursorPos, obfuscatedText.length);
      editor.selectionEnd = editor.selectionStart;
    }, 0);
  }
  
  showInlineNotice(editor, 'PII detected and obfuscated');
}

// Clipboard handling removed - system monitor handles it
// Extension only notifies system monitor about risky domain status

// Quick regex detection (lightweight)
const SENSITIVE_PATTERNS = [
  {type: 'API_KEY', re: /(?:api[_-]?key|secret|sk_live|sk_test)[\s:=]*[A-Za-z0-9\-_]{20,}/ig},
  {type: 'EMAIL', re: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}/ig},
  {type: 'SSN', re: /\b\d{3}-\d{2}-\d{4}\b/g},
  {type: 'JWT', re: /\beyJ[0-9A-Za-z\-_]+\.[0-9A-Za-z\-_]+\.[0-9A-Za-z\-_]+\b/g},
  {type: 'PHONE', re: /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g},
  {type: 'CREDIT_CARD', re: /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/g}
];

function detectRegex(text) {
  const findings = [];
  for (const p of SENSITIVE_PATTERNS) {
    let m;
    const regex = new RegExp(p.re.source, p.re.flags);
    while ((m = regex.exec(text)) !== null) {
      findings.push({type: p.type, match: m[0], index: m.index, start: m.index, end: m.index + m[0].length});
    }
  }
  return findings;
}

function redactText(text, findings) {
  let out = text;
  findings.sort((a,b) => b.index - a.index);
  for (const f of findings) {
    out = out.slice(0, f.start) + '[REDACTED:' + f.type + ']' + out.slice(f.end);
  }
  return out;
}

function getText(editor) {
  return editor.isContentEditable ? editor.innerText : editor.value || '';
}

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
  const n = document.createElement('div');
  n.textContent = text;
  n.style.cssText = 'position:absolute;background:#222;color:white;padding:6px;border-radius:6px;z-index:99999;font-size:12px;';
  document.body.appendChild(n);
  const rect = editor.getBoundingClientRect();
  n.style.left = (rect.left + window.scrollX) + 'px';
  n.style.top = (rect.top + window.scrollY - 36) + 'px';
  setTimeout(() => n.remove(), 3000);
}

function attachEditor(editor) {
  if (!editor || editor.__edgeAttached) return;
  editor.__edgeAttached = true;
  console.log('[EdgeDLP] Attached to editor:', editor.tagName, editor.className);

  // Real-time typing detection
  editor.addEventListener('input', () => {
    if (isRiskyDomain) {
      console.log('[EdgeDLP] Input detected on risky domain');
      handleTyping(editor);
    }
  });

  // Copy/paste handling removed - system clipboard monitor handles it globally

  // On Enter/submit - final check
  editor.addEventListener('keydown', async (e) => {
    if (!isRiskyDomain) return;
    
    if (e.key === 'Enter' && !e.shiftKey) {
      const text = getText(editor);
      if (text.length < 10) return;
      
      const response = await escalateToNative(text);
      if (response && response.action === 'replace' && response.replacement) {
        e.preventDefault();
        const setText = (t) => { 
          if (editor.isContentEditable) editor.innerText = t; 
          else editor.value = t; 
        };
        setText(response.replacement);
        showInlineNotice(editor, 'Content obfuscated before sending');
      } else if (response && response.action === 'block') {
        e.preventDefault();
        showInlineNotice(editor, 'Send blocked - sensitive data detected');
      }
    }
  });
}

function attachToAllEditors() {
  // Attach to existing editors
  document.querySelectorAll('input, textarea, [contenteditable="true"]').forEach(attachEditor);
  
  // Watch for new editors
  const mo = new MutationObserver((mutations) => {
    for (const m of mutations) {
      m.addedNodes.forEach(node => {
        if (node.nodeType !== 1) return;
        if (node.matches && (node.matches('input') || node.matches('textarea') || node.isContentEditable)) {
          attachEditor(node);
        }
        if (node.querySelectorAll) {
          node.querySelectorAll('[contenteditable="true"], input, textarea').forEach(attachEditor);
        }
      });
    }
  });
  mo.observe(document.body, {childList: true, subtree: true});
}

// Persistent message listener for native responses
let pendingRequests = new Map();
let requestIdCounter = 0;

// Set up a single persistent listener for all native responses
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // Log all messages for debugging
  if (msg && msg.type === 'native-verdict') {
    console.log('[EdgeDLP] Received native-verdict message:', msg);
    console.log('[EdgeDLP] Message requestId:', msg.requestId);
    console.log('[EdgeDLP] Current pending requests:', Array.from(pendingRequests.keys()));
  }
  
  if (msg && msg.type === 'native-verdict' && msg.payload && msg.requestId !== undefined) {
    console.log('[EdgeDLP] Processing native-verdict for request ID:', msg.requestId);
    const resolver = pendingRequests.get(msg.requestId);
    if (resolver) {
      console.log('[EdgeDLP] Found resolver for request ID:', msg.requestId, '- calling it');
      // Don't delete here - let the resolver handle cleanup
      resolver(msg.payload);
    } else {
      console.warn('[EdgeDLP] No resolver found for request ID:', msg.requestId);
      console.warn('[EdgeDLP] Pending requests:', Array.from(pendingRequests.keys()));
      console.warn('[EdgeDLP] This likely means the timeout fired before the message arrived');
    }
    // Don't return true - we're not using sendResponse() for async response
    // The message is handled synchronously by resolving the promise
    return false;
  }
  return false; // Not our message type
});

// Escalate to native host for full obfuscation
function escalateToNative(text) {
  return new Promise((resolve) => {
    // Check if extension context is still valid
    if (!chrome.runtime || !chrome.runtime.id) {
      console.error('[EdgeDLP] Extension context invalidated - extension was reloaded');
      resolve(null);
      return;
    }
    
    // Generate unique request ID
    const requestId = ++requestIdCounter;
    const startTime = Date.now();
    console.log('[EdgeDLP] Sending message to service worker (request ID:', requestId, ') at', startTime);
    
    // Track if we've already resolved
    let resolved = false;
    
    // Store resolver for this request
    pendingRequests.set(requestId, (payload) => {
      const elapsed = Date.now() - startTime;
      console.log('[EdgeDLP] Resolver called for request ID:', requestId, 'after', elapsed, 'ms');
      if (!resolved) {
        resolved = true;
        clearTimeout(timeout);
        if (pendingRequests.has(requestId)) {
          pendingRequests.delete(requestId);
        }
        console.log('[EdgeDLP] Resolving promise with payload:', payload);
        resolve(payload);
      } else {
        console.warn('[EdgeDLP] Resolver called multiple times for request ID:', requestId);
      }
    });
    
    // Set timeout to clean up - increased to 30 seconds to account for transformer model initialization
    const timeout = setTimeout(() => {
      const elapsed = Date.now() - startTime;
      console.log('[EdgeDLP] Timeout fired for request ID:', requestId, 'after', elapsed, 'ms');
      if (pendingRequests.has(requestId)) {
        pendingRequests.delete(requestId);
        console.log('[EdgeDLP] Timeout waiting for native response (request ID:', requestId, ') - removing resolver');
        if (!resolved) {
          resolved = true;
          resolve(null);
        }
      } else {
        console.log('[EdgeDLP] Timeout fired but resolver already removed for request ID:', requestId);
      }
    }, 30000); // 30 seconds - enough for transformer model initialization (~15 secs) + processing + network delay
    
    try {
      chrome.runtime.sendMessage({
        type: 'escalate-to-native', 
        text,
        requestId: requestId
      }, (resp) => {
        if (chrome.runtime.lastError) {
          const errorMsg = chrome.runtime.lastError.message;
          console.error('[EdgeDLP] Error sending message:', errorMsg);
          
          // If context invalidated, extension was reloaded - user needs to refresh page
          if (errorMsg.includes('Extension context invalidated') || 
              errorMsg.includes('message port closed')) {
            console.warn('[EdgeDLP] Extension was reloaded. Please refresh this page.');
          }
          
          if (pendingRequests.has(requestId)) {
            clearTimeout(timeout);
            pendingRequests.delete(requestId);
            resolve(null);
          }
          return;
        }
        console.log('[EdgeDLP] Service worker response:', resp);
        // Don't resolve here - wait for the native-verdict message
        // The response is just an acknowledgment
      });
    } catch (e) {
      console.error('[EdgeDLP] Exception sending message:', e);
      if (pendingRequests.has(requestId)) {
        clearTimeout(timeout);
        pendingRequests.delete(requestId);
        resolve(null);
      }
    }
  });
}

// Global copy/paste handling removed - system clipboard monitor handles it

// Initialize
console.log('[EdgeDLP] Content script loaded on:', window.location.hostname);
loadRiskyDomains();

// Get tab ID
chrome.runtime.sendMessage({type: 'get-tab-id'}, (resp) => {
  if (resp && resp.tabId) {
    window.tabId = resp.tabId;
    console.log('[EdgeDLP] Tab ID:', resp.tabId);
  }
});

// Re-check domain on navigation
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    console.log('[EdgeDLP] URL changed to:', url);
    checkCurrentDomain(); // This will notify system monitor if status changed
  }
}).observe(document, {subtree: true, childList: true});

// Notify on initial load
checkCurrentDomain();
