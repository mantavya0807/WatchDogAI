"""
Combined Monitor - Runs clipboard + desktop monitoring together
Notifications are already integrated in both monitors
"""
import threading
import time
from clipboard_monitor_paste_based import FocusBasedClipboardMonitor
from desktop_app_monitor import DesktopAppMonitorV2

print("=" * 70)
print("  PII GUARD - Complete Protection")
print("=" * 70)
print("\nStarting:")
print("  • Clipboard Monitor (copy/paste)")
print("  • Desktop App Monitor (typing)")
print("  • Notifications (built-in)")
print()

# Create monitors
clipboard = FocusBasedClipboardMonitor()
desktop = DesktopAppMonitorV2()

# Run clipboard monitor
def run_clipboard():
    clipboard.start()
    while clipboard.running:
        time.sleep(1)

# Run desktop monitor
def run_desktop():
    desktop.start()
    while desktop.running:
        time.sleep(1)

# Start both in threads
clipboard_thread = threading.Thread(target=run_clipboard, daemon=True)
desktop_thread = threading.Thread(target=run_desktop, daemon=True)

clipboard_thread.start()
time.sleep(0.5)
desktop_thread.start()
time.sleep(0.5)

print("✓ All monitors running!")
print("\nPress Ctrl+C to stop")
print("=" * 70)
print()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nStopping monitors...")
    clipboard.stop()
    desktop.stop()
    clipboard_thread.join(timeout=2)
    desktop_thread.join(timeout=2)
    print("\n✓ Stopped")
    clipboard.print_stats()
    desktop.print_stats()