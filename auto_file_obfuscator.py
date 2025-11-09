"""
Automatic File Obfuscator
Watches a directory and automatically obfuscates files when they're created or modified.
Perfect for automatically obfuscating files before uploading to ChatGPT.
"""

import sys
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_servers.unified_server import check_file
from mcp_client import cmd_check
import argparse


class FileObfuscationHandler(FileSystemEventHandler):
    """Watch for file changes and automatically obfuscate"""
    
    def __init__(self, watch_dir, output_dir=None, auto_replace=False):
        self.watch_dir = Path(watch_dir)
        self.output_dir = Path(output_dir) if output_dir else self.watch_dir / "obfuscated"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.auto_replace = auto_replace
        self.processed_files = set()
        
        print(f"Watching: {self.watch_dir}")
        print(f"Output: {self.output_dir}")
        print(f"Auto-replace: {auto_replace}")
        print("=" * 70)
    
    def on_created(self, event):
        """Handle file creation"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        self.process_file(file_path)
    
    def on_modified(self, event):
        """Handle file modification"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        # Avoid processing the same file multiple times
        if file_path in self.processed_files:
            return
        
        self.process_file(file_path)
    
    def process_file(self, file_path):
        """Process a file and obfuscate it"""
        try:
            # Check if file is supported
            ext = file_path.suffix.lower()
            supported = ['.py', '.js', '.java', '.cpp', '.c', '.ts', '.go', '.rs',
                         '.pdf', '.docx', '.doc', '.txt']
            
            if ext not in supported:
                return
            
            print(f"\n📄 Detected file: {file_path.name}")
            
            # Check if it's already obfuscated
            if '_safe' in file_path.stem or file_path.parent == self.output_dir:
                return
            
            # Obfuscate the file
            print(f"🔒 Obfuscating {file_path.name}...")
            
            if self.auto_replace:
                # Replace original with obfuscated version
                output_path = file_path
            else:
                # Save to output directory
                output_path = self.output_dir / f"{file_path.stem}_safe{file_path.suffix}"
            
            # Use unified server to obfuscate
            result = check_file(str(file_path))
            
            if result.get('error'):
                print(f"❌ Error: {result['error']}")
                return
            
            if result.get('pii_found', 0) > 0:
                print(f"✅ Found {result['pii_found']} PII items")
                
                # Save obfuscated file
                if 'safe_docx' in result and result['safe_docx']:
                    result['safe_docx'].save(str(output_path))
                    result['safe_docx'].close()
                elif 'safe_pdf' in result and result['safe_pdf']:
                    result['safe_pdf'].save(str(output_path))
                    result['safe_pdf'].close()
                elif 'safe_text' in result:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(result['safe_text'])
                
                print(f"✅ Saved: {output_path}")
                
                if self.auto_replace:
                    print(f"⚠️  Original file replaced with obfuscated version")
            else:
                print(f"ℹ️  No PII found in {file_path.name}")
            
            self.processed_files.add(file_path)
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            import traceback
            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Automatically obfuscate files when created or modified",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch current directory, save obfuscated files to ./obfuscated/
  python auto_file_obfuscator.py --watch .
  
  # Watch specific directory
  python auto_file_obfuscator.py --watch ~/Downloads
  
  # Auto-replace original files (be careful!)
  python auto_file_obfuscator.py --watch . --auto-replace
  
  # Custom output directory
  python auto_file_obfuscator.py --watch . --output ~/SafeFiles
        """
    )
    
    parser.add_argument('--watch', '-w', 
                       default='.',
                       help='Directory to watch (default: current directory)')
    parser.add_argument('--output', '-o',
                       help='Output directory for obfuscated files (default: watch_dir/obfuscated)')
    parser.add_argument('--auto-replace', '-r',
                       action='store_true',
                       help='Replace original files with obfuscated versions (DANGEROUS!)')
    
    args = parser.parse_args()
    
    watch_dir = Path(args.watch).resolve()
    if not watch_dir.exists():
        print(f"❌ Error: Directory does not exist: {watch_dir}")
        sys.exit(1)
    
    if not watch_dir.is_dir():
        print(f"❌ Error: Not a directory: {watch_dir}")
        sys.exit(1)
    
    # Check if watchdog is installed
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("❌ Error: watchdog not installed")
        print("Install it with: pip install watchdog")
        sys.exit(1)
    
    # Create handler
    event_handler = FileObfuscationHandler(
        watch_dir=watch_dir,
        output_dir=args.output,
        auto_replace=args.auto_replace
    )
    
    # Create observer
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=True)
    observer.start()
    
    print("\n✅ File watcher started!")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopping file watcher...")
        observer.stop()
    
    observer.join()
    print("✅ File watcher stopped")


if __name__ == '__main__':
    main()

