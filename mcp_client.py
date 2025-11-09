"""
MCP Client CLI for PII Guard
Command-line interface for testing MCP servers.
"""

import sys
import argparse
import json
import io
from pathlib import Path
from typing import Dict, Any

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Import server functions directly (for testing without MCP protocol)
from mcp_servers.pdf_server import check_pdf, extract_pdf_text
from mcp_servers.code_server import check_code, extract_code_strings
from mcp_servers.docx_server import check_docx, extract_docx_text
from mcp_servers.unified_server import check_file, extract_text, list_supported_types


def print_result(result: Dict[str, Any], verbose: bool = False):
    """Pretty print result dictionary"""
    if "error" in result:
        print(f"\n❌ Error: {result['error']}")
        return
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    if "pii_found" in result:
        pii_count = result.get("pii_found", 0)
        if pii_count > 0:
            print(f"⚠️  PII DETECTED: {pii_count} items")
        else:
            print("✅ No PII detected")
        
        if "detections" in result and result["detections"]:
            print(f"   Types: {', '.join(result['detections'])}")
    
    if "extraction_time_ms" in result:
        print(f"\n⏱️  Performance:")
        print(f"   Extraction: {result.get('extraction_time_ms', 0):.2f}ms")
        if "detection_time_ms" in result:
            print(f"   Detection: {result.get('detection_time_ms', 0):.2f}ms")
        if "obfuscation_time_ms" in result:
            print(f"   Obfuscation: {result.get('obfuscation_time_ms', 0):.2f}ms")
        if "total_time_ms" in result:
            print(f"   Total: {result.get('total_time_ms', 0):.2f}ms")
    
    if verbose:
        if "original_text" in result:
            print(f"\n📄 Original Text (first 500 chars):")
            print("-" * 70)
            print(result["original_text"][:500] + ("..." if len(result["original_text"]) > 500 else ""))
        
        if "safe_text" in result:
            print(f"\n🔒 Safe Text (first 500 chars):")
            print("-" * 70)
            print(result["safe_text"][:500] + ("..." if len(result["safe_text"]) > 500 else ""))
    
    print("=" * 70)


def cmd_check(args):
    """Check file for PII"""
    print(f"\n🔍 Checking file for PII: {args.file}")
    print("=" * 70)
    
    # Use unified server
    use_ocr = getattr(args, 'use_ocr', False)
    use_tree_sitter = not getattr(args, 'no_tree_sitter', False)
    
    result = check_file(
        args.file,
        use_ocr=use_ocr,
        use_tree_sitter=use_tree_sitter
    )
    print_result(result, verbose=args.verbose)
    
    # Save output if requested
    if args.output and "safe_text" in result:
        output_path = Path(args.output)
        input_path = Path(args.file)
        
        # If output doesn't have extension, preserve input file extension
        if not output_path.suffix and input_path.suffix:
            output_path = output_path.with_suffix(input_path.suffix)
        
        # If output is a directory or doesn't exist, generate filename
        if output_path.is_dir() or not output_path.parent.exists():
            # Generate output filename: input_safe.ext
            output_path = input_path.parent / f"{input_path.stem}_safe{input_path.suffix}"
        
        # Check if we have a DOCX document object to save
        if "safe_docx" in result and result["safe_docx"]:
            # Save as DOCX file
            result["safe_docx"].save(str(output_path))
            print(f"\n✅ Saved safe DOCX to: {output_path}")
        elif "safe_pdf" in result and result["safe_pdf"]:
            # Save as PDF file
            result["safe_pdf"].save(str(output_path))
            result["safe_pdf"].close()
            print(f"\n✅ Saved safe PDF to: {output_path}")
        else:
            # Save as text file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result["safe_text"])
            print(f"\n✅ Saved safe text to: {output_path}")


def cmd_extract(args):
    """Extract text from file without PII detection"""
    print(f"\n📄 Extracting text from: {args.file}")
    print("=" * 70)
    
    use_ocr = getattr(args, 'use_ocr', False)
    use_tree_sitter = not getattr(args, 'no_tree_sitter', False)
    
    result = extract_text(
        args.file,
        use_ocr=use_ocr,
        use_tree_sitter=use_tree_sitter
    )
    
    if "error" in result:
        print(f"\n❌ Error: {result['error']}")
        return
    
    if "text" in result:
        print(f"\nExtracted {result.get('char_count', 0)} characters")
        if args.verbose:
            print("\n" + "-" * 70)
            print(result["text"][:1000] + ("..." if len(result["text"]) > 1000 else ""))
            print("-" * 70)
        
        # Save output if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result["text"])
            print(f"\n✅ Saved extracted text to: {args.output}")
    elif "strings" in result:
        print(f"\nExtracted {result.get('count', 0)} strings/comments")
        if args.verbose:
            print("\nFirst 10 strings:")
            for i, s in enumerate(result["strings"][:10], 1):
                print(f"  {i}. {s[:100]}...")


def cmd_list(args):
    """List supported file types"""
    result = list_supported_types()
    
    print("\n" + "=" * 70)
    print("SUPPORTED FILE TYPES")
    print("=" * 70)
    
    for processor, extensions in result["supported_types"].items():
        print(f"\n{processor.upper()}:")
        print(f"  {', '.join(extensions)}")
    
    print(f"\nTotal: {result['total_extensions']} extensions")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="PII Guard MCP Client - Check files for PII",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check a PDF file
  python mcp_client.py check document.pdf
  
  # Check a code file
  python mcp_client.py check script.py
  
  # Extract text without PII detection
  python mcp_client.py extract document.pdf -o extracted.txt
  
  # Use OCR for scanned PDF
  python mcp_client.py check scanned.pdf --use-ocr
  
  # List supported file types
  python mcp_client.py list
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check file for PII')
    check_parser.add_argument('file', help='File to check')
    check_parser.add_argument('-o', '--output', help='Save safe text to file (preserves original file extension if not specified)')
    check_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output')
    check_parser.add_argument('--use-ocr', action='store_true', help='Use OCR for PDFs (slower)')
    check_parser.add_argument('--no-tree-sitter', action='store_true', help='Use regex fallback for code')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract text without PII detection')
    extract_parser.add_argument('file', help='File to extract text from')
    extract_parser.add_argument('-o', '--output', help='Save extracted text to file')
    extract_parser.add_argument('-v', '--verbose', action='store_true', help='Show extracted text')
    extract_parser.add_argument('--use-ocr', action='store_true', help='Use OCR for PDFs')
    extract_parser.add_argument('--no-tree-sitter', action='store_true', help='Use regex fallback for code')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List supported file types')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'check':
            cmd_check(args)
        elif args.command == 'extract':
            cmd_extract(args)
        elif args.command == 'list':
            cmd_list(args)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()

