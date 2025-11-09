"""
Unified MCP Server for PII Guard
Routes file types to appropriate processors (PDF, Code, DOCX).
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

# Import individual server functions
from mcp_servers.pdf_server import check_pdf, extract_pdf_text
from mcp_servers.code_server import check_code, extract_code_strings
from mcp_servers.docx_server import check_docx, extract_docx_text

# Initialize MCP server
mcp = FastMCP("pii-guard-unified")

# File type detection
SUPPORTED_EXTENSIONS = {
    # PDF
    '.pdf': 'pdf',
    
    # Code files
    '.py': 'code',
    '.js': 'code',
    '.jsx': 'code',
    '.ts': 'code',
    '.tsx': 'code',
    '.java': 'code',
    '.cpp': 'code',
    '.cc': 'code',
    '.cxx': 'code',
    '.c': 'code',
    '.h': 'code',
    '.hpp': 'code',
    '.go': 'code',
    '.rs': 'code',
    
    # DOCX
    '.docx': 'docx',
    '.doc': 'docx',  # Note: .doc is old format, may not work perfectly
    
    # Text files
    '.txt': 'text',
    '.md': 'text',
    '.markdown': 'text',
    '.log': 'text',
    '.csv': 'text',
}


def detect_file_type(filepath: str) -> Optional[str]:
    """Detect file type from extension"""
    ext = Path(filepath).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(ext)


def check_file(
    filepath: str,
    use_ocr: bool = False,
    use_tree_sitter: bool = True,
    max_pages: int = 100,
    max_file_size: int = 50 * 1024 * 1024
) -> Dict:
    """
    Automatically detect file type and check for PII.
    Routes to appropriate processor (PDF, Code, or DOCX).
    
    Args:
        filepath: Path to file
        use_ocr: Whether to use OCR for PDFs (only used for PDF files)
        use_tree_sitter: Whether to use tree-sitter for code (only used for code files)
        max_pages: Maximum pages to process for PDFs (only used for PDF files)
        max_file_size: Maximum file size in bytes (only used for code/DOCX files)
        
    Returns:
        Dictionary with PII detection results
    """
    start_time = time.time()
    
    try:
        # Detect file type
        file_type = detect_file_type(filepath)
        
        if not file_type:
            return {
                "error": f"Unsupported file type: {Path(filepath).suffix}",
                "supported_types": list(set(SUPPORTED_EXTENSIONS.values())),
                "pii_found": 0
            }
        
        print(f"Detected file type: {file_type}")
        print(f"Processing: {filepath}")
        
        # Route to appropriate processor
        if file_type == 'pdf':
            result = check_pdf(filepath, use_ocr=use_ocr, max_pages=max_pages)
        elif file_type == 'code':
            result = check_code(filepath, use_tree_sitter=use_tree_sitter, max_file_size=max_file_size)
        elif file_type == 'docx':
            result = check_docx(filepath, max_file_size=max_file_size)
        elif file_type == 'text':
            # For text files, read and obfuscate directly
            from src.obfuscator import PIIObfuscator
            from pathlib import Path as PathLib
            
            # Read text file
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                text_content = f.read()
            
            # Initialize obfuscator
            project_root = PathLib(__file__).parent.parent
            escrow_path = project_root / "data" / "escrow" / "pii_escrow.db"
            obfuscator = PIIObfuscator(
                use_regex=True,
                use_spacy=True,
                use_transformer=True,
                transformer_model="lakshyakh93/deberta_finetuned_pii",
                escrow_db_path=str(escrow_path),
                confidence_threshold=0.85
            )
            
            # Obfuscate
            obf_result = obfuscator.obfuscate(text_content, source="unified_server")
            
            # Return in same format as other processors
            result = {
                "safe_text": obf_result.obfuscated_text,
                "pii_found": obf_result.num_redactions,
                "num_redactions": obf_result.num_redactions,
                "findings": [
                    {
                        "type": placeholder.replace('{', '').split('_')[0],
                        "match": original,
                        "start": text_content.find(original),
                        "end": text_content.find(original) + len(original) if original in text_content else 0
                    }
                    for placeholder, original in obf_result.replacements.items()
                ] if obf_result.replacements else []
            }
        else:
            return {
                "error": f"Unknown file type: {file_type}",
                "pii_found": 0
            }
        
        # Add routing metadata
        if isinstance(result, dict):
            result['file_type'] = file_type
            result['routing_time_ms'] = (time.time() - start_time) * 1000
        
        return result
        
    except Exception as e:
        return {
            "error": f"Error processing file: {str(e)}",
            "pii_found": 0
        }


# Register as MCP tool
mcp.tool()(check_file)


def extract_text(
    filepath: str,
    use_ocr: bool = False,
    use_tree_sitter: bool = True
) -> Dict:
    """
    Automatically detect file type and extract text without PII detection.
    Routes to appropriate processor.
    
    Args:
        filepath: Path to file
        use_ocr: Whether to use OCR for PDFs (only used for PDF files)
        use_tree_sitter: Whether to use tree-sitter for code (only used for code files)
        
    Returns:
        Dictionary with extracted text and metadata
    """
    try:
        # Detect file type
        file_type = detect_file_type(filepath)
        
        if not file_type:
            return {
                "error": f"Unsupported file type: {Path(filepath).suffix}",
                "supported_types": list(set(SUPPORTED_EXTENSIONS.values())),
                "extracted": False
            }
        
        # Route to appropriate processor
        if file_type == 'pdf':
            result = extract_pdf_text(filepath, use_ocr=use_ocr)
        elif file_type == 'code':
            result = extract_code_strings(filepath, use_tree_sitter=use_tree_sitter)
        elif file_type == 'docx':
            result = extract_docx_text(filepath)
        elif file_type == 'text':
            # For text files, just read the content
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                text_content = f.read()
            result = {
                "extracted": True,
                "text": text_content,
                "length": len(text_content)
            }
        else:
            return {
                "error": f"Unknown file type: {file_type}",
                "extracted": False
            }
        
        # Add routing metadata
        if isinstance(result, dict):
            result['file_type'] = file_type
        
        return result
        
    except Exception as e:
        return {
            "error": f"Error extracting text: {str(e)}",
            "extracted": False
        }


# Register as MCP tool
mcp.tool()(extract_text)


def list_supported_types() -> Dict:
    """
    List all supported file types and their processors.
    
    Returns:
        Dictionary with supported file types grouped by processor
    """
    types_by_processor = {
        'pdf': [],
        'code': [],
        'docx': [],
        'text': []
    }
    
    for ext, processor in SUPPORTED_EXTENSIONS.items():
        types_by_processor[processor].append(ext)
    
    return {
        "supported_types": types_by_processor,
        "total_extensions": len(SUPPORTED_EXTENSIONS),
        "processors": list(types_by_processor.keys())
    }


# Register as MCP tool
mcp.tool()(list_supported_types)


if __name__ == "__main__":
    # Run MCP server via stdio
    print("=" * 70)
    print("PII Guard - Unified MCP Server")
    print("=" * 70)
    print("Starting server via stdio transport...")
    print("This server automatically routes file types to appropriate processors")
    print("=" * 70)
    print("\nSupported file types:")
    types_by_processor = {
        'pdf': [],
        'code': [],
        'docx': [],
        'text': []
    }
    for ext, processor in SUPPORTED_EXTENSIONS.items():
        types_by_processor[processor].append(ext)
    
    for processor, extensions in types_by_processor.items():
        print(f"  {processor.upper()}: {', '.join(extensions)}")
    print("=" * 70)
    mcp.run()

