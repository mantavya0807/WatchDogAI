"""
ALL-IN-ONE: Project Cleanup & Organization
This script does everything:
1. Backs up current state
2. Deletes redundant files
3. Copies new organized files
4. Runs verification
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Project paths
PROJECT_ROOT = Path(r"D:\Projects\HackPrinceton")
SCRIPT_DIR = Path(__file__).parent

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70)

def backup_project():
    """Create a complete backup before making changes"""
    print_header("CREATING BACKUP")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = PROJECT_ROOT / f"backup_{timestamp}"
    
    print(f"Backup location: {backup_dir}")
    
    try:
        # Create backup
        shutil.copytree(PROJECT_ROOT, backup_dir, 
                       ignore=shutil.ignore_patterns('venv', 'env', '__pycache__', '*.pyc', 'backup_*'))
        print(f"✓ Backup created successfully")
        return backup_dir
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        return None

def cleanup_files():
    """Remove redundant files"""
    print_header("REMOVING REDUNDANT FILES")
    
    # Files to delete
    files_to_delete = [
        "ARCHITECTURAL_CHANGES.md",
        "ARCHITECTURE.md",
        "CHANGES_SUMMARY.md",
        "CHECKLIST.md",
        "CONSENSUS_IMPLEMENTATION.md",
        "CONSENSUS_MODE.md",
        "GETTING_STARTED.md",
        "IMPLEMENTATION_COMPLETE.md",
        "IMPLEMENTATION_SUMMARY.md",
        "Instructions",
        "Notification_Summary.md",
        "QUICK_START_UPDATED.md",
        "REGEX_PRIORITY_MODE.md",
        "SETUP_GUIDE.md",
        "START_HERE.md",
        "_AutomationLog.txt",
        "Readme.md",
        "employee_record.txt",
        "employee_record_safe_final.txt",
        "test_export.json",
        "test_architectural_changes.py",
        "test_clipboard.py",
        "test_keystroke.py",
        "test_model_download.py",
        "test_transformer_first.py",
        "test_pii_image_blurred.png",
        "test_pii_image_pixelated.png",
        "test_pii_image_preview.png",
        "test_pii_image_redacted.png",
        "keystroke_monitor.py",
        "quickstart.py",
        "tray_desktop_monitor.py",
    ]
    
    deleted = 0
    for filename in files_to_delete:
        filepath = PROJECT_ROOT / filename
        if filepath.exists():
            try:
                if filepath.is_file():
                    filepath.unlink()
                else:
                    shutil.rmtree(filepath)
                print(f"✓ Deleted: {filename}")
                deleted += 1
            except Exception as e:
                print(f"✗ Failed to delete {filename}: {e}")
        else:
            print(f"⊘ Not found: {filename}")
    
    print(f"\nTotal deleted: {deleted} files")
    return deleted

def copy_new_files():
    """Copy new organized files to project"""
    print_header("COPYING NEW FILES")
    
    new_files = [
        "README.md",
        "requirements.txt",
        "setup.py",
        ".gitignore",
        "DEMO_GUIDE.md",
    ]
    
    copied = 0
    for filename in new_files:
        src = SCRIPT_DIR / filename
        dst = PROJECT_ROOT / filename
        
        if src.exists():
            try:
                shutil.copy2(src, dst)
                print(f"✓ Copied: {filename}")
                copied += 1
            except Exception as e:
                print(f"✗ Failed to copy {filename}: {e}")
        else:
            print(f"⊘ Source not found: {filename}")
    
    print(f"\nTotal copied: {copied} files")
    return copied

def create_project_structure():
    """Create organized directory structure"""
    print_header("ORGANIZING DIRECTORY STRUCTURE")
    
    # Create directories if they don't exist
    dirs_to_create = [
        "data",
        "docs",
        "tests",
    ]
    
    for dir_name in dirs_to_create:
        dir_path = PROJECT_ROOT / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"✓ Created/verified: {dir_name}/")
    
    # Move test files to tests/ directory
    test_files = ["test_integration.py", "test_consensus.py", "verify_installation.py"]
    for test_file in test_files:
        src = PROJECT_ROOT / test_file
        dst = PROJECT_ROOT / "tests" / test_file
        if src.exists() and src != dst:
            try:
                shutil.move(str(src), str(dst))
                print(f"✓ Moved: {test_file} → tests/")
            except Exception as e:
                print(f"⊘ Could not move {test_file}: {e}")

def show_project_summary():
    """Show final project structure"""
    print_header("PROJECT STRUCTURE SUMMARY")
    
    print("""
Root Directory (Core Modules):
  • obfuscator.py              - Main obfuscation engine
  • regex_detector.py          - Pattern-based detection
  • spacy_detector.py          - Named entity recognition
  • transformer_detector.py    - AI context-aware detection
  • consensus_detector.py      - Multi-model voting
  • clipboard_monitor_paste_based.py  - Clipboard protection
  • desktop_app_monitor.py     - Desktop app monitoring
  • notification_system.py     - Toast notifications
  • preference_gui.py          - Configuration GUI
  • escrow_db.py              - Database for original values
  • image_obfuscator.py       - Image PII processing
  • cli.py                    - Command-line interface

Configuration:
  • pii_guard_config.json     - User preferences
  • start_combined.ps1        - Launcher script

Documentation:
  • README.md                 - Comprehensive guide
  • DEMO_GUIDE.md             - Presentation script
  • requirements.txt          - Dependencies
  • setup.py                  - Installation script
  • .gitignore               - Git configuration

Tests (tests/):
  • test_integration.py       - Full system test
  • test_consensus.py         - Consensus mode test
  • verify_installation.py    - Setup verification

Data (data/):
  • escrow.db                - Escrow database (auto-created)
  • pii_guard_config.json    - User config (if moved)

Sample Images:
  • test_pii_image.png       - Example image (1 kept for demo)
    """)

def run_verification():
    """Run verification tests"""
    print_header("RUNNING VERIFICATION")
    
    print("Testing installation...")
    try:
        import subprocess
        result = subprocess.run(
            ["python", str(PROJECT_ROOT / "tests" / "verify_installation.py")],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(result.stdout)
        if result.returncode == 0:
            print("✓ Verification passed!")
        else:
            print("⚠ Verification had warnings")
            print(result.stderr)
    except Exception as e:
        print(f"⚠ Could not run verification: {e}")
        print("Please run manually: python tests/verify_installation.py")

def main():
    """Main cleanup and organization process"""
    
    print_header("PII GUARD - PROJECT CLEANUP & ORGANIZATION")
    
    print("""
This script will:
  1. Create a complete backup of your project
  2. Delete redundant documentation and test files
  3. Copy new organized files (README, setup, etc.)
  4. Organize directory structure (tests/ directory)
  5. Run verification tests

Your project will be cleaner, better organized, and easier to present!
    """)
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Cleanup cancelled.")
        return
    
    # Step 1: Backup
    backup_dir = backup_project()
    if backup_dir is None:
        print("✗ Backup failed! Aborting for safety.")
        return
    
    # Step 2: Cleanup
    deleted_count = cleanup_files()
    
    # Step 3: Copy new files
    copied_count = copy_new_files()
    
    # Step 4: Organize structure
    create_project_structure()
    
    # Step 5: Show summary
    show_project_summary()
    
    # Step 6: Verification
    run_verification()
    
    # Final summary
    print_header("CLEANUP COMPLETE!")
    
    print(f"""
✓ Files deleted: {deleted_count}
✓ Files added: {copied_count}
✓ Backup location: {backup_dir}

Your project is now organized and ready for HackPrinceton!

Next steps:
  1. Review the new README.md
  2. Run: python setup.py (if first time)
  3. Test: python tests/test_integration.py
  4. Demo: python clipboard_monitor_paste_based.py

If anything goes wrong, restore from backup:
  {backup_dir}

Good luck at HackPrinceton! 🚀
    """)

if __name__ == "__main__":
    main()
