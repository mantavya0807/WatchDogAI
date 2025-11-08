// service_worker.js - handles native messaging (connect only when needed)
const NATIVE_HOST = "com.edge_dlp.nativehost";

console.log('Service worker loaded');

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Received message:', message.type);
  
  // Handle tab ID request
  if (message && message.type === 'get-tab-id') {
    sendResponse({tabId: sender.tab ? sender.tab.id : null});
    return true;
  }
  
  if (message && message.type === 'escalate-to-native') {
    console.log('Escalating to native:', message.text.substring(0, 50));
    
    const payload = {
      tabId: sender.tab ? sender.tab.id : null,
      text: message.text,
      context: message.context || {}
    };
    
    // Use sendNativeMessage instead of connectNative for one-off messages
    console.log('Sending to native host...');
    chrome.runtime.sendNativeMessage(NATIVE_HOST, payload, (response) => {
      if (chrome.runtime.lastError) {
        console.error('Native message error:', chrome.runtime.lastError.message);
        sendResponse({status: 'error', error: chrome.runtime.lastError.message});
      } else {
        console.log('Native response:', response);
        // Send response back to content script
        if (response && sender.tab) {
          chrome.tabs.sendMessage(sender.tab.id, {
            type: 'native-verdict',
            payload: response
          });
        }
        sendResponse({status: 'success', response});
      }
    });
    
    return true; // Will respond asynchronously
  }
});

console.log('Service worker ready, waiting for messages...');
