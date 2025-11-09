"""
Demo Script for MCP Integration
Shows PII detection across multiple file types.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.unified_server import check_file, list_supported_types

def print_header(title: str):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_list_types():
    """Demo: List supported file types"""
    print_header("SUPPORTED FILE TYPES")
    
    result = list_supported_types()
    
    for processor, extensions in result["supported_types"].items():
        print(f"\n{processor.upper()}:")
        for ext in extensions:
            print(f"  • {ext}")
    
    print(f"\nTotal: {result['total_extensions']} file extensions supported")


def demo_code_file():
    """Demo: Check code file for PII"""
    print_header("CODE FILE DETECTION")
    
    test_file = Path(__file__).parent / "test_files" / "test_code.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    print(f"📄 File: {test_file.name}")
    print(f"   Path: {test_file}")
    
    result = check_file(str(test_file))
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"\n✅ Results:")
    print(f"   PII Found: {result.get('pii_found', 0)} items")
    
    if result.get('detections'):
        print(f"   Types: {', '.join(result['detections'])}")
    
    if "extraction_time_ms" in result:
        print(f"\n⏱️  Performance:")
        print(f"   Extraction: {result.get('extraction_time_ms', 0):.2f}ms")
        print(f"   Detection: {result.get('detection_time_ms', 0):.2f}ms")
        print(f"   Total: {result.get('total_time_ms', 0):.2f}ms")
    
    # Show sample of safe text
    if "safe_text" in result:
        print(f"\n🔒 Sample Safe Text (first 300 chars):")
        print("-" * 70)
        print(result["safe_text"][:300] + "...")
        print("-" * 70)


def demo_text_file():
    """Demo: Check text file for PII"""
    print_header("TEXT FILE DETECTION")
    
    test_file = Path(__file__).parent / "test_files" / "sample_text.txt"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    print(f"📄 File: {test_file.name}")
    print(f"   Path: {test_file}")
    
    # For text files, we can use the existing obfuscator directly
    from src.obfuscator import PIIObfuscator
    
    with open(test_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"\n📝 Original Text (first 200 chars):")
    print("-" * 70)
    print(text[:200] + "...")
    print("-" * 70)
    
    obfuscator = PIIObfuscator()
    result = obfuscator.obfuscate(text, source="demo")
    
    print(f"\n✅ Results:")
    print(f"   PII Found: {result.num_redactions} items")
    print(f"   Detection Time: {result.detection_time_ms:.2f}ms")
    
    print(f"\n🔒 Safe Text (first 200 chars):")
    print("-" * 70)
    print(result.obfuscated_text[:200] + "...")
    print("-" * 70)
    
    obfuscator.close()


def demo_summary():
    """Demo: Summary of capabilities"""
    print_header("MCP INTEGRATION SUMMARY")
    
    print("""
✅ COMPLETED FEATURES:

1. PDF Processing
   • Extract text from PDFs (native + OCR)
   • Detect PII in extracted text
   • Obfuscate PII with placeholders

2. Code Processing
   • Parse code files (Python, JS, Java, C++, Go, Rust)
   • Extract strings and comments
   • Detect PII in code strings
   • Obfuscate PII in code

3. DOCX Processing
   • Extract text from DOCX files
   • Extract from paragraphs and tables
   • Detect and obfuscate PII

4. Unified Interface
   • Automatic file type detection
   • Routing to appropriate processor
   • Single command for all file types

5. Integration
   • Uses existing detection stack (no changes!)
   • Uses existing obfuscation engine (no changes!)
   • Uses existing escrow database (no changes!)
   • 100% local processing (no cloud!)

📊 ARCHITECTURE:

File → Extract Text → Detection Stack → Obfuscation → Safe Output
         (MCP)         (Existing)        (Existing)      (Protected)

🎯 KEY BENEFITS:

• Zero changes to existing code
• Standardized interface (MCP protocol)
• Extensible (easy to add more file types)
• Local-first (no cloud dependencies)
• Production-ready (uses battle-tested detection stack)
    """)


def main():
    """Run demo"""
    print("\n" + "=" * 70)
    print("  PII GUARD - MCP INTEGRATION DEMO")
    print("=" * 70)
    print("\nThis demo shows PII detection across multiple file types")
    print("using the MCP (Model Context Protocol) integration.")
    
    try:
        # Demo 1: List supported types
        demo_list_types()
        
        # Demo 2: Code file
        demo_code_file()
        
        # Demo 3: Text file (using existing obfuscator)
        demo_text_file()
        
        # Demo 4: Summary
        demo_summary()
        
        print("\n" + "=" * 70)
        print("  DEMO COMPLETE")
        print("=" * 70)
        print("\nTo test with your own files:")
        print("  python mcp_client.py check <file>")
        print("\nTo list supported file types:")
        print("  python mcp_client.py list")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

