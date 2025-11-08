"""
Test Clipboard Monitor
Quick verification that clipboard monitoring works.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import win32clipboard
import win32con
import time
from clipboard_monitor import ClipboardMonitor


def set_clipboard_text(text):
    """Set clipboard text for testing"""
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()
    time.sleep(0.2)  # Give monitor time to process


def get_clipboard_text():
    """Get clipboard text for verification"""
    win32clipboard.OpenClipboard()
    try:
        return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()


def test_text_monitoring():
    """Test text monitoring functionality"""
    print("\n" + "=" * 60)
    print("TEST: Text Monitoring")
    print("=" * 60)
    
    test_cases = [
        {
            'name': 'Email detection',
            'input': 'Contact me at john.doe@email.com',
            'should_contain': '{EMAIL_'
        },
        {
            'name': 'Phone detection',
            'input': 'Call me at (555) 123-4567',
            'should_contain': '{PHONE_'
        },
        {
            'name': 'Person name detection',
            'input': 'John Smith works at Google',
            'should_contain': '{PERSON_'
        },
        {
            'name': 'SSN detection',
            'input': 'SSN: 123-45-6789',
            'should_contain': '{SSN_'
        },
        {
            'name': 'No PII (should not change)',
            'input': 'Hello world, this is a test',
            'should_contain': 'Hello world'
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print(f"  Input: {test['input']}")
        
        # Set clipboard
        set_clipboard_text(test['input'])
        
        # Get result
        result = get_clipboard_text()
        print(f"  Output: {result}")
        
        # Check if expected content is present
        if test['should_contain'] in result:
            print("  ✓ PASS")
            results.append(True)
        else:
            print("  ✗ FAIL")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


def test_monitor_lifecycle():
    """Test monitor start/stop/stats"""
    print("\n" + "=" * 60)
    print("TEST: Monitor Lifecycle")
    print("=" * 60)
    
    # Create monitor
    print("\n1. Creating monitor...")
    monitor = ClipboardMonitor(enable_text=True, enable_images=False)
    print("   ✓ Monitor created")
    
    # Start
    print("\n2. Starting monitor...")
    monitor.start()
    time.sleep(1)  # Give it time to initialize
    
    if monitor.running:
        print("   ✓ Monitor is running")
    else:
        print("   ✗ Monitor failed to start")
        return False
    
    # Process some text
    print("\n3. Testing with sample data...")
    test_text = "Contact Alice at alice@email.com or call 555-1234"
    set_clipboard_text(test_text)
    time.sleep(0.5)
    
    result = get_clipboard_text()
    if '{EMAIL_' in result or '{PHONE_' in result or '{PERSON_' in result:
        print("   ✓ PII detected and obfuscated")
    else:
        print("   ⚠ No PII detected (this might be okay)")
    
    # Check stats
    print("\n4. Checking statistics...")
    monitor.print_stats()
    
    # Stop
    print("\n5. Stopping monitor...")
    monitor.stop()
    time.sleep(0.5)
    
    if not monitor.running:
        print("   ✓ Monitor stopped successfully")
    else:
        print("   ✗ Monitor failed to stop")
        return False
    
    print("\n" + "=" * 60)
    print("✓ Lifecycle test complete")
    print("=" * 60)
    
    return True


def interactive_test():
    """Interactive test - manually copy text and see results"""
    print("\n" + "=" * 60)
    print("INTERACTIVE TEST")
    print("=" * 60)
    print("\nStarting clipboard monitor...")
    print("Try copying text with PII from any application")
    print("The clipboard will be automatically obfuscated")
    print("\nExamples to try:")
    print("  - Email addresses")
    print("  - Phone numbers")
    print("  - Names")
    print("  - SSNs")
    print("\nPress Ctrl+C to stop\n")
    
    # Create and start monitor
    monitor = ClipboardMonitor(enable_text=True, enable_images=True)
    monitor.start()
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    
    finally:
        monitor.stop()
        monitor.print_stats()


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test clipboard monitor")
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Run interactive test (manually copy text)')
    parser.add_argument('--lifecycle', '-l', action='store_true',
                       help='Test monitor start/stop')
    parser.add_argument('--all', '-a', action='store_true',
                       help='Run all automated tests')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_test()
        return
    
    # Create and start monitor for automated tests
    print("=" * 60)
    print("CLIPBOARD MONITOR AUTOMATED TESTS")
    print("=" * 60)
    
    print("\nStarting monitor in background...")
    monitor = ClipboardMonitor(enable_text=True, enable_images=False)
    monitor.start()
    time.sleep(2)  # Give monitor time to initialize
    
    try:
        # Run tests
        if args.lifecycle or args.all:
            # Don't start new monitor for lifecycle test
            pass
        
        if args.all or not args.lifecycle:
            test_text_monitoring()
        
        if args.lifecycle:
            monitor.stop()
            time.sleep(1)
            test_monitor_lifecycle()
    
    finally:
        if monitor.running:
            print("\n\nCleaning up...")
            monitor.stop()
            monitor.print_stats()


if __name__ == "__main__":
    main()