"""
Combined Monitor - Runs clipboard + desktop monitoring together
Notifications are already integrated in both monitors
"""
import threading
import time
import sys
from pathlib import Path
from clipboard_monitor_paste_based import FocusBasedClipboardMonitor
from desktop_app_monitor import DesktopAppMonitorV2
from preference_gui import PreferencesManager

# Amplitude tracking integration
try:
    sys.path.insert(0, str(Path(__file__).parent / 'amplitude_integration'))
    from amplitude_tracker import get_tracker
    from integration_helper import get_amplitude_tracker
    AMPLITUDE_TRACKING_AVAILABLE = True
except Exception as e:
    AMPLITUDE_TRACKING_AVAILABLE = False
    print(f"⚠ Amplitude tracking not available: {e}")

print("=" * 70)
print("  PII GUARD - Complete Protection")
print("=" * 70)
print("\nStarting:")
print("  • Clipboard Monitor (copy/paste)")
print("  • Desktop App Monitor (typing)")
print("  • Notifications (built-in)")
print()

# Initialize Amplitude tracker and track system start
amplitude_tracker = None
if AMPLITUDE_TRACKING_AVAILABLE:
    try:
        amplitude_tracker = get_amplitude_tracker()
        if amplitude_tracker:
            # Track system start
            prefs_manager = PreferencesManager()
            detectors_enabled = []
            if prefs_manager.get('detectors.regex', False):
                detectors_enabled.append('regex')
            if prefs_manager.get('detectors.spacy', False):
                detectors_enabled.append('spacy')
            if prefs_manager.get('detectors.transformer', True):
                detectors_enabled.append('transformer')
            
            sources_enabled = []
            if prefs_manager.get('sources.clipboard', True):
                sources_enabled.append('clipboard')
            if prefs_manager.get('sources.typing', True):
                sources_enabled.append('typing')
            
            amplitude_tracker.track_system_start(detectors_enabled, sources_enabled)
            amplitude_tracker.flush()
            print("✓ Amplitude tracking initialized")
    except Exception as e:
        print(f"⚠ Amplitude tracking error: {e}")

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
    
    # Stop Amplitude tracker
    if amplitude_tracker:
        try:
            amplitude_tracker.stop()
        except:
            pass
    
    print("\n✓ Stopped")
    clipboard.print_stats()
    desktop.print_stats()