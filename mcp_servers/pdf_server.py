"""
MCP Server for PDF Processing
Extracts text from PDFs and checks for PII using existing detection stack.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, Optional
import time

try:
    from fastmcp import FastMCP
except ImportError:
    print("Error: fastmcp not installed. Run: pip install fastmcp")
    sys.exit(1)

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: pymupdf not installed. Run: pip install pymupdf")
    sys.exit(1)

# Import existing obfuscator
from src.obfuscator import PIIObfuscator

# Initialize MCP server
mcp = FastMCP("pii-guard-pdf")

# Initialize obfuscator (lazy loading)
_obfuscator: Optional[PIIObfuscator] = None


def get_obfuscator() -> PIIObfuscator:
    """Get or create obfuscator instance (lazy loading)"""
    global _obfuscator
    if _obfuscator is None:
        print("Initializing PII Obfuscator for PDF processing...")
        _obfuscator = PIIObfuscator(
            use_regex=True,
            use_spacy=True,
            use_transformer=True,
            escrow_db_path="data/escrow/pii_escrow.db"
        )
    return _obfuscator


def check_pdf(filepath: str, use_ocr: bool = False, max_pages: int = 100) -> Dict:
    """
    Extract text from PDF and check for PII.
    
    Args:
        filepath: Path to PDF file
        use_ocr: Whether to use OCR for scanned PDFs (slower but handles images)
        max_pages: Maximum number of pages to process (performance limit)
        
    Returns:
        Dictionary with:
        - safe_text: Obfuscated text with PII replaced
        - original_text: Original extracted text
        - pii_found: Number of PII items detected
        - detections: List of detected PII types
        - extraction_time_ms: Time taken to extract text
        - detection_time_ms: Time taken to detect PII
        - obfuscation_time_ms: Time taken to obfuscate
    """
    start_time = time.time()
    
    try:
        # Check file size (limit to 50MB for performance)
        file_size = Path(filepath).stat().st_size
        if file_size > 50 * 1024 * 1024:  # 50MB
            return {
                "error": f"File too large: {file_size / (1024*1024):.1f}MB (max 50MB)",
                "pii_found": 0
            }
        
        # Check if file exists
        if not Path(filepath).exists():
            return {
                "error": f"File not found: {filepath}",
                "pii_found": 0
            }
        # Step 1: Extract text from PDF
        print(f"Extracting text from PDF: {filepath}")
        doc = fitz.open(filepath)
        
        total_pages = len(doc)
        if total_pages > max_pages:
            print(f"Warning: PDF has {total_pages} pages, processing first {max_pages} pages")
        
        text_parts = []
        for page_num, page in enumerate(doc, 1):
            if page_num > max_pages:
                break
            if use_ocr:
                # Use OCR for scanned PDFs (slower)
                text = page.get_text("ocr")
            else:
                # Native text extraction (fast)
                text = page.get_text()
            
            if text.strip():
                text_parts.append(text)
        
        doc.close()
        
        full_text = "\n\n".join(text_parts)
        extraction_time = (time.time() - start_time) * 1000
        
        if not full_text.strip():
            return {
                "safe_text": "",
                "original_text": "",
                "pii_found": 0,
                "detections": [],
                "extraction_time_ms": extraction_time,
                "detection_time_ms": 0.0,
                "obfuscation_time_ms": 0.0,
                "error": "No text found in PDF. Try use_ocr=True for scanned PDFs."
            }
        
        print(f"Extracted {len(full_text)} characters from PDF ({len(text_parts)} pages)")
        
        # Step 2: Detect and obfuscate PII using existing detection stack
        # The obfuscator follows: transformer → spaCy → regex
        print("Detecting PII in extracted text...")
        print("Using obfuscator flow: Transformer → spaCy → Regex")
        obfuscator = get_obfuscator()
        
        # Process each page individually to maintain mapping
        obfuscated_pages = []
        all_replacements = {}
        detection_types = set()
        total_detection_time = 0.0
        total_obfuscation_time = 0.0
        
        for page_text in text_parts:
            # Obfuscate each page individually
            result = obfuscator.obfuscate(page_text, source=f"pdf:{filepath}")
            obfuscated_pages.append(result.obfuscated_text)
            
            # Collect replacements and detection types
            for placeholder, original in result.replacements.items():
                all_replacements[placeholder] = original
                if placeholder.startswith("{") and placeholder.endswith("}"):
                    entity_type = placeholder[1:].split("_")[0]
                    detection_types.add(entity_type)
            
            total_detection_time += result.detection_time_ms
            total_obfuscation_time += result.obfuscation_time_ms
        
        # Combine obfuscated text
        obfuscated_full_text = "\n\n".join(obfuscated_pages)
        
        # Step 3: Create new PDF with obfuscated text (simple text-based PDF)
        # Note: This creates a simple PDF with text only, formatting is not preserved
        safe_pdf_doc = None
        try:
            safe_pdf_doc = fitz.open()  # Create new PDF
            for page_num, obfuscated_page_text in enumerate(obfuscated_pages, 1):
                page = safe_pdf_doc.new_page(width=612, height=792)  # US Letter size
                # Insert text at top of page
                page.insert_text((50, 50), obfuscated_page_text, fontsize=11)
        except Exception as e:
            print(f"Warning: Could not create PDF document: {e}")
            safe_pdf_doc = None
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            "safe_text": obfuscated_full_text,
            "safe_pdf": safe_pdf_doc,  # PDF document object for saving (may be None)
            "original_text": full_text,
            "pii_found": len(all_replacements),
            "detections": sorted(list(detection_types)),
            "extraction_time_ms": extraction_time,
            "detection_time_ms": total_detection_time,
            "obfuscation_time_ms": total_obfuscation_time,
            "total_time_ms": total_time,
            "page_count": len(text_parts)
        }
        
    except FileNotFoundError:
        return {
            "error": f"File not found: {filepath}",
            "pii_found": 0
        }
    except Exception as e:
        return {
            "error": f"Error processing PDF: {str(e)}",
            "pii_found": 0
        }


# Register as MCP tool
mcp.tool()(check_pdf)


def extract_pdf_text(filepath: str, use_ocr: bool = False) -> Dict:
    """
    Extract text from PDF without PII detection (for testing/debugging).
    
    Args:
        filepath: Path to PDF file
        use_ocr: Whether to use OCR for scanned PDFs
        
    Returns:
        Dictionary with extracted text and metadata
    """
    try:
        doc = fitz.open(filepath)
        
        text_parts = []
        for page_num, page in enumerate(doc, 1):
            if use_ocr:
                text = page.get_text("ocr")
            else:
                text = page.get_text()
            
            if text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{text}")
        
        doc.close()
        
        full_text = "\n\n".join(text_parts)
        
        return {
            "text": full_text,
            "char_count": len(full_text),
            "page_count": len(text_parts),
            "extracted": True
        }
        
    except Exception as e:
        return {
            "error": f"Error extracting text: {str(e)}",
            "extracted": False
        }


# Register as MCP tool
mcp.tool()(extract_pdf_text)


if __name__ == "__main__":
    # Run MCP server via stdio
    print("=" * 70)
    print("PII Guard - PDF MCP Server")
    print("=" * 70)
    print("Starting server via stdio transport...")
    print("This server extracts text from PDFs and checks for PII")
    print("=" * 70)
    mcp.run()

