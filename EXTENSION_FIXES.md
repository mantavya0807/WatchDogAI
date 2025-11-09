# Extension Fixes and Updates

## Issues Fixed

### 1. ✅ Removed `__pycache__` folder
- Chrome/Edge doesn't allow folders starting with `_` in extensions
- Removed the folder that was causing the loading error

### 2. ✅ Updated Extension to Check URLs
- Extension now only activates on risky domains (ChatGPT, Claude, etc.)
- Checks `risky_domains.json` on page load
- Only monitors typing/clipboard on risky websites

### 3. ✅ Real-Time Typing Detection
- Monitors typing in real-time (500ms debounce)
- Automatically obfuscates PII as you type
- Preserves cursor position when replacing text

### 4. ✅ Clipboard/Paste Detection
- Intercepts paste events on risky domains
- Obfuscates pasted content before it's inserted
- Handles copy events (monitors clipboard)

### 5. ✅ Integrated Main Obfuscator
- Native host now uses `src/obfuscator.py` from main project
- Uses regex + spaCy (fast mode, no transformer for real-time)
- Falls back to regex if obfuscator unavailable

### 6. ✅ Fixed Manifest
- Added `web_accessible_resources` for `risky_domains.json`
- Fixed JSON syntax errors

### 7. ✅ Fixed Logging Path
- Logs to `native_host.log` in extension folder (Windows)
- Cross-platform compatible

## How It Works Now

1. **Extension loads** → Checks current domain against risky domains list
2. **If risky domain** (ChatGPT, etc.):
   - Attaches to all text inputs/editors
   - Monitors typing in real-time (500ms debounce)
   - Intercepts paste events
   - Intercepts copy events
3. **When PII detected**:
   - Quick regex check in content script (fast)
   - Escalates to native host for full obfuscation
   - Native host uses main obfuscator (regex + spaCy)
   - Returns obfuscated text
   - Content script replaces text in real-time
4. **If safe domain**:
   - Extension doesn't activate
   - No monitoring, no interference

## Risky Domains (Default)

- chat.openai.com
- chatgpt.com
- claude.ai
- gemini.google.com
- copilot.microsoft.com
- bard.google.com
- And more (see `risky_domains.json`)

## Testing

1. **Load Extension:**
   ```
   - Go to edge://extensions/ or chrome://extensions/
   - Enable Developer mode
   - Click "Load unpacked"
   - Select Extension/edge-dlp-ext folder
   ```

2. **Test on ChatGPT:**
   - Go to chat.openai.com
   - Type: "My email is test@example.com"
   - Wait 500ms → Should see text obfuscated
   - Paste: "SSN: 123-45-6789"
   - Should be obfuscated immediately

3. **Test on Safe Site:**
   - Go to google.com
   - Type PII → Should NOT be obfuscated
   - Extension doesn't activate on safe sites

4. **Check Logs:**
   - Check `Extension/edge-dlp-ext/native_host.log`
   - Should see detection messages

## Files Changed

- `content_script.js` - Complete rewrite with URL checking and real-time detection
- `native_host.py` - Integrated main obfuscator, fixed logging
- `manifest.json` - Added web_accessible_resources, fixed syntax
- `risky_domains.json` - Updated with AI chat sites
- Removed `__pycache__/` folder

## Next Steps

1. Load extension in browser
2. Test on ChatGPT
3. Verify real-time obfuscation works
4. Check native_host.log for errors
5. Adjust risky domains as needed

