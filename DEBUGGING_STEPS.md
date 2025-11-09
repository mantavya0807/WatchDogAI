# Debugging Steps for Extension

## Check Console Logs

### 1. Browser Console (F12 on ChatGPT page)
Look for these messages:
- `[EdgeDLP] Content script loaded on: chat.openai.com`
- `[EdgeDLP] Checking domain: chat.openai.com`
- `[EdgeDLP] Risky domains list: [...]`
- `[EdgeDLP] ✓ Active on risky domain: chat.openai.com`
- `[EdgeDLP] Attached to editor: ...`
- `[EdgeDLP] Input detected on risky domain`
- `[EdgeDLP] Quick regex check found: X findings`
- `[EdgeDLP] Escalating to native host...`
- `[EdgeDLP] Sending message to service worker...`
- `[EdgeDLP] Service worker response: ...`
- `[EdgeDLP] Native response: ...`

### 2. Service Worker Console
1. Go to `edge://extensions/`
2. Find your extension
3. Click **"service worker"** link (or "Inspect views: service worker")
4. Look for:
   - `Service worker loaded`
   - `[ServiceWorker] Received message: escalate-to-native`
   - `[ServiceWorker] Sending to native host...`
   - `[ServiceWorker] Native response received: ...`
   - OR `[ServiceWorker] Native message error: ...`

### 3. Native Host Log
Check: `Extension/edge-dlp-ext/native_host.log`
- Should see: `Native host starting...`
- Should see: `Processing text for tab X: ...`
- Should see: `PII detected via obfuscator: X items`
- OR errors if something failed

## Common Issues

### Issue 1: Extension not detecting ChatGPT
**Symptoms:** No `[EdgeDLP] ✓ Active on risky domain` message

**Check:**
- Is `chat.openai.com` in risky domains list?
- Check browser console for domain check messages
- Try hardcoded fallback list

**Fix:**
- Check `risky_domains.json` includes `chat.openai.com`
- Reload extension

### Issue 2: Editor not attached
**Symptoms:** No `[EdgeDLP] Attached to editor` messages

**Check:**
- Is ChatGPT's text input a contenteditable div?
- Check browser console for attachment attempts

**Fix:**
- ChatGPT uses dynamic content - wait a few seconds after page load
- Try typing in the input box

### Issue 3: Native host not responding
**Symptoms:** `[ServiceWorker] Native message error: ...`

**Check:**
- Is native host registered in registry?
- Check `com.edge_dlp.nativehost.json` path is correct
- Check Extension ID matches

**Fix:**
- Register native host (see setup guide)
- Update Extension ID in manifest
- Restart browser

### Issue 4: No PII detected
**Symptoms:** `[EdgeDLP] Quick regex check found: 0 findings`

**Check:**
- Are you typing actual PII? (email, SSN, etc.)
- Check regex patterns match your test data

**Fix:**
- Try: `test@example.com`
- Try: `123-45-6789` (SSN)
- Check regex patterns in content_script.js

## Test Commands

```powershell
# Check if native host is registered
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.edge_dlp.nativehost"

# Check log file
Get-Content Extension/edge-dlp-ext/native_host.log -Tail 20

# Test native host directly
cd Extension/edge-dlp-ext
python test_native_host.py
```

## What to Look For

1. **Content script loads** → Should see `[EdgeDLP] Content script loaded`
2. **Domain check** → Should see `[EdgeDLP] ✓ Active on risky domain`
3. **Editor attachment** → Should see `[EdgeDLP] Attached to editor`
4. **Input detection** → Should see `[EdgeDLP] Input detected`
5. **PII detection** → Should see `[EdgeDLP] Quick regex check found: X findings`
6. **Native escalation** → Should see `[EdgeDLP] Escalating to native host...`
7. **Service worker** → Should see `[ServiceWorker] Sending to native host...`
8. **Native response** → Should see `[EdgeDLP] Native response: ...`

If any step is missing, that's where the problem is!

