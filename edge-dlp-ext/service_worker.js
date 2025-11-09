// service_worker.js - handles native messaging (connect only when needed)
const NATIVE_HOST = "com.edge_dlp.nativehost";

console.log('Service worker loaded');

// Load risky domains
let riskyDomains = [];
async function loadRiskyDomains() {
  try {
    const response = await fetch(chrome.runtime.getURL('risky_domains.json'));
    const data = await response.json();
    riskyDomains = data.high_risk_domains || [];
    console.log('[ServiceWorker] Loaded risky domains:', riskyDomains.length);
  } catch (e) {
    console.error('[ServiceWorker] Failed to load risky domains:', e);
    // Fallback to hardcoded list
    riskyDomains = [
      'chat.openai.com',
      'chatgpt.com',
      'claude.ai',
      'gemini.google.com',
      'copilot.microsoft.com',
      'bard.google.com',
      'pastebin.com',
      'paste.ee',
      'dpaste.com',
      'hastebin.com',
      'github.com',
      'gist.github.com',
      'stackoverflow.com',
      'discord.com',
      'slack.com',
      'reddit.com',
      'twitter.com',
      'x.com',
      'facebook.com',
      'linkedin.com',
      'medium.com',
      'notion.so'
    ];
  }
}

// Check if a URL is risky
function isRiskyDomain(url) {
  try {
    const hostname = new URL(url).hostname;
    return riskyDomains.some(domain => 
      hostname === domain || hostname.endsWith('.' + domain)
    );
  } catch (e) {
    return false;
  }
}

// Notify clipboard monitor about domain status
function notifyClipboardMonitor(isRisky, hostname) {
  const payload = {
    type: 'notify-clipboard-monitor',
    isRiskyDomain: isRisky,
    hostname: hostname || ''
  };
  
  chrome.runtime.sendNativeMessage(NATIVE_HOST, payload, (response) => {
    if (chrome.runtime.lastError) {
      console.error('[ServiceWorker] Error notifying clipboard monitor:', chrome.runtime.lastError);
    } else {
      console.log('[ServiceWorker] Clipboard monitor notified:', response);
    }
  });
}

// Keep service worker alive by listening to events
// In Manifest V3, service workers can be terminated when idle
// This ensures it stays active when needed
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed/updated');
  loadRiskyDomains();
});

chrome.runtime.onStartup.addListener(() => {
  console.log('Browser started');
  loadRiskyDomains();
});

// Load risky domains on startup
loadRiskyDomains();

// Listen for tab activation (when user switches tabs)
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab && tab.url) {
      const hostname = new URL(tab.url).hostname;
      const isRisky = isRiskyDomain(tab.url);
      console.log('[ServiceWorker] Tab activated:', hostname, 'risky:', isRisky);
      notifyClipboardMonitor(isRisky, hostname);
    }
  } catch (e) {
    // Tab might be chrome:// or invalid URL
    console.log('[ServiceWorker] Could not check tab URL:', e.message);
  }
});

// Listen for tab updates (when URL changes in a tab)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Only notify when URL changes and tab is active
  if (changeInfo.status === 'complete' && changeInfo.url && tab.active) {
    try {
      const hostname = new URL(changeInfo.url).hostname;
      const isRisky = isRiskyDomain(changeInfo.url);
      console.log('[ServiceWorker] Tab URL updated:', hostname, 'risky:', isRisky);
      notifyClipboardMonitor(isRisky, hostname);
    } catch (e) {
      // Invalid URL
      console.log('[ServiceWorker] Could not check updated URL:', e.message);
    }
  }
});

  // Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Received message:', message.type);
  
  // Handle tab ID request
  if (message && message.type === 'get-tab-id') {
    sendResponse({tabId: sender.tab ? sender.tab.id : null});
    return true;
  }
  
  // Handle file obfuscation
  if (message && message.type === 'obfuscate-file') {
    console.log('[ServiceWorker] Obfuscating file:', message.fileName, message.fileType);
    
    const payload = {
      type: 'obfuscate-file',
      content: message.content || '',
      fileType: message.fileType || '',
      fileName: message.fileName || 'file'
    };
    
    chrome.runtime.sendNativeMessage(NATIVE_HOST, payload, (response) => {
      if (chrome.runtime.lastError) {
        console.error('[ServiceWorker] Error obfuscating file:', chrome.runtime.lastError);
        sendResponse({obfuscated: null, success: false, error: chrome.runtime.lastError.message});
      } else {
        console.log('[ServiceWorker] File obfuscated:', response);
        sendResponse(response || {obfuscated: null, success: false});
      }
    });
    
    return true; // Will respond asynchronously
  }
  
  // Handle clipboard monitor notification
  if (message && message.type === 'notify-clipboard-monitor') {
    console.log('[ServiceWorker] Notifying clipboard monitor:', message.isRiskyDomain, message.hostname);
    
    const payload = {
      type: 'notify-clipboard-monitor',
      isRiskyDomain: message.isRiskyDomain || false,
      hostname: message.hostname || ''
    };
    
    chrome.runtime.sendNativeMessage(NATIVE_HOST, payload, (response) => {
      if (chrome.runtime.lastError) {
        console.error('[ServiceWorker] Error notifying clipboard monitor:', chrome.runtime.lastError);
      } else {
        console.log('[ServiceWorker] Clipboard monitor notified:', response);
      }
    });
    
    sendResponse({status: 'sent'});
    return true;
  }
  
  if (message && message.type === 'escalate-to-native') {
    console.log('[ServiceWorker] Escalating to native:', message.text ? message.text.substring(0, 50) : 'no text');
    
    // Store requestId from message to forward it back with response
    const requestId = message.requestId || null;
    
    const payload = {
      tabId: sender.tab ? sender.tab.id : null,
      text: message.text || '',
      context: message.context || {}
    };
    
    console.log('[ServiceWorker] Payload:', payload);
    console.log('[ServiceWorker] Request ID:', requestId);
    console.log('[ServiceWorker] Native host name:', NATIVE_HOST);
    
    // Use sendNativeMessage instead of connectNative for one-off messages
    console.log('[ServiceWorker] Sending to native host...');
    chrome.runtime.sendNativeMessage(NATIVE_HOST, payload, (response) => {
      if (chrome.runtime.lastError) {
        const errorMsg = chrome.runtime.lastError.message;
        console.error('[ServiceWorker] Native message error:', errorMsg);
        console.error('[ServiceWorker] Full error:', chrome.runtime.lastError);
        console.error('[ServiceWorker] Error details - code:', chrome.runtime.lastError.code);
        // Try to send error to content script with requestId
        if (sender.tab && sender.tab.id) {
          chrome.tabs.sendMessage(sender.tab.id, {
            type: 'native-verdict',
            payload: {action: 'allow', error: errorMsg},
            requestId: requestId // Include requestId so content script can match it
          }).catch(e => {
            // Ignore "Receiving end does not exist" - happens when extension is reloaded
            if (!e.message || !e.message.includes('Receiving end does not exist')) {
              console.error('[ServiceWorker] Failed to send error to content script:', e);
            }
          });
        }
        sendResponse({status: 'error', error: errorMsg});
      } else {
        console.log('[ServiceWorker] Native response received:', response);
        // Send response back to content script via chrome.tabs.sendMessage
        // Check if tab still exists before sending
        if (response && sender.tab && sender.tab.id) {
          console.log('[ServiceWorker] Sending response to content script, tab ID:', sender.tab.id);
          
          // Check if tab still exists
          chrome.tabs.get(sender.tab.id).then((tab) => {
            if (tab && tab.status === 'complete') {
              const messageToSend = {
                type: 'native-verdict',
                payload: response,
                requestId: requestId // Forward request ID back to content script
              };
              console.log('[ServiceWorker] Sending message to content script:', messageToSend);
              chrome.tabs.sendMessage(sender.tab.id, messageToSend).then(() => {
                console.log('[ServiceWorker] Response sent to content script successfully');
              }).catch(e => {
                // Content script might have timed out or extension was reloaded - this is expected
                // Suppress the error to avoid console noise
                if (e.message && e.message.includes('Receiving end does not exist')) {
                  // This happens when extension is reloaded or content script timed out - ignore it
                  // Don't log anything to avoid console noise
                } else {
                  console.warn('[ServiceWorker] Could not send response to content script:', e.message);
                }
              });
            } else {
              console.warn('[ServiceWorker] Tab not ready, status:', tab ? tab.status : 'not found');
            }
          }).catch(e => {
            console.warn('[ServiceWorker] Tab no longer exists:', e.message);
          });
        } else {
          console.warn('[ServiceWorker] Cannot send response - no tab ID:', sender.tab);
        }
        sendResponse({status: 'success', response});
      }
    });
    
    return true; // Will respond asynchronously
  }
});

console.log('Service worker ready, waiting for messages...');
