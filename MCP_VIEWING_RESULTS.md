# How to View MCP Integration Results

## 📊 Where to See Results

### 1. **Console/Terminal Output** (Immediate Results)

When you run the MCP client, results are displayed directly in your terminal:

```bash
# Basic output (shows summary)
python mcp_client.py check mcp_servers/test_files/test_code.py

# Verbose output (shows original and safe text)
python mcp_client.py check mcp_servers/test_files/test_code.py -v
```

**What you'll see:**
- ⚠️ PII DETECTED: Number of items found
- Types: List of detected PII types (EMAIL, PHONE, SSN, etc.)
- ⏱️ Performance: Extraction, detection, and total time
- 📄 Original Text: First 500 chars (with `-v` flag)
- 🔒 Safe Text: First 500 chars with PII replaced (with `-v` flag)

### 2. **Saved Output Files** (Full Results)

Save the complete safe text to a file:

```bash
# Save safe text to file
python mcp_client.py check document.pdf -o safe_document.txt

# Save with verbose output
python mcp_client.py check script.py -v -o safe_script.py
```

**File location:** Saved in the current directory (or path you specify)

### 3. **Escrow Database** (Original PII Values)

The original PII values are stored in the escrow database:

**Location:** `data/escrow/pii_escrow.db`

**View escrow entries:**
```python
from src.escrow_db import EscrowDatabase

db = EscrowDatabase("data/escrow/pii_escrow.db")
entries = db.get_all_entries()

for entry in entries:
    print(f"{entry.placeholder_id} -> {entry.original_value}")
    print(f"  Type: {entry.entity_type}")
    print(f"  Source: {entry.source}")
    print(f"  Timestamp: {entry.timestamp}")
    print()
```

**Or use the CLI:**
```bash
python cli.py export --output escrow_export.json
```

### 4. **Python API** (Programmatic Access)

Access results programmatically:

```python
from mcp_servers.unified_server import check_file

result = check_file("document.pdf")

# Access results
print(f"PII Found: {result['pii_found']}")
print(f"Detections: {result['detections']}")
print(f"Safe Text: {result['safe_text']}")
print(f"Original Text: {result['original_text']}")
```

## 📁 Result Locations Summary

| Result Type | Location | How to Access |
|------------|----------|---------------|
| **Console Output** | Terminal | Run `mcp_client.py check` |
| **Safe Text File** | Current directory | Use `-o filename.txt` flag |
| **Original PII** | `data/escrow/pii_escrow.db` | Use `EscrowDatabase` or `cli.py export` |
| **Performance Stats** | Console output | Shown in terminal |
| **Detection Details** | Console output | Use `-v` flag for verbose |

## 🔍 Example: Viewing Complete Results

### Step 1: Run Check with Verbose Output
```bash
python mcp_client.py check mcp_servers/test_files/test_code.py -v -o safe_code.py
```

### Step 2: View Saved File
```bash
# Windows
type safe_code.py

# Linux/Mac
cat safe_code.py
```

### Step 3: View Escrow Database
```python
from src.escrow_db import EscrowDatabase

db = EscrowDatabase("data/escrow/pii_escrow.db")
stats = db.get_stats()

print(f"Total entries: {stats['total_entries']}")
print(f"By type: {stats['by_type']}")
```

## 📊 Understanding the Output

### Console Output Format:
```
======================================================================
RESULTS
======================================================================
⚠️  PII DETECTED: 25 items
   Types: EMAIL, PHONE, SSN, CREDITCARDNUMBER, PERSON, ...

⏱️  Performance:
   Extraction: 3.00ms
   Detection: 270.22ms
   Total: 3129.70ms

📄 Original Text (first 500 chars):
----------------------------------------------------------------------
[Your original text here...]

🔒 Safe Text (first 500 chars):
----------------------------------------------------------------------
[Your safe text with placeholders...]
======================================================================
```

### Result Dictionary Structure:
```python
{
    "safe_text": "Text with {PERSON_1}, {EMAIL_1}, etc.",
    "original_text": "Original text with actual PII",
    "pii_found": 25,
    "detections": ["EMAIL", "PHONE", "SSN", ...],
    "extraction_time_ms": 3.00,
    "detection_time_ms": 270.22,
    "obfuscation_time_ms": 0.50,
    "total_time_ms": 3129.70,
    "file_type": "code"
}
```

## 🎯 Quick Reference

### View Results in Console:
```bash
python mcp_client.py check <file> -v
```

### Save Results to File:
```bash
python mcp_client.py check <file> -o <output_file>
```

### View Escrow Database:
```python
from src.escrow_db import EscrowDatabase
db = EscrowDatabase("data/escrow/pii_escrow.db")
entries = db.get_all_entries()
```

### Export Escrow to JSON:
```bash
python cli.py export --output escrow.json
```

## 📝 Notes

- **Console output** shows summary by default, full text with `-v`
- **Saved files** contain the complete safe text (all PII replaced)
- **Escrow database** stores original values for restoration
- **Performance stats** are always shown in console output

