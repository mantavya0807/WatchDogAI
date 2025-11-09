# Troubleshooting Native Messaging Host

## Issue: "Specified native messaging host not found"

This error means the browser cannot find the native messaging host in the Windows registry.

### Verification Steps

1. **Check Registry Entry**
   ```powershell
   Get-ItemProperty -Path "HKCU:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.edge_dlp.nativehost"
   ```
   Should show the path to `com.edge_dlp.nativehost.json`

2. **Check Manifest File**
   - Location: `Extension/edge-dlp-ext/com.edge_dlp.nativehost.json`
   - Should contain:
     - `path`: Full path to `native_host.bat`
     - `allowed_origins`: Your extension ID (e.g., `chrome-extension://gfnmacidakedamgiapgfhchbcoljojlc/`)

3. **Check Batch File**
   - Location: `Extension/edge-dlp-ext/native_host.bat`
   - Should contain full path to Python executable

### Fix Steps

1. **Restart Browser**
   - Close ALL Edge/Chrome windows completely
   - Restart the browser
   - This is required for registry changes to take effect

2. **Reload Extension**
   - Go to `edge://extensions/` (or `chrome://extensions/`)
   - Click "Reload" on your extension
   - Or remove and re-add the extension

3. **Verify Extension ID**
   - Check your extension ID in `edge://extensions/`
   - Ensure it matches the ID in `com.edge_dlp.nativehost.json`
   - If it doesn't match, update the manifest file and re-register:
     ```powershell
     cd Extension\edge-dlp-ext
     .\register_native_host.ps1
     ```

4. **Test Native Host Directly**
   ```powershell
   cd Extension\edge-dlp-ext
   .\test_native_messaging.ps1
   ```

### Current Setup Status

✅ Registry entry exists: `HKCU:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.edge_dlp.nativehost`
✅ Manifest file exists: `Extension/edge-dlp-ext/com.edge_dlp.nativehost.json`
✅ Batch file exists: `Extension/edge-dlp-ext/native_host.bat`
✅ Extension ID in manifest: `chrome-extension://gfnmacidakedamgiapgfhchbcoljojlc/`

### Next Steps

1. **Restart your browser completely** (close all windows)
2. **Reload the extension** in `edge://extensions/`
3. **Test on ChatGPT** - try typing or pasting an email address
4. **Check console logs** in the browser DevTools (F12)
5. **Check native host log**: `Extension/edge-dlp-ext/native_host.log`

### If Still Not Working

1. Check if the extension ID changed:
   - Go to `edge://extensions/`
   - Find your extension
   - Copy the ID
   - Update `com.edge_dlp.nativehost.json` with the new ID
   - Re-run `register_native_host.ps1`

2. Check Windows Event Viewer for errors:
   - Open Event Viewer
   - Look for errors related to native messaging

3. Verify Python is accessible:
   ```powershell
   python --version
   ```

4. Check file permissions:
   - Ensure the batch file and Python script are readable
   - Ensure the registry key is accessible


