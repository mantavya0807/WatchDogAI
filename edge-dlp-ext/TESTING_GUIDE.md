# Testing Guide for EdgeDLP Extension

## Quick Test Steps

### 1. Reload the Extension
1. Open Chrome/Edge and go to `chrome://extensions/` (or `edge://extensions/`)
2. Find "EdgeDLP (Prototype)" extension
3. Click the **reload** button (circular arrow icon)
4. Make sure it's **enabled** (toggle should be ON)

### 2. Open ChatGPT
1. Go to `https://chatgpt.com/`
2. Open the browser console:
   - Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
   - Click on the **Console** tab

### 3. Test PII Detection
Type text with PII in the ChatGPT input box:

**Test Cases:**
- Email: `Hi my email is test@example.com`
- Phone: `My phone number is 5645444219`
- Name + Email: `My name is John Doe and my email is john@example.com`
- Multiple PII: `Hi, I'm Mantavya Mahajan, my email is mantavya@gmail.com and my phone is 5645444219`

### 4. What to Look For

#### In the Browser Console (Content Script):
You should see logs like:
```
[EdgeDLP] Content script loaded on: chatgpt.com
[EdgeDLP] ✓ Active on risky domain: chatgpt.com
[EdgeDLP] Input detected on risky domain
[EdgeDLP] Quick regex check found: 1 findings
[EdgeDLP] Escalating to native host...
[EdgeDLP] Sending message to service worker (request ID: 1)...
[EdgeDLP] Native verdict received for request 1: {action: 'replace', replacement: '...', ...}
[EdgeDLP] Replacing text with obfuscated version
```

#### In the Service Worker Console:
1. In `chrome://extensions/`, click **"service worker"** link under the extension
2. You should see:
```
Service worker loaded
Received message: escalate-to-native
[ServiceWorker] Escalating to native: ...
[ServiceWorker] Native response received: ...
[ServiceWorker] Response sent to content script successfully
```

#### In the Native Host Log:
Check the log file: `Extension/edge-dlp-ext/native_host.log`

You should see:
```
Native host starting...
Obfuscator initialized eagerly with transformer model
Regex detector initialized for fallback
Processing text for tab ...
PII detected via obfuscator: X items
Response sent successfully
```

### 5. Expected Behavior

**When you type PII:**
1. Text should be **automatically replaced** with obfuscated version (e.g., `{EMAIL_11}`, `{PHONE_4}`)
2. The replacement happens **in real-time** as you type
3. The original text is stored in the escrow database

**Example:**
- You type: `My email is test@example.com`
- It becomes: `My email is {EMAIL_11}`

### 6. Troubleshooting

#### If nothing happens:
1. **Check extension is loaded:**
   - Go to `chrome://extensions/`
   - Make sure extension is enabled
   - Check for any errors (red error icon)

2. **Check native host registration:**
   - Run: `.\register_native_host.ps1` in PowerShell
   - Make sure it says "Registration successful"

3. **Check console for errors:**
   - Look for red error messages in browser console
   - Check service worker console for errors

4. **Check native host log:**
   - Open `Extension/edge-dlp-ext/native_host.log`
   - Look for errors or initialization issues

#### If timeout errors:
- The transformer model takes longer to initialize (1-2 seconds)
- First request may timeout, but subsequent requests should work
- Check if obfuscator initialized successfully in the log

#### If PII not detected:
- Check if the text matches the patterns (email format, phone format, etc.)
- Check the native host log to see what was detected
- Try different PII formats (e.g., `(555) 123-4567` vs `555-123-4567`)

### 7. Testing Different PII Types

**Emails:**
- `test@example.com`
- `user.name@domain.co.uk`
- `user+tag@example.org`

**Phone Numbers:**
- `5645444219`
- `(555) 123-4567`
- `555-123-4567`
- `+1 555 123 4567`

**Names:**
- `John Doe`
- `Mantavya Mahajan`
- (Detected by spaCy/transformer, not regex)

**SSN:**
- `123-45-6789`
- `123 45 6789`

**Credit Cards:**
- `4532015112830366`
- `4532-0151-1283-0366`

### 8. Performance Testing

**First Request:**
- May take 2-5 seconds (transformer model initialization)
- Check log: "Obfuscator initialized eagerly with transformer model"

**Subsequent Requests:**
- Should be faster (1-2 seconds)
- Obfuscator is already initialized

**Typing Speed:**
- Extension uses 500ms debounce
- Should not interfere with normal typing
- Detection happens after you pause typing

### 9. Advanced Testing

**Test Paste:**
1. Copy text with PII: `My email is test@example.com`
2. Paste into ChatGPT input box
3. Should be obfuscated immediately

**Test Copy:**
1. Type text with PII
2. Select and copy it
3. Check if copy event is logged in console

**Test Multiple Requests:**
1. Type rapidly with PII
2. Check if all requests are handled correctly
3. Check for request ID matching in logs

### 10. Verification

**Check Escrow Database:**
- Location: `data/escrow/pii_escrow.db`
- Contains original PII values
- Can be queried to verify storage

**Check Obfuscation:**
- Text should be replaced with placeholders like `{EMAIL_11}`, `{PHONE_4}`, `{PERSON_108}`
- Original text should be in escrow database
- Obfuscated text should be in the input field

## Quick Test Script

Run this in PowerShell to check everything:

```powershell
cd D:\Projects\HackPrinceton\Extension\edge-dlp-ext

# Check native host registration
Get-ItemProperty -Path "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.edge_dlp.nativehost" -ErrorAction SilentlyContinue

# Check log file
Get-Content native_host.log -Tail 20

# Test native host directly
python test_native_host_standalone.py
```

## Success Indicators

✅ Extension loads without errors  
✅ Native host initializes successfully  
✅ PII is detected and obfuscated  
✅ Text is replaced in real-time  
✅ No timeout errors  
✅ Logs show successful detection  


