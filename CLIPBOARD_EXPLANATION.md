# How Copy/Paste Works: System-Level vs Browser Extension

## Two Different Approaches

### 1. **System-Level Clipboard Monitor** (`clipboard_monitor_paste_based.py`)

**How it works:**
- **COPY**: User copies text → Text goes to **Windows system clipboard** → Python script monitors clipboard changes → Detects PII → Stores both original and obfuscated versions in memory
- **PASTE**: User pastes (Ctrl+V) → **Windows reads from system clipboard** → Python script monitors which app has focus → If dangerous app (Slack, Discord, etc.), Python **modifies the system clipboard** to obfuscated version → App pastes obfuscated text

**Key point:** The Python script **actually modifies the Windows system clipboard** based on which app has focus. The clipboard content changes dynamically.

```
User copies "john@example.com"
  ↓
System clipboard = "john@example.com" (original)
Python stores: original + obfuscated versions
  ↓
User switches to Slack (dangerous app)
  ↓
Python modifies system clipboard = "{EMAIL_1}" (obfuscated)
  ↓
User pastes in Slack → Gets obfuscated version
```

---

### 2. **Browser Extension** (Current Implementation)

**How it works:**
- **COPY**: User copies text in browser → Browser fires `copy` event → Extension intercepts → Detects PII → Obfuscates → Stores both versions in **extension memory** (NOT in system clipboard)
- **PASTE**: User pastes in browser → Browser fires `paste` event → Extension intercepts → Checks if on risky domain → If yes and cached obfuscated exists, **prevents default paste** and inserts obfuscated version

**Key point:** The extension **does NOT modify the system clipboard**. It intercepts browser events and replaces the paste content in the browser only.

```
User copies "john@example.com" in browser
  ↓
System clipboard = "john@example.com" (original) ← Still original!
Extension memory = {original: "john@example.com", obfuscated: "{EMAIL_1}"}
  ↓
User pastes on ChatGPT (risky domain)
  ↓
Extension intercepts paste event
  ↓
Extension prevents default paste, inserts "{EMAIL_1}" directly into browser
  ↓
User sees obfuscated version in browser
```

---

## Current Implementation Details

### Copy Flow (Browser Extension):
1. User selects text and presses Ctrl+C (or right-click → Copy)
2. Browser fires `copy` event
3. Extension's `handleCopy()` function runs:
   - Gets selected text from `window.getSelection()`
   - Detects PII using regex
   - Sends to native host for full obfuscation
   - Stores both versions in `clipboardCache` (in-memory JavaScript variable)
4. **System clipboard still has original text** (we don't modify it)

### Paste Flow (Browser Extension):
1. User presses Ctrl+V (or right-click → Paste) in browser
2. Browser fires `paste` event
3. Extension's `handlePaste()` function runs:
   - Checks if we're on a risky domain (ChatGPT, etc.)
   - Checks if we have cached obfuscated version from recent copy
   - If yes: `ev.preventDefault()` → Insert obfuscated version directly
   - If no: Check pasted content and obfuscate if needed
4. **System clipboard still has original** (we just intercept the paste)

---

## Limitations of Browser Extension Approach

1. **Only works in browser**: Can't protect when pasting into desktop apps (Slack, Discord, etc.)
2. **System clipboard unchanged**: If user pastes outside browser, they get original text
3. **Memory-based**: Cache is lost if extension reloads or page refreshes

---

## Why We Can't Modify System Clipboard from Browser

Browser extensions run in a **sandboxed environment** for security. They cannot:
- Directly access or modify the Windows system clipboard
- Monitor which desktop application has focus
- Intercept paste events outside the browser

This is why the system-level Python script is needed for full protection across all applications.

---

## Hybrid Approach (Best of Both Worlds)

1. **Browser Extension**: Protects when copying/pasting within browser (works on any website)
2. **System-Level Monitor**: Protects when copying/pasting in desktop applications (Slack, Discord, etc.)

Both can run simultaneously and complement each other!

