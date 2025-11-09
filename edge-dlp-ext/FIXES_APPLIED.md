# Fixes Applied for Extension Issues

## Issues Fixed

### 1. ✅ Extension Context Invalidated Error

**Problem:** 
- Error: "Extension context invalidated" when trying to send messages to service worker
- Happens when extension is reloaded while page is still open

**Fix:**
- Added check for `chrome.runtime.id` before sending messages
- Added try-catch block around `chrome.runtime.sendMessage`
- Added better error messages to guide user to refresh page

**Location:** `content_script.js` - `escalateToNative()` function

### 2. ✅ Service Worker Not Running

**Problem:**
- Service worker can be terminated when idle in Manifest V3
- Messages fail if service worker is not active

**Fix:**
- Added event listeners (`onInstalled`, `onStartup`) to keep service worker active
- These listeners ensure service worker stays alive when needed

**Location:** `service_worker.js` - Added event listeners at top

### 3. ✅ Native Host Import Error

**Problem:**
- Error: "No module named 'detectors'"
- Project root path calculation was wrong
- From `Extension/edge-dlp-ext/native_host.py`, going up 2 levels gets to `Extension/`, but we need `HackPrinceton/`

**Fix:**
- Fixed project root calculation to go up 3 levels (or check if parent is 'Extension' and go up one more)
- Added logging to show project root and Python path for debugging

**Location:** `native_host.py` - Project root calculation

### 4. ✅ Native Messaging Protocol Error

**Problem:**
- Error: "Message too large: 1702109819 bytes"
- Message length being read incorrectly
- Native messaging uses little-endian format, but wasn't explicitly specified

**Fix:**
- Changed `struct.pack('I', ...)` to `struct.pack('<I', ...)` for little-endian
- Changed `struct.unpack('I', ...)` to `struct.unpack('<I', ...)` for little-endian
- This ensures correct byte order for native messaging protocol

**Location:** `native_host.py` - `send_message()` and `read_message()` functions

## How to Test

1. **Reload Extension:**
   - Go to `edge://extensions/`
   - Click "Reload" on your extension
   - **Important:** Refresh the ChatGPT page after reloading

2. **Test on ChatGPT:**
   - Go to `https://chatgpt.com`
   - Open DevTools (F12) → Console tab
   - Type or paste an email: `test@example.com`
   - You should see:
     - `[EdgeDLP] Input detected on risky domain`
     - `[EdgeDLP] Quick regex check found: 1 findings`
     - `[EdgeDLP] Escalating to native host...`
     - `[EdgeDLP] Native verdict received: {...}`

3. **Check Native Host Log:**
   - Location: `Extension/edge-dlp-ext/native_host.log`
   - Should show:
     - "Project root: D:\Projects\HackPrinceton"
     - "Main obfuscator imported successfully"
     - "Processing text for tab..."
     - "PII detected via obfuscator: X items"

## Important Notes

### Service Worker Must Be Running

**Yes, the service worker file MUST be running for the extension to work.**

In Manifest V3:
- Service workers can be terminated when idle
- They restart automatically when needed
- But if they're not running, messages from content scripts will fail

**How to check if service worker is running:**
1. Go to `edge://extensions/`
2. Find your extension
3. Click "service worker" link (or "Inspect views: service worker")
4. Should open DevTools for service worker
5. Check console for "Service worker loaded" message

**If service worker is not running:**
- Reload the extension
- Refresh the page
- Check for errors in service worker console

### Extension Context Invalidated

This error means:
- The extension was reloaded while the page was still open
- The content script is still using the old extension context
- **Solution:** Refresh the page after reloading the extension

### Native Host Communication Flow

1. **Content Script** detects PII → sends message to **Service Worker**
2. **Service Worker** receives message → sends to **Native Host** via `chrome.runtime.sendNativeMessage()`
3. **Native Host** (Python script) processes text → sends response back
4. **Service Worker** receives response → sends to **Content Script**
5. **Content Script** receives response → replaces text in page

If any step fails, check:
- Service worker console (for step 1-2, 4-5)
- Native host log (for step 3)
- Browser console (for step 1, 5)

## Troubleshooting

### "Extension context invalidated" error
- **Fix:** Refresh the page after reloading extension

### "Native message error: Specified native messaging host not found"
- **Fix:** 
  1. Restart browser completely
  2. Reload extension
  3. Verify registry entry exists: `HKCU:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.edge_dlp.nativehost`

### "No module named 'detectors'"
- **Fix:** Project root path is now calculated correctly
- Check `native_host.log` for "Project root: ..." to verify

### "Message too large" error
- **Fix:** Native messaging protocol now uses little-endian format
- Should read messages correctly now

### Service worker not receiving messages
- **Fix:** Added event listeners to keep service worker active
- Reload extension and refresh page

## Next Steps

1. **Reload extension** in `edge://extensions/`
2. **Refresh ChatGPT page** (important!)
3. **Test typing/pasting** an email address
4. **Check console logs** for any errors
5. **Check native host log** for processing details

If still not working, check:
- Service worker console for errors
- Native host log for import/processing errors
- Registry entry for native host registration

