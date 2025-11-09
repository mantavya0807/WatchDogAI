#!/usr/bin/env python3
"""
PII Guard - Unified Startup Script
Starts all system-level monitors and services
"""
import sys
import threading
import time
import signal
from pathlib import Path

# Import monitors
from clipboard_monitor_paste_based import FocusBasedClipboardMonitor
from desktop_app_monitor import DesktopAppMonitorV2
from placeholder_restoration_monitor import PlaceholderRestorationMonitor

# Amplitude tracking (optional)
try:
    sys.path.insert(0, str(Path(__file__).parent / 'amplitude_integration'))
    from integration_helper import get_amplitude_tracker
    AMPLITUDE_TRACKING_AVAILABLE = True
except Exception:
    AMPLITUDE_TRACKING_AVAILABLE = False

# Global references for cleanup
monitors = {}
amplitude_tracker = None
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n\n🛑 Shutting down all monitors...")
    running = False
    
    # Stop all monitors
    for name, monitor in monitors.items():
        if monitor and hasattr(monitor, 'stop'):
            try:
                monitor.stop()
            except:
                pass
    
    # Stop Amplitude tracker
    if amplitude_tracker:
        try:
            amplitude_tracker.stop()
        except:
            pass
    
    print("✓ All monitors stopped")
    sys.exit(0)

def run_clipboard_monitor():
    """Run clipboard monitor in thread"""
    try:
        monitors['clipboard'].start()
        while monitors['clipboard'].running and running:
            time.sleep(1)
    except Exception as e:
        print(f"❌ Clipboard monitor error: {e}")

def run_desktop_monitor():
    """Run desktop app monitor in thread"""
    try:
        monitors['desktop'].start()
        while monitors['desktop'].running and running:
            time.sleep(1)
    except Exception as e:
        print(f"❌ Desktop monitor error: {e}")

def run_restoration_monitor():
    """Run placeholder restoration monitor in thread"""
    try:
        monitors['restoration'].start()
        while monitors['restoration'].running and running:
            time.sleep(1)
    except Exception as e:
        print(f"❌ Restoration monitor error: {e}")

def main():
    """Main entry point"""
    global monitors, amplitude_tracker
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 70)
    print("  🛡️  PII GUARD - Complete Protection System")
    print("=" * 70)
    print()
    print("Starting all monitors:")
    print("  ✓ Clipboard Monitor (copy/paste protection)")
    print("  ✓ Desktop App Monitor (typing protection)")
    print("  ✓ Placeholder Restoration (clipboard restoration)")
    print("  ✓ Notifications (built-in)")
    print()
    
    # Initialize Amplitude tracker if available
    if AMPLITUDE_TRACKING_AVAILABLE:
        try:
            amplitude_tracker = get_amplitude_tracker()
            if amplitude_tracker:
                print("  ✓ Amplitude tracking enabled")
        except Exception as e:
            print(f"  ⚠ Amplitude tracking unavailable: {e}")
    
    print()
    print("=" * 70)
    print()
    
    # Initialize monitors
    try:
        monitors['clipboard'] = FocusBasedClipboardMonitor()
        monitors['desktop'] = DesktopAppMonitorV2()
        monitors['restoration'] = PlaceholderRestorationMonitor()
    except Exception as e:
        print(f"❌ Failed to initialize monitors: {e}")
        sys.exit(1)
    
    # Start monitors in separate threads
    clipboard_thread = threading.Thread(target=run_clipboard_monitor, daemon=True)
    desktop_thread = threading.Thread(target=run_desktop_monitor, daemon=True)
    restoration_thread = threading.Thread(target=run_restoration_monitor, daemon=True)
    
    clipboard_thread.start()
    time.sleep(0.5)
    desktop_thread.start()
    time.sleep(0.5)
    restoration_thread.start()
    time.sleep(0.5)
    
    print("✓ All monitors running!")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    # Keep main thread alive
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)
    
    # Print stats before exit
    print()
    print("=" * 70)
    print("STATISTICS")
    print("=" * 70)
    for name, monitor in monitors.items():
        if monitor and hasattr(monitor, 'print_stats'):
            try:
                monitor.print_stats()
            except:
                pass

if __name__ == "__main__":
    main()

