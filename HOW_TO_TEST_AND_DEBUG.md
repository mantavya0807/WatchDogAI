# How to Test and Debug the Extension

## Quick Testing Steps

### 1. Test Native Host Directly (Python Backend)

Test if the Python script works standalone:

```powershell
cd Extension/edge-dlp-ext
python test_native_host.py
```

**Expected output:**
```json
Response: {
  "tabId": 1,
  "action": "replace",
  "replacement": "my api_key is [REDACTED:API_KEY]",
  "findings": [...]
}
```

**If it fails:**
- Check Python is installed: `python --version`
- Check `native_host.py` exists and is readable
- Check `test_native_host.py` exists

### 2. Test Extension in Browser

**Load Extension:**
1. Open Edge/Chrome
2. Go to `edge://extensions/` or `chrome://extensions/`
3. Enable **Developer mode** (top-right toggle)
4. Click **Load unpacked**
5. Select folder: `Extension/edge-dlp-ext`
6. Extension should appear in list

**Test on a Webpage:**
1. Open any webpage with text input (Gmail, ChatGPT, any form)
2. Type: `My email is test@example.com and SSN is 123-45-6789`
3. Press Enter (or submit)
4. **Expected:** Text should be redacted to `[REDACTED:EMAIL]` and `[REDACTED:SSN]`

## Finding Errors

### Error Location 1: Service Worker Console

**How to access:**
1. Go to `edge://extensions/`
2. Find your extension in the list
3. Click the **"service worker"** link (or "Inspect views: service worker")
4. Console tab opens - this shows service worker errors

**What to look for:**
- `Service worker loaded` - Good sign
- `Native message error: ...` - Connection problem
- `Received message: escalate-to-native` - Messages are flowing
- `Native response: {...}` - Native host responded

### Error Location 2: Browser Console (Content Script)

**How to access:**
1. Open any webpage
2. Press `F12` to open DevTools
3. Go to **Console** tab
4. This shows content script errors and messages

**What to look for:**
- Extension messages about detection
- JavaScript errors from content_script.js
- Native messaging errors

### Error Location 3: Native Host Log File

**Where to find:**
- Windows: Check if `native_host.log` exists in extension folder
- Linux/Mac: `/tmp/native_host.log`

**How to view:**
```powershell
# Windows PowerShell
Get-Content Extension/edge-dlp-ext/native_host.log -Tail 50

# Or just open the file
notepad Extension/edge-dlp-ext/native_host.log
```

**What to look for:**
- `Native host starting...` - Script started
- `Received: {...}` - Message received from extension
- `Found X potential issues` - Detection working
- `Error reading message: ...` - Communication problem
- `Fatal error in main: ...` - Crash in Python script

### Error Location 4: Extension Errors Page

**How to access:**
1. Go to `edge://extensions/`
2. Find your extension
3. Look for red error badge or error message
4. Click "Errors" button if shown

## Common Errors and How to Fix

### Error: "Native messaging host not found"

**What it means:** Browser can't find the native host

**How to debug:**
1. Check registry entry exists:
   ```powershell
   Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.edge_dlp.nativehost"
   ```
2. Check `com.edge_dlp.nativehost.json` path is correct and absolute
3. Check Extension ID matches in `allowed_origins`

**Fix:**
- Register native host in registry (see setup instructions)
- Update `com.edge_dlp.nativehost.json` with correct paths
- Restart browser

### Error: "This native messaging host does not support the extension"

**What it means:** Extension ID mismatch

**How to debug:**
1. Get Extension ID from `edge://extensions/` page
2. Check `com.edge_dlp.nativehost.json`:
   ```json
   "allowed_origins": [
     "chrome-extension://YOUR_EXTENSION_ID_HERE/"
   ]
   ```

**Fix:**
- Update `allowed_origins` with correct Extension ID
- Reload extension

### Error: "Failed to read message" or "Incomplete message"

**What it means:** Communication protocol issue

**How to debug:**
1. Check native host log file
2. Check service worker console for message format errors
3. Test native host directly: `python test_native_host.py`

**Fix:**
- Verify message format matches expected structure
- Check Python script is reading/writing correctly
- Check for encoding issues

### Error: Content script not working

**What it means:** Extension not attaching to web pages

**How to debug:**
1. Check browser console (F12) for JavaScript errors
2. Check if content script is listed in manifest.json
3. Check permissions in manifest.json include `"<all_urls>"`

**Fix:**
- Reload extension
- Check manifest.json is valid JSON
- Verify content_script.js exists and has no syntax errors

## Testing Checklist

- [ ] Native host works standalone (`python test_native_host.py`)
- [ ] Extension loads without errors in `edge://extensions/`
- [ ] Service worker shows "ready" in console
- [ ] Content script attaches to text inputs on web pages
- [ ] Typing PII triggers detection
- [ ] Native host receives messages (check log file)
- [ ] Native host responds (check service worker console)
- [ ] Text gets redacted on webpage
- [ ] No errors in browser console (F12)
- [ ] No errors in service worker console

## Quick Debug Commands

```powershell
# Test native host
python Extension/edge-dlp-ext/test_native_host.py

# Check if native host is registered (Windows)
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.edge_dlp.nativehost"

# View native host log (if exists)
Get-Content Extension/edge-dlp-ext/native_host.log -Tail 20

# Check Python version
python --version

# Check if files exist
Test-Path Extension/edge-dlp-ext/native_host.py
Test-Path Extension/edge-dlp-ext/content_script.js
Test-Path Extension/edge-dlp-ext/service_worker.js
```

## What to Check When Something Doesn't Work

1. **Service Worker Console** - Are messages being sent?
2. **Native Host Log** - Is Python script receiving messages?
3. **Browser Console** - Are there JavaScript errors?
4. **Extension Errors Page** - Any manifest or permission errors?
5. **Test Native Host Directly** - Does Python script work standalone?

## Testing Different Scenarios

**Test Case 1: Email Detection**
- Input: `Contact me at test@example.com`
- Expected: `Contact me at [REDACTED:EMAIL]`

**Test Case 2: API Key Detection**
- Input: `My API key is sk_live_abc123def456ghi789`
- Expected: `My API key is [REDACTED:API_KEY]`

**Test Case 3: SSN Detection**
- Input: `SSN: 123-45-6789`
- Expected: `SSN: [REDACTED:SSN]`

**Test Case 4: Multiple PII**
- Input: `Email: test@example.com, SSN: 123-45-6789`
- Expected: Both should be redacted

**Test Case 5: No PII**
- Input: `This is just normal text`
- Expected: No changes, no errors

