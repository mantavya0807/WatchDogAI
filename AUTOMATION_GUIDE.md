# Automation Guide - Seamless File Obfuscation

## 🎯 Overview

This guide shows you how to make file obfuscation **completely automatic** - no manual work needed!

---

## 🚀 Option 1: Browser Extension (Automatic on Upload)

**Best for:** Uploading files to ChatGPT, Claude, etc.

### How It Works:
1. Install the extension
2. When you upload a file to a risky domain (ChatGPT, etc.)
3. Extension **automatically intercepts** the file upload
4. Obfuscates the file **before** it's uploaded
5. You upload the obfuscated version automatically

### Setup:
1. **Load the extension:**
   ```bash
   # In Chrome/Edge:
   # 1. Go to edge://extensions/
   # 2. Enable "Developer mode"
   # 3. Click "Load unpacked"
   # 4. Select: Extension/edge-dlp-ext/
   ```

2. **Test it:**
   - Go to ChatGPT
   - Upload a file with PII
   - The extension automatically obfuscates it before upload!

### What Gets Obfuscated:
- ✅ Code files (.py, .js, .java, etc.)
- ✅ PDF files
- ✅ DOCX files
- ✅ Any file with PII

---

## 🚀 Option 2: File Watcher (Automatic on Save)

**Best for:** Automatically obfuscating files when you save them

### How It Works:
1. Run the file watcher
2. It watches a directory (e.g., Downloads, Desktop)
3. When you save/create a file, it **automatically obfuscates** it
4. Saves obfuscated version to a safe location

### Setup:
```bash
# Install watchdog
pip install watchdog

# Watch current directory
python auto_file_obfuscator.py --watch .

# Watch Downloads folder
python auto_file_obfuscator.py --watch ~/Downloads

# Watch with custom output directory
python auto_file_obfuscator.py --watch . --output ~/SafeFiles
```

### Options:
- `--watch` / `-w`: Directory to watch (default: current directory)
- `--output` / `-o`: Output directory (default: watch_dir/obfuscated)
- `--auto-replace` / `-r`: Replace original files (⚠️ DANGEROUS!)

### Example:
```bash
# Watch Downloads folder
python auto_file_obfuscator.py --watch ~/Downloads

# Now when you save a file to Downloads:
# - Original: ~/Downloads/document.pdf
# - Obfuscated: ~/Downloads/obfuscated/document_safe.pdf
```

---

## 🚀 Option 3: Context Menu Integration (Right-Click)

**Best for:** Quick obfuscation from file explorer

### Setup (Windows):
1. Create a registry entry or batch file
2. Add "Obfuscate PII" to right-click menu
3. Click → Automatically obfuscates file

### Example Batch File:
```batch
@echo off
python "D:\Projects\HackPrinceton\mcp_client.py" check "%~1" -o "%~dpn1_safe%~x1"
```

---

## 🚀 Option 4: Clipboard Integration (Already Working!)

**Best for:** Copying text with PII

### How It Works:
- You already have this! The clipboard monitor automatically obfuscates when pasting to risky apps
- Works for text, images (via OCR), and now files!

---

## 📋 Quick Comparison

| Method | When It Works | Manual Work | Best For |
|--------|---------------|-------------|----------|
| **Extension** | On file upload | None | ChatGPT uploads |
| **File Watcher** | On file save | None | Auto-backup |
| **Context Menu** | Right-click | 1 click | Quick obfuscation |
| **CLI** | When you run | Manual | Testing |

---

## 🎯 Recommended Setup

### For Maximum Automation:

1. **Start clipboard monitor** (for text/images):
   ```bash
   python clipboard_monitor_paste_based.py
   ```

2. **Start file watcher** (for files):
   ```bash
   python auto_file_obfuscator.py --watch ~/Downloads
   ```

3. **Install extension** (for browser uploads):
   - Load extension in Chrome/Edge
   - Done!

### Result:
- ✅ Text pasted to ChatGPT → Auto-obfuscated
- ✅ Files uploaded to ChatGPT → Auto-obfuscated
- ✅ Files saved to Downloads → Auto-obfuscated
- ✅ **Zero manual work!**

---

## 🔧 Advanced: Integration with Your Workflow

### Git Hook (Auto-obfuscate before commit):
```bash
# .git/hooks/pre-commit
python mcp_client.py check "$1" -o "$1_safe"
```

### VS Code Extension:
- Create a VS Code task that runs on save
- Automatically obfuscates files before saving

### Scheduled Task (Windows):
- Run file watcher as a Windows service
- Always running in background

---

## ⚠️ Important Notes

1. **File Watcher:**
   - Don't use `--auto-replace` unless you're sure!
   - Original files are preserved by default

2. **Extension:**
   - Only works in browser
   - Only activates on risky domains
   - Files are obfuscated in memory before upload

3. **Performance:**
   - File watcher processes files as they're created
   - Large files may take a few seconds
   - Extension uploads are instant (happens before upload)

---

## 🎉 Result

With all these automations:
- **Zero manual work** - everything happens automatically
- **Always protected** - PII never leaves your machine un-obfuscated
- **Seamless experience** - you don't even notice it's happening!

