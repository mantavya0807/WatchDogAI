# Placeholder Restoration Guide

## Overview

The `placeholder_restoration_monitor.py` automatically restores placeholders (like `{FULLNAME_3}`, `{EMAIL_4}`) back to original PII values when you copy text from ChatGPT or other sources.

## How It Works

1. **Monitors Windows Clipboard** - Continuously watches for clipboard changes
2. **Detects Placeholders** - Finds patterns like `{ENTITY_TYPE_NUMBER}` (e.g., `{EMAIL_4}`)
3. **Restores via Escrow DB** - Looks up original values from the escrow database
4. **Updates Clipboard** - Automatically replaces placeholders with original PII
5. **Loop Prevention** - Multiple safeguards prevent infinite loops

## Loop Prevention Mechanisms

The monitor has **robust loop prevention** that should NOT be modified:

1. **Hash Tracking** - Tracks MD5 hash of clipboard content to prevent reprocessing
2. **History Buffer** - Maintains last 5 clipboard hashes to detect circular replacements
3. **Debouncing** - 500ms delay between restorations
4. **Sequence Tracking** - Uses Windows clipboard sequence numbers to detect external changes
5. **Processing Flag** - Prevents concurrent processing

## Setup

### 1. Start the Restoration Monitor

```bash
python placeholder_restoration_monitor.py
```

The monitor will:
- Initialize the escrow database
- Load the transformer model (optional, for missing placeholders)
- Start monitoring the clipboard

### 2. Test the Flow

1. **Upload a file to ChatGPT** (e.g., `test_code.py` with PII)
   - File gets obfuscated automatically by the extension
   - ChatGPT receives: `Contact {FULLNAME_3} at {EMAIL_4}`

2. **Copy ChatGPT's response** (Ctrl+C)
   - Monitor detects placeholders in clipboard
   - Restores them using escrow database
   - Clipboard now contains: `Contact John Smith at john@example.com`

3. **Paste anywhere** (Ctrl+V)
   - You get the restored text with real PII values

## How It Works with ChatGPT

```
┌─────────────────┐
│  Upload File    │
│  (test_code.py) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extension       │
│ Obfuscates PII  │
│ {FULLNAME_3}    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ChatGPT        │
│  Processes      │
│  Placeholders   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Copy Response  │
│  (Ctrl+C)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Monitor        │
│  Detects        │
│  Placeholders   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Escrow DB      │
│  Restores       │
│  Original PII   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Clipboard      │
│  Updated        │
│  Automatically  │
└─────────────────┘
```

## Restoration Strategy

### Step 1: Escrow Database Lookup (Fast)
- Direct lookup of placeholder → original value
- Uses SQLite database: `data/escrow/pii_escrow.db`
- Same database used by obfuscator

### Step 2: Transformer Inference (Smart Fallback)
- If placeholder not found in DB, uses transformer model
- Analyzes context around placeholder
- Generates synthetic value based on entity type

## Placeholder Pattern

The monitor detects placeholders matching:
```regex
\{([A-Z_]+_\d+)\}
```

Examples:
- `{FULLNAME_3}` ✅
- `{EMAIL_4}` ✅
- `{PHONE_NUMBER_1}` ✅
- `{SSN_2}` ✅
- `{API_KEY_1}` ✅

## Important Notes

### ⚠️ Loop Prevention Logic

**DO NOT MODIFY** the following loop prevention mechanisms:
- `_is_loop_detected()` - Hash-based loop detection
- `_update_history()` - History tracking
- `DEBOUNCE_TIME` - Debouncing delay
- `last_clipboard_hash` - Duplicate detection
- `processing` flag - Concurrent processing prevention

These are critical for preventing infinite loops when the monitor updates the clipboard.

### ✅ Safe to Modify

- `DEBOUNCE_TIME` - Can adjust delay (default: 0.5s)
- `max_history` - Can adjust history buffer size (default: 5)
- Transformer model - Can change model name
- Logging verbosity

## Troubleshooting

### Placeholders Not Restoring

1. **Check escrow database:**
   ```python
   from src.escrow_db import EscrowDatabase
   db = EscrowDatabase()
   original = db.retrieve("FULLNAME_3")  # Should return original value
   ```

2. **Verify placeholder format:**
   - Must match: `{ENTITY_TYPE_NUMBER}`
   - Example: `{EMAIL_4}` not `EMAIL_4` or `{EMAIL}`

3. **Check monitor is running:**
   - Look for console output: `✓ Restoration monitor started`
   - Should see: `🔄 RESTORATION TRIGGERED` when copying

### Infinite Loop Detected

If you see `⚠️ LOOP DETECTED`, the loop prevention is working:
- The monitor detected a circular replacement
- It skips restoration to prevent infinite loop
- This is **expected behavior** and protects the system

### Monitor Not Starting

1. **Check dependencies:**
   ```bash
   pip install pywin32
   ```

2. **Check escrow database path:**
   - Default: `data/escrow/pii_escrow.db`
   - Must match the path used by obfuscator

3. **Check Windows clipboard access:**
   - Monitor requires Windows (`win32clipboard`)
   - Linux/Mac users need alternative implementation

## Integration with Extension

The restoration monitor works **independently** of the browser extension:

- **Extension** → Obfuscates files/text before upload to ChatGPT
- **Monitor** → Restores placeholders when copying from ChatGPT

Both use the **same escrow database** for consistency.

## Example Output

```
[20:35:24] 🔄 RESTORATION TRIGGERED
  Clipboard length: 156 chars
  📋 Found 3 placeholder(s) in clipboard
    • Escrow DB: Restored 3/3
  ✅ RESTORED: 3 from DB + 0 from AI
  ✓ Clipboard updated with restored values
```

## Status

✅ **Complete and Functional**
- Loop prevention: ✅ Robust
- Escrow DB integration: ✅ Working
- Transformer fallback: ✅ Optional
- Clipboard monitoring: ✅ Active

The monitor is ready to use! Just run it and copy text from ChatGPT to see placeholders automatically restored.

