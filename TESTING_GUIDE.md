# Testing Guide - PII Guard MCP Servers

## Quick Test Commands

### 1. Test Code Files (Python, JavaScript, etc.)

```bash
# Test with sample code file
python mcp_client.py check mcp_servers/test_files/test_code.py -o test_code_safe

# Check the output (should be a .py file)
# The output will be: test_code_safe.py
```

**What to verify:**
- ✅ Output file is `.py` (not `.txt`)
- ✅ PII in strings/comments is replaced with placeholders
- ✅ Code structure is preserved
- ✅ API keys, emails, SSNs, etc. are detected

### 2. Test DOCX Files

```bash
# Test with sample DOCX file
python mcp_client.py check mcp_servers/test_files/test_docx.docx -o test_docx_safe

# Check the output (should be a .docx file)
# The output will be: test_docx_safe.docx
```

**What to verify:**
- ✅ Output file is `.docx` (not `.txt`)
- ✅ Document structure is preserved (paragraphs, tables)
- ✅ PII is replaced with placeholders
- ✅ You can open it in Word/LibreOffice

### 3. Test PDF Files

```bash
# Test with a PDF file
python mcp_client.py check document.pdf -o document_safe

# With OCR for scanned PDFs
python mcp_client.py check scanned.pdf --use-ocr -o scanned_safe
```

**What to verify:**
- ✅ Output file is `.pdf` (if PDF output is implemented)
- ✅ Text is extracted and PII is detected
- ✅ OCR works for scanned documents

### 4. List Supported File Types

```bash
python mcp_client.py list
```

### 5. Verbose Output (See Details)

```bash
# See detailed output including original and safe text
python mcp_client.py check mcp_servers/test_files/test_code.py -v -o test_code_safe
```

## Creating Test Files

### Create a Test DOCX File

```python
from docx import Document

doc = Document()
doc.add_paragraph('Test Document with PII')
doc.add_paragraph('Contact John Smith at john.smith@example.com')
doc.add_paragraph('Phone: (555) 123-4567')
doc.add_paragraph('SSN: 123-45-6789')
doc.add_paragraph('Address: 123 Main St, Seattle, WA 98101')
doc.add_paragraph('API Key: sk-1234567890abcdef')
doc.save('test_docx.docx')
```

### Create a Test Code File

```python
# test_code.py
API_KEY = "sk-1234567890abcdef"
USER_EMAIL = "john.smith@example.com"
PHONE_NUMBER = "555-123-4567"
# Comment with SSN: 123-45-6789
```

## Expected Results

### Code Files
- **Input:** `test_code.py` with PII in strings/comments
- **Output:** `test_code_safe.py` with placeholders like `{EMAIL_1}`, `{SSN_1}`, etc.
- **Format:** Python file (`.py`)

### DOCX Files
- **Input:** `test_docx.docx` with PII in paragraphs
- **Output:** `test_docx_safe.docx` with placeholders
- **Format:** DOCX file (`.docx`)

### PDF Files
- **Input:** `document.pdf` with PII in text
- **Output:** Text file or PDF (depending on implementation)
- **Format:** Text or PDF

## Troubleshooting

### Issue: "File not found"
- Make sure the file path is correct
- Use absolute paths if needed

### Issue: "Unsupported file type"
- Check supported types: `python mcp_client.py list`
- Make sure file has correct extension

### Issue: "No PII detected"
- Check if the file actually contains PII
- Try verbose mode: `-v` flag
- Check if obfuscator is initialized correctly

### Issue: Output is text file instead of original format
- Make sure you're using the latest version
- Check that the file extension is preserved in output path

## Performance Testing

```bash
# Time the operation
time python mcp_client.py check large_file.docx -o output.docx

# Check performance metrics in output
# Look for: Extraction time, Detection time, Obfuscation time
```

## Integration Testing

```bash
# Test all file types
python mcp_client.py check test.py -o test_safe.py
python mcp_client.py check test.docx -o test_safe.docx
python mcp_client.py check test.pdf -o test_safe.pdf

# Verify outputs are correct format
ls -la test_safe.*
```

