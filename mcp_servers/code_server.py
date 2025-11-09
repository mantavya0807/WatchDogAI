"""
MCP Server for Code Processing
Extracts strings and comments from code files and checks for PII.
Uses tree-sitter for parsing multiple programming languages.
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, List, Optional, Set
import time
import re

try:
    from fastmcp import FastMCP
except ImportError:
    print("Error: fastmcp not installed. Run: pip install fastmcp")
    sys.exit(1)

# Import existing obfuscator
from src.obfuscator import PIIObfuscator

# Initialize MCP server
mcp = FastMCP("pii-guard-code")

# Initialize obfuscator (lazy loading)
_obfuscator: Optional[PIIObfuscator] = None

# Language support mapping
LANGUAGE_GRAMMARS = {
    'python': 'tree_sitter_python',
    'javascript': 'tree_sitter_javascript',
    'js': 'tree_sitter_javascript',
    'typescript': 'tree_sitter_javascript',  # Can use JS parser
    'java': 'tree_sitter_java',
    'cpp': 'tree_sitter_cpp',
    'c++': 'tree_sitter_cpp',
    'c': 'tree_sitter_cpp',  # Can use C++ parser
    'go': 'tree_sitter_go',
    'rust': 'tree_sitter_rust',
}

# Try to import tree-sitter
TREE_SITTER_AVAILABLE = False
try:
    from tree_sitter import Language, Parser, Query, QueryCursor
    TREE_SITTER_AVAILABLE = True
except ImportError:
    print("Warning: tree-sitter not installed. Code parsing will use fallback method.")
    print("Run: pip install tree-sitter tree-sitter-python")


def get_obfuscator() -> PIIObfuscator:
    """Get or create obfuscator instance (lazy loading)"""
    global _obfuscator
    if _obfuscator is None:
        print("Initializing PII Obfuscator for code processing...")
        _obfuscator = PIIObfuscator(
            use_regex=True,
            use_spacy=True,
            use_transformer=True,
            escrow_db_path="data/escrow/pii_escrow.db"
        )
    return _obfuscator


def detect_language(filepath: str) -> Optional[str]:
    """Detect programming language from file extension"""
    ext = Path(filepath).suffix.lower().lstrip('.')
    
    # Map extensions to languages
    ext_map = {
        'py': 'python',
        'js': 'javascript',
        'jsx': 'javascript',
        'ts': 'typescript',
        'tsx': 'typescript',
        'java': 'java',
        'cpp': 'cpp',
        'cc': 'cpp',
        'cxx': 'cpp',
        'c': 'c',
        'h': 'c',
        'hpp': 'cpp',
        'go': 'go',
        'rs': 'rust',
    }
    
    return ext_map.get(ext)


def extract_with_tree_sitter(code: str, language: str) -> tuple[List[str], List[tuple]]:
    """
    Extract strings and comments using tree-sitter queries (proper API).
    Returns both extracted text and node positions for mapping back.
    
    Returns:
        (extracted_strings, node_positions) where node_positions is list of
        (start_byte, end_byte, node_type, original_text) tuples
    """
    if not TREE_SITTER_AVAILABLE:
        return [], []
    
    try:
        # Import language grammar
        grammar_module = LANGUAGE_GRAMMARS.get(language.lower())
        if not grammar_module:
            return [], []
        
        # Dynamic import
        try:
            lang_module = __import__(grammar_module, fromlist=['language'])
            lang = Language(lang_module.language())
        except ImportError:
            print(f"Warning: {grammar_module} not installed. Using fallback method.")
            return [], []
        
        # Create parser
        parser = Parser(lang)
        tree = parser.parse(bytes(code, "utf8"))
        
        # Create query for strings and comments
        query_string = """
        (string) @string
        (comment) @comment
        """
        
        try:
            query = Query(lang, query_string)
        except Exception as e:
            print(f"Warning: Failed to create query: {e}")
            return [], []
        
        # Execute query using QueryCursor
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        
        # Extract and clean text from captures, keeping positions
        extracted = []
        node_positions = []
        
        # Process string captures
        if 'string' in captures:
            for node in captures['string']:
                text = code[node.start_byte:node.end_byte]
                # Remove quotes (single, double, triple)
                cleaned = re.sub(r'^["\']+|["\']+$', '', text)  # Remove outer quotes
                cleaned = re.sub(r'^["\']{3}|["\']{3}$', '', cleaned)  # Remove triple quotes
                if cleaned and len(cleaned.strip()) > 3:
                    extracted.append(cleaned.strip())
                    node_positions.append((node.start_byte, node.end_byte, 'string', text))
        
        # Process comment captures
        if 'comment' in captures:
            for node in captures['comment']:
                text = code[node.start_byte:node.end_byte]
                # Remove comment markers
                cleaned = re.sub(r'^//|^#|^/\*|\*/$', '', text).strip()
                if cleaned and len(cleaned.strip()) > 3:
                    extracted.append(cleaned.strip())
                    node_positions.append((node.start_byte, node.end_byte, 'comment', text))
        
        return extracted, node_positions
            
    except Exception as e:
        print(f"Warning: Tree-sitter parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return [], []


def extract_with_regex(code: str) -> List[str]:
    """Fallback method: Extract strings and comments using regex"""
    extracted = []
    
    # Extract string literals (single, double, triple quotes)
    string_patterns = [
        r'["\']([^"\']+)["\']',  # Simple strings
        r'["\']{3}(.*?)["\']{3}',  # Triple-quoted strings (multiline)
    ]
    
    for pattern in string_patterns:
        matches = re.finditer(pattern, code, re.DOTALL)
        for match in matches:
            text = match.group(1) if match.groups() else match.group(0)
            if text and len(text.strip()) > 3:
                extracted.append(text.strip())
    
    # Extract comments
    comment_patterns = [
        r'//(.+)',  # Single-line comments
        r'#(.+)',   # Python comments
        r'/\*(.*?)\*/',  # Multi-line comments
    ]
    
    for pattern in comment_patterns:
        matches = re.finditer(pattern, code, re.DOTALL)
        for match in matches:
            text = match.group(1) if match.groups() else match.group(0)
            if text and len(text.strip()) > 3:
                extracted.append(text.strip())
    
    return extracted


def check_code(filepath: str, use_tree_sitter: bool = True, max_file_size: int = 10 * 1024 * 1024) -> Dict:
    """
    Extract strings and comments from code file and check for PII.
    
    Args:
        filepath: Path to code file
        use_tree_sitter: Whether to use tree-sitter (more accurate) or regex fallback
        max_file_size: Maximum file size in bytes (default 10MB)
        
    Returns:
        Dictionary with:
        - safe_text: Obfuscated code with PII replaced
        - original_text: Original code
        - pii_found: Number of PII items detected
        - detections: List of detected PII types
        - extracted_strings: List of strings/comments extracted
        - extraction_time_ms: Time taken to extract
        - detection_time_ms: Time taken to detect PII
    """
    start_time = time.time()
    
    try:
        # Check file size
        file_size = Path(filepath).stat().st_size
        if file_size > max_file_size:
            return {
                "error": f"File too large: {file_size / (1024*1024):.1f}MB (max {max_file_size / (1024*1024):.1f}MB)",
                "pii_found": 0
            }
        
        # Check if file exists
        if not Path(filepath).exists():
            return {
                "error": f"File not found: {filepath}",
                "pii_found": 0
            }
        # Read code file
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        
        if not code.strip():
            return {
                "error": "File is empty",
                "pii_found": 0
            }
        
        # Detect language
        language = detect_language(filepath)
        print(f"Detected language: {language or 'unknown'}")
        
        # Step 1: Extract strings and comments
        print("Extracting strings and comments from code...")
        node_positions = []
        if use_tree_sitter and TREE_SITTER_AVAILABLE and language:
            extracted_strings, node_positions = extract_with_tree_sitter(code, language)
            if not extracted_strings:
                # Fallback to regex if tree-sitter fails
                extracted_strings = extract_with_regex(code)
                node_positions = []  # No positions for regex fallback
        else:
            extracted_strings = extract_with_regex(code)
            node_positions = []  # No positions for regex
        
        extraction_time = (time.time() - start_time) * 1000
        
        if not extracted_strings:
            return {
                "safe_text": code,
                "original_text": code,
                "pii_found": 0,
                "detections": [],
                "extracted_strings": [],
                "extraction_time_ms": extraction_time,
                "detection_time_ms": 0.0,
                "message": "No strings or comments found in code"
            }
        
        print(f"Extracted {len(extracted_strings)} strings/comments")
        
        # Step 2: Process each extracted string using obfuscator (transformer → spaCy → regex)
        # The obfuscator already follows: transformer → spaCy → regex in sequence
        print("Detecting PII in extracted strings...")
        print("Using obfuscator flow: Transformer → spaCy → Regex")
        obfuscator = get_obfuscator()
        
        # Process each string individually to maintain mapping
        obfuscated_strings_map = {}  # Map original extracted string to obfuscated version
        all_replacements = {}
        detection_types = set()
        total_detection_time = 0.0
        total_obfuscation_time = 0.0
        
        for extracted_str in extracted_strings:
            if extracted_str not in obfuscated_strings_map:
                # Use obfuscator which follows: transformer → spaCy → regex
                result = obfuscator.obfuscate(extracted_str, source=f"code:{filepath}")
                obfuscated_strings_map[extracted_str] = result.obfuscated_text
                
                # Collect replacements and detection types
                for placeholder, original in result.replacements.items():
                    all_replacements[placeholder] = original
                    if placeholder.startswith("{") and placeholder.endswith("}"):
                        entity_type = placeholder[1:].split("_")[0]
                        detection_types.add(entity_type)
                
                total_detection_time += result.detection_time_ms
                total_obfuscation_time += result.obfuscation_time_ms
        
        # Step 3: Replace PII in original code using exact positions
        
        # Create safe code by replacing in exact positions
        safe_code_parts = []
        last_end = 0
        
        if node_positions and len(node_positions) == len(extracted_strings):
            # Use tree-sitter positions for accurate replacement
            # Sort positions by start_byte
            sorted_positions = sorted(node_positions, key=lambda x: x[0])
            
            for idx, (start_byte, end_byte, node_type, original_text) in enumerate(sorted_positions):
                # Add text before this node
                safe_code_parts.append(code[last_end:start_byte])
                
                # Extract original content (without quotes/markers) to find its obfuscated version
                if node_type == 'string':
                    original_content = re.sub(r'^["\']+|["\']+$', '', original_text)
                    original_content = re.sub(r'^["\']{3}|["\']{3}$', '', original_content)
                else:  # comment
                    original_content = re.sub(r'^//|^#|^/\*|\*/$', '', original_text).strip()
                
                # Get the obfuscated version from the map (obfuscator did transformer → spaCy → regex)
                obfuscated_content = obfuscated_strings_map.get(original_content.strip(), original_content.strip())
                
                # Check if content was obfuscated (contains placeholders)
                if obfuscated_content != original_content.strip():
                    # PII was detected and replaced by obfuscator (transformer → spaCy → regex)
                    if node_type == 'string':
                        # Keep quotes, replace content with obfuscated version
                        quote_char = original_text[0] if original_text[0] in ['"', "'"] else '"'
                        if original_text.startswith('"""') or original_text.startswith("'''"):
                            quote_char = original_text[:3]
                            safe_code_parts.append(f'{quote_char}{obfuscated_content}{quote_char}')
                        else:
                            safe_code_parts.append(f'{quote_char}{obfuscated_content}{quote_char}')
                    else:  # comment
                        # Keep comment marker, replace content
                        if original_text.startswith('//'):
                            safe_code_parts.append(f'// {obfuscated_content}')
                        elif original_text.startswith('#'):
                            safe_code_parts.append(f'# {obfuscated_content}')
                        elif original_text.startswith('/*'):
                            safe_code_parts.append(f'/* {obfuscated_content} */')
                        else:
                            safe_code_parts.append(original_text)  # Keep original if unknown format
                else:
                    # No PII found, keep original
                    safe_code_parts.append(original_text)
                
                last_end = end_byte
            
            # Add remaining text
            safe_code_parts.append(code[last_end:])
            safe_code = ''.join(safe_code_parts)
        else:
            # Fallback: simple string replace (less accurate)
            safe_code = code
            # Sort replacements by length (longest first) to avoid partial matches
            sorted_replacements = sorted(all_replacements.items(), key=lambda x: len(x[1]), reverse=True)
            for placeholder, original in sorted_replacements:
                # Only replace if it's a complete match (not substring)
                safe_code = safe_code.replace(original, placeholder)
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            "safe_text": safe_code,
            "original_text": code,
            "pii_found": len(all_replacements),
            "detections": sorted(list(detection_types)),
            "extracted_strings": extracted_strings[:10],  # First 10 for preview
            "extraction_time_ms": extraction_time,
            "detection_time_ms": total_detection_time,
            "obfuscation_time_ms": total_obfuscation_time,
            "total_time_ms": total_time
        }
        
    except FileNotFoundError:
        return {
            "error": f"File not found: {filepath}",
            "pii_found": 0
        }
    except Exception as e:
        return {
            "error": f"Error processing code: {str(e)}",
            "pii_found": 0
        }


# Register as MCP tool
mcp.tool()(check_code)


def extract_code_strings(filepath: str, use_tree_sitter: bool = True) -> Dict:
    """
    Extract strings and comments from code file without PII detection (for testing).
    
    Args:
        filepath: Path to code file
        use_tree_sitter: Whether to use tree-sitter or regex fallback
        
    Returns:
        Dictionary with extracted strings and metadata
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        
        language = detect_language(filepath)
        
        if use_tree_sitter and TREE_SITTER_AVAILABLE and language:
            extracted = extract_with_tree_sitter(code, language)
            if not extracted:
                extracted = extract_with_regex(code)
        else:
            extracted = extract_with_regex(code)
        
        return {
            "strings": extracted,
            "count": len(extracted),
            "language": language or "unknown",
            "extracted": True
        }
        
    except Exception as e:
        return {
            "error": f"Error extracting strings: {str(e)}",
            "extracted": False
        }


# Register as MCP tool
mcp.tool()(extract_code_strings)


if __name__ == "__main__":
    # Run MCP server via stdio
    print("=" * 70)
    print("PII Guard - Code MCP Server")
    print("=" * 70)
    print("Starting server via stdio transport...")
    print("This server extracts strings/comments from code and checks for PII")
    print("=" * 70)
    mcp.run()

