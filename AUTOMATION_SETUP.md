# Automation Setup - Quick Start

## 🎯 Goal: Zero Manual Work

Make file obfuscation **completely automatic** so you never have to think about it.

---

## ✅ What We Built

### 1. **Browser Extension** - Auto-obfuscate on upload
- Intercepts file uploads to ChatGPT/Claude
- Automatically obfuscates before upload
- **Zero clicks needed!**

### 2. **File Watcher** - Auto-obfuscate on save
- Watches a directory (Downloads, Desktop, etc.)
- Automatically obfuscates files when created/modified
- **Zero clicks needed!**

### 3. **CLI Tool** - Manual obfuscation (for testing)
- `python mcp_client.py check file.py -o output.py`
- Still useful for testing and one-off files

---

## 🚀 Setup Instructions

### Step 1: Install Dependencies

```bash
# Install MCP server dependencies
pip install -r mcp_servers/requirements.txt

# Install file watcher dependency
pip install watchdog
```

### Step 2: Load Browser Extension

1. Open Chrome/Edge
2. Go to `edge://extensions/` (or `chrome://extensions/`)
3. Enable **"Developer mode"** (top right)
4. Click **"Load unpacked"**
5. Select: `Extension/edge-dlp-ext/`
6. ✅ Extension loaded!

### Step 3: Start File Watcher (Optional)

```bash
# Watch Downloads folder
python auto_file_obfuscator.py --watch ~/Downloads

# Or watch current directory
python auto_file_obfuscator.py --watch .
```

---

## 🎯 How It Works

### Scenario 1: Uploading to ChatGPT

**Before:**
1. You upload `code.py` with PII
2. PII gets sent to ChatGPT ❌

**After (with extension):**
1. You upload `code.py` with PII
2. Extension intercepts upload
3. Automatically obfuscates file
4. ChatGPT receives `code_safe.py` with placeholders ✅
5. **You don't even notice!**

### Scenario 2: Saving Files

**Before:**
1. You save `document.pdf` with PII
2. File sits there with PII ❌

**After (with file watcher):**
1. You save `document.pdf` with PII
2. File watcher detects it
3. Automatically creates `obfuscated/document_safe.pdf` ✅
4. **You don't even notice!**

---

## 📋 What Gets Obfuscated

### Supported File Types:
- ✅ **Code:** `.py`, `.js`, `.java`, `.cpp`, `.c`, `.ts`, `.go`, `.rs`
- ✅ **Documents:** `.pdf`, `.docx`, `.doc`
- ✅ **Text:** `.txt` (any text file)

### What Gets Detected:
- ✅ Emails
- ✅ Phone numbers
- ✅ SSNs
- ✅ Credit cards
- ✅ API keys
- ✅ Names, addresses
- ✅ And 20+ more PII types!

---

## 🔧 Configuration

### File Watcher Options:

```bash
# Basic usage
python auto_file_obfuscator.py --watch ~/Downloads

# Custom output directory
python auto_file_obfuscator.py --watch . --output ~/SafeFiles

# Auto-replace (⚠️ replaces original files!)
python auto_file_obfuscator.py --watch . --auto-replace
```

### Extension Configuration:

- Automatically activates on risky domains
- No configuration needed!
- Risky domains: ChatGPT, Claude, Gemini, etc.

---

## 🎉 Result

With both systems running:

1. **Upload file to ChatGPT** → Automatically obfuscated ✅
2. **Save file to Downloads** → Automatically obfuscated ✅
3. **Paste text to ChatGPT** → Automatically obfuscated ✅
4. **Copy image with text** → Automatically obfuscated ✅

**Zero manual work. Everything is automatic!**

---

## 🧪 Testing

### Test Extension:
1. Go to ChatGPT
2. Upload a file with PII
3. Check console (F12) for obfuscation messages
4. File should be obfuscated automatically

### Test File Watcher:
1. Start watcher: `python auto_file_obfuscator.py --watch .`
2. Create a file with PII
3. Check `obfuscated/` folder for obfuscated version

---

## 📝 Files Created

- `Extension/edge-dlp-ext/file_obfuscator.js` - File upload interceptor
- `auto_file_obfuscator.py` - File watcher script
- `AUTOMATION_GUIDE.md` - Detailed guide
- `AUTOMATION_SETUP.md` - This file

---

## 🎯 Next Steps

1. ✅ Load extension
2. ✅ Start file watcher (optional)
3. ✅ Test with a file upload
4. ✅ Enjoy automatic obfuscation!

**That's it! No more manual work needed.**

