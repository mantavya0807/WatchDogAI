"""
Test Desktop App Monitor
Quick verification that desktop app monitoring works.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import time
from desktop_app_monitor import DesktopAppMonitor


def test_basic():
    """Test basic functionality"""
    print("\n" + "=" * 60)
    print("DESKTOP APP MONITOR TEST")
    print("=" * 60)
    print("\nThis will monitor your typing for 60 seconds.")
    print("\nTo test properly:")
    print("1. Open Slack, Teams, Outlook, or Discord")
    print("2. Start typing a message with PII:")
    print("   - 'My email is john@email.com'")
    print("   - 'Contact Alice at 555-123-4567'")
    print("   - 'SSN: 123-45-6789'")
    print("3. Watch as PII gets automatically replaced")
    print("4. See popup with undo option")
    print("\nNOTE: Opens in monitored apps only, not in browsers!\n")
    
    input("Press Enter to start test...")
    
    # Create monitor
    monitor = DesktopAppMonitor(
        buffer_size=500,
        check_interval=1.5,
        enable_replacement=True,
        enable_notifications=True
    )
    
    print("\nMonitoring for 60 seconds...\n")
    
    # Start in a thread with timeout
    import threading
    monitor_thread = threading.Thread(target=monitor.start, daemon=True)
    monitor_thread.start()
    
    # Wait 60 seconds
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    
    # Show stats
    print("\n\nTest complete!")
    monitor.print_stats()
    monitor.close()


def test_replacement():
    """Test PII replacement specifically"""
    print("\n" + "=" * 60)
    print("PII REPLACEMENT TEST")
    print("=" * 60)
    print("\nThis test will run for 90 seconds.")
    print("\nInstructions:")
    print("1. Open Slack or Teams")
    print("2. Type: 'Contact john@email.com or call 555-1234'")
    print("3. Wait 1-2 seconds")
    print("4. Text should auto-replace with placeholders")
    print("5. Popup will show what was hidden")
    print("6. Click 'Undo' to restore original")
    print("\nTry multiple times to see it work!\n")
    
    input("Press Enter to start test...")
    
    monitor = DesktopAppMonitor(
        buffer_size=500,
        check_interval=1.0,  # Check more frequently
        enable_replacement=True,
        enable_notifications=True
    )
    
    print("\nMonitoring for 90 seconds...\n")
    
    import threading
    monitor_thread = threading.Thread(target=monitor.start, daemon=True)
    monitor_thread.start()
    
    try:
        time.sleep(90)
    except KeyboardInterrupt:
        pass
    
    print("\n\nTest complete!")
    monitor.print_stats()
    monitor.close()


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test desktop app monitor")
    parser.add_argument('--basic', action='store_true', help='Run basic test (60s)')
    parser.add_argument('--replacement', action='store_true', help='Test PII replacement (90s)')
    
    args = parser.parse_args()
    
    if args.replacement:
        test_replacement()
    elif args.basic:
        test_basic()
    else:
        # Run basic by default
        test_basic()


if __name__ == "__main__":
    main()