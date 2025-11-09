"""
CLI Interface for PII Obfuscator
Simple command-line interface for testing text and image obfuscation.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from obfuscator import PIIObfuscator
from image_obfuscator import ImagePIIObfuscator
import time

def obfuscate_text_cli(args):
    """Handle text obfuscation command"""
    print("\n" + "=" * 60)
    print("TEXT OBFUSCATION")
    print("=" * 60)
    
    # Create obfuscator
    obfuscator = PIIObfuscator(
        use_regex=args.regex,
        use_spacy=args.spacy,
        use_transformer=args.transformer,
        spacy_model=args.spacy_model,
        # Consensus mode (if enabled)
        use_consensus=getattr(args, 'consensus', False),
        consensus_mode=getattr(args, 'consensus_mode', 'any_two')
    )
    
    # Get input text
    if args.file:
        print(f"\nReading from file: {args.file}")
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        print("\nEnter text to obfuscate (press Ctrl+Z then Enter on Windows, or Ctrl+D on Unix when done):")
        text = sys.stdin.read()
    
    if not text.strip():
        print("Error: No input text provided")
        return
    
    print(f"\nOriginal text:")
    print("-" * 60)
    print(text.strip())
    
    # Obfuscate
    print("\nObfuscating...")
    start_time = time.time()
    result = obfuscator.obfuscate(text, source=args.source)
    total_time = time.time() - start_time
    
    print(f"\nObfuscated text:")
    print("-" * 60)
    print(result.obfuscated_text.strip())
    
    # Show stats
    print(f"\nStatistics:")
    print("-" * 60)
    print(f"  Detections: {result.num_redactions}")
    print(f"  Detection time: {result.detection_time_ms:.2f}ms")
    print(f"  Obfuscation time: {result.obfuscation_time_ms:.2f}ms")
    print(f"  Total time: {total_time * 1000:.2f}ms")
    
    if result.replacements and not args.no_details:
        print(f"\nReplacements:")
        print("-" * 60)
        for placeholder, original in result.replacements.items():
            print(f"  {placeholder:20} -> {original}")
    
    # Save output if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result.obfuscated_text)
        print(f"\n✓ Saved obfuscated text to: {args.output}")
    
    # Test deobfuscation
    if args.deobfuscate:
        print(f"\nDeobfuscated text:")
        print("-" * 60)
        deobfuscated = obfuscator.deobfuscate(result.obfuscated_text)
        print(deobfuscated.strip())
    
    obfuscator.close()

def obfuscate_image_cli(args):
    """Handle image obfuscation command"""
    print("\n" + "=" * 60)
    print("IMAGE OBFUSCATION")
    print("=" * 60)
    
    if not args.input:
        print("Error: --input is required for image obfuscation")
        return
    
    if not args.output:
        # Auto-generate output filename
        input_path = Path(args.input)
        args.output = str(input_path.parent / f"{input_path.stem}_obfuscated{input_path.suffix}")
    
    # Create obfuscators
    text_obfuscator = PIIObfuscator(
        use_regex=args.regex,
        use_spacy=args.spacy,
        use_transformer=args.transformer
    )
    
    img_obfuscator = ImagePIIObfuscator(
        text_obfuscator=text_obfuscator,
        blur_strength=args.blur_strength
    )
    
    # Process image
    print(f"\nProcessing image: {args.input}")
    start_time = time.time()
    
    result = img_obfuscator.obfuscate_image(
        args.input,
        args.output,
        method=args.method
    )
    
    total_time = time.time() - start_time
    
    # Show stats
    print(f"\nStatistics:")
    print("-" * 60)
    print(f"  Redactions: {result['num_redactions']}")
    print(f"  Method: {result['method']}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Output: {args.output}")
    
    if result['redacted_texts'] and not args.no_details:
        print(f"\nRedacted texts:")
        print("-" * 60)
        for item in result['redacted_texts']:
            print(f"  '{item['text']}' at box {item['box']}")
    
    text_obfuscator.close()

def view_stats_cli(args):
    """Show database statistics"""
    print("\n" + "=" * 60)
    print("ESCROW DATABASE STATISTICS")
    print("=" * 60)
    
    obfuscator = PIIObfuscator()
    stats = obfuscator.get_stats()
    
    print(f"\nTotal entries: {stats['total_entries']}")
    print(f"\nBy type:")
    print("-" * 60)
    for type_, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {type_:20}: {count}")
    
    if args.show_entries:
        entries = obfuscator.escrow_db.get_all_entries()
        print(f"\nAll entries (last {min(args.limit, len(entries))}):")
        print("-" * 60)
        for entry in entries[:args.limit]:
            print(f"  {entry.placeholder_id:15} | {entry.entity_type:12} | {entry.original_value:30} | {entry.source}")
    
    obfuscator.close()

def interactive_mode():
    """Interactive text obfuscation mode"""
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("=" * 60)
    print("Enter text to obfuscate. Type 'quit' or 'exit' to exit.")
    print("Type 'stats' to see database statistics.")
    print("=" * 60 + "\n")
    
    obfuscator = PIIObfuscator()
    
    while True:
        try:
            text = input("\nEnter text (or command): ")
            
            if text.lower() in ['quit', 'exit', 'q']:
                break
            
            if text.lower() == 'stats':
                stats = obfuscator.get_stats()
                print(f"\nTotal entries: {stats['total_entries']}")
                for type_, count in stats['by_type'].items():
                    print(f"  {type_:15}: {count}")
                continue
            
            if not text.strip():
                continue
            
            # Obfuscate
            result = obfuscator.obfuscate(text, source="interactive")
            
            print(f"\nObfuscated: {result.obfuscated_text}")
            print(f"Found {result.num_redactions} PII items")
            
            if result.replacements:
                show_detail = input("Show details? (y/n): ")
                if show_detail.lower() == 'y':
                    for placeholder, original in result.replacements.items():
                        print(f"  {placeholder} -> {original}")
        
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    
    print("\n\nExiting...")
    obfuscator.close()

def main():
    parser = argparse.ArgumentParser(
        description="PII Obfuscator - Protect sensitive data in text and images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Obfuscate text from stdin
  python cli.py text --text "Contact John at john@email.com"
  
  # Obfuscate text from file
  python cli.py text --file input.txt --output output.txt
  
  # Obfuscate image
  python cli.py image --input photo.png --output redacted.png --method blur
  
  # View statistics
  python cli.py stats
  
  # Interactive mode
  python cli.py interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Text obfuscation
    text_parser = subparsers.add_parser('text', help='Obfuscate text')
    text_parser.add_argument('--text', type=str, help='Text to obfuscate')
    text_parser.add_argument('--file', type=str, help='Read text from file')
    text_parser.add_argument('--output', type=str, help='Save obfuscated text to file')
    text_parser.add_argument('--source', type=str, default='cli', help='Source identifier')
    text_parser.add_argument('--no-details', action='store_true', help='Hide replacement details')
    text_parser.add_argument('--deobfuscate', action='store_true', help='Also show deobfuscated version')
    text_parser.add_argument('--regex', action='store_true', default=True, help='Use regex detector')
    text_parser.add_argument('--spacy', action='store_true', default=True, help='Use spaCy detector')
    text_parser.add_argument('--transformer', action='store_true', help='Use transformer detector (slower, more accurate)')
    # Consensus mode arguments
    text_parser.add_argument('--consensus', action='store_true', help='Use consensus mode (multi-model ensemble with voting)')
    text_parser.add_argument('--consensus-mode', default='any_two', choices=['any_two', 'majority', 'strict', 'unanimous_structured', 'regex_priority'],
                           help='Consensus threshold (default: any_two, recommended: regex_priority)')
    text_parser.add_argument('--spacy-model', type=str, default='en_core_web_sm', help='spaCy model name')
    
    # Image obfuscation
    image_parser = subparsers.add_parser('image', help='Obfuscate PII in images')
    image_parser.add_argument('--input', '-i', type=str, required=True, help='Input image path')
    image_parser.add_argument('--output', '-o', type=str, help='Output image path')
    image_parser.add_argument('--method', type=str, default='blur', choices=['blur', 'black', 'pixelate'], 
                              help='Obfuscation method')
    image_parser.add_argument('--blur-strength', type=int, default=25, help='Blur strength (odd number)')
    image_parser.add_argument('--no-details', action='store_true', help='Hide redaction details')
    image_parser.add_argument('--regex', action='store_true', default=True)
    image_parser.add_argument('--spacy', action='store_true', default=True)
    image_parser.add_argument('--transformer', action='store_true')
    
    # Stats
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    stats_parser.add_argument('--show-entries', action='store_true', help='Show all entries')
    stats_parser.add_argument('--limit', type=int, default=50, help='Max entries to show')
    
    # Interactive
    subparsers.add_parser('interactive', help='Interactive text obfuscation mode')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'text':
            obfuscate_text_cli(args)
        elif args.command == 'image':
            obfuscate_image_cli(args)
        elif args.command == 'stats':
            view_stats_cli(args)
        elif args.command == 'interactive':
            interactive_mode()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()