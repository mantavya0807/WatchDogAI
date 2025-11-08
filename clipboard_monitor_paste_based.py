"""
Paste-Based Clipboard Monitor - FOCUS-BASED APPROACH
=====================================================

SMART STRATEGY (No admin privileges needed):
1. On COPY: Detect PII, store both versions
2. Monitor active window every 100ms
3. If dangerous app has focus: Keep clipboard obfuscated
4. If safe app has focus: Keep clipboard original

This way:
- No keyboard hooks needed (no admin privileges)
- Clipboard is always correct for current app
- User can paste freely with Ctrl+V
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import win32clipboard
import win32con
import win32gui
import win32process
import psutil
import threading
import time
import traceback

from obfuscator import PIIObfuscator
from notification_system import show_pii_notification
from preference_gui import PreferencesManager


class FocusBasedClipboardMonitor:
    """
    Focus-based clipboard monitor.
    
    Strategy:
    - Monitor which app has focus
    - If dangerous app focused: Clipboard = obfuscated
    - If safe app focused: Clipboard = original
    - User can paste normally with Ctrl+V
    """
    
    DANGEROUS_APPS = {
        'slack.exe': 'Slack',
        'discord.exe': 'Discord',
        'teams.exe': 'Microsoft Teams',
        'telegram.exe': 'Telegram Desktop',
        'whatsapp.exe': 'WhatsApp Desktop',
        'signal.exe': 'Signal',
        'skype.exe': 'Skype',
        'outlook.exe': 'Outlook Desktop',
        'thunderbird.exe': 'Thunderbird',
    }
    
    def __init__(self):
        print("=" * 60)
        print("PII GUARD - FOCUS-BASED CLIPBOARD MONITOR")
        print("No admin privileges needed!")
        print("=" * 60)
        
        self.prefs_manager = PreferencesManager()
        print("✓ Loaded preferences")
        
        self.clipboard_cache = {
            'original': None,
            'obfuscated': None,
            'has_pii': False,
            'num_items': 0,
        }
        
        self.text_obfuscator = None
        self.running = False
        
        # Track current clipboard state
        self.clipboard_is_obfuscated = False
        self.last_focused_app = None
        
        self.last_clipboard_seq = 0
        self.processing = False
        
        self.stats = {
            'copies_monitored': 0,
            'clipboard_swaps': 0,
            'dangerous_app_focused': 0,
            'safe_app_focused': 0,
            'pii_items_detected': 0,
        }
        
        print("✓ Monitor initialized")
        print("=" * 60)
    
    def _get_clipboard_sequence(self):
        try:
            return win32clipboard.GetClipboardSequenceNumber()
        except:
            return 0
    
    def _get_clipboard_text(self):
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    return text
            finally:
                win32clipboard.CloseClipboard()
        except:
            pass
        return None
    
    def _set_clipboard_text(self, text):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            return False
    
    def _get_active_window_info(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            
            process_name = process.name().lower()
            window_title = win32gui.GetWindowText(hwnd)
            
            return {
                'process': process_name,
                'title': window_title,
            }
        except:
            return None
    
    def _is_dangerous_app(self, process_name):
        """Check if process is dangerous"""
        if process_name in self.DANGEROUS_APPS:
            return True, self.DANGEROUS_APPS[process_name]
        
        whitelist = self.prefs_manager.get('whitelist.apps', [])
        if process_name in whitelist:
            return False, f"Whitelisted"
        
        return False, process_name
    
    def _monitor_clipboard_changes(self):
        """Monitor clipboard for copies"""
        print("\n✓ Clipboard monitor started")
        print("Initializing obfuscator in monitoring thread...")
        
        use_regex = self.prefs_manager.get('detectors.regex', True)
        use_spacy = self.prefs_manager.get('detectors.spacy', True)
        use_transformer = self.prefs_manager.get('detectors.transformer', True)
        spacy_model = self.prefs_manager.get('advanced.spacy_model', 'en_core_web_sm')
        transformer_model = self.prefs_manager.get('advanced.transformer_model', 'lakshyakh93/deberta_finetuned_pii')
        
        print(f"  Transformer: {'✓' if use_transformer else '✗'}")
        print(f"  spaCy: {'✓' if use_spacy else '✗'}")
        print(f"  Regex: {'✓' if use_regex else '✗'}")
        
        self.text_obfuscator = PIIObfuscator(
            use_regex=use_regex,
            use_spacy=use_spacy,
            use_transformer=use_transformer,
            transformer_model=transformer_model,
            spacy_model=spacy_model,
        )
        
        print("✓ Obfuscator initialized\n")
        
        while self.running:
            try:
                current_seq = self._get_clipboard_sequence()
                
                if current_seq != self.last_clipboard_seq and not self.processing:
                    self.last_clipboard_seq = current_seq
                    
                    # Only process if clipboard changed by user (not by us)
                    if not self.processing:
                        self._on_copy_detected()
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in clipboard monitor: {e}")
    
    def _on_copy_detected(self):
        """User copied something - detect PII"""
        self.processing = True
        
        try:
            text = self._get_clipboard_text()
            if not text or len(text.strip()) < 10:
                self.clipboard_cache = {
                    'original': None,
                    'obfuscated': None,
                    'has_pii': False,
                    'num_items': 0,
                }
                self.clipboard_is_obfuscated = False
                return
            
            # Detect PII
            import time
            start_time = time.time()
            result = self.text_obfuscator.obfuscate(text, source="clipboard")
            detection_time = (time.time() - start_time) * 1000
            
            # Store both versions
            self.clipboard_cache = {
                'original': text,
                'obfuscated': result.obfuscated_text,
                'has_pii': result.num_redactions > 0,
                'num_items': result.num_redactions,
                'replacements': result.replacements,
            }
            
            self.clipboard_is_obfuscated = False  # User copied original
            self.stats['copies_monitored'] += 1
            
            if result.num_redactions > 0:
                self.stats['pii_items_detected'] += result.num_redactions
                print(f"\n📋 COPY: Detected {result.num_redactions} PII items ({detection_time:.0f}ms)")
                print(f"   Clipboard will auto-adjust based on active app")
            
        except Exception as e:
            print(f"Error detecting PII: {e}")
        finally:
            self.processing = False
    
    def _monitor_focus_changes(self):
        """Monitor which app has focus and adjust clipboard"""
        print("✓ Focus monitor started\n")
        
        last_app = None
        
        while self.running:
            try:
                # Don't adjust clipboard while processing copy
                if self.processing:
                    time.sleep(0.1)
                    continue
                
                # Get focused app
                window_info = self._get_active_window_info()
                if not window_info:
                    time.sleep(0.1)
                    continue
                
                current_app = window_info['process']
                
                # Check if app changed
                if current_app != last_app:
                    last_app = current_app
                    
                    # Check if current app is dangerous
                    is_dangerous, app_name = self._is_dangerous_app(current_app)
                    
                    # Only adjust if we have PII to protect
                    if self.clipboard_cache.get('has_pii', False):
                        
                        if is_dangerous and not self.clipboard_is_obfuscated:
                            # Switched to dangerous app - obfuscate clipboard
                            print(f"\n🔒 Switched to {app_name} → Obfuscating clipboard")
                            self.processing = True
                            self._set_clipboard_text(self.clipboard_cache['obfuscated'])
                            self.clipboard_is_obfuscated = True
                            self.stats['clipboard_swaps'] += 1
                            self.stats['dangerous_app_focused'] += 1
                            self.processing = False
                            
                        elif not is_dangerous and self.clipboard_is_obfuscated:
                            # Switched to safe app - restore original
                            print(f"\n✓ Switched to safe app → Restoring original")
                            self.processing = True
                            self._set_clipboard_text(self.clipboard_cache['original'])
                            self.clipboard_is_obfuscated = False
                            self.stats['clipboard_swaps'] += 1
                            self.stats['safe_app_focused'] += 1
                            self.processing = False
                
                time.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                print(f"Error in focus monitor: {e}")
                time.sleep(0.1)
    
    def start(self):
        if self.running:
            print("⚠ Monitor already running")
            return
        
        if self.prefs_manager.get('notifications.enabled', True):
            from notification_system import get_notification_manager
            notification_thread = threading.Thread(
                target=lambda: get_notification_manager().start(),
                daemon=True
            )
            notification_thread.start()
            time.sleep(0.5)
            print("✓ Notification system started\n")
        
        self.running = True
        
        # Start clipboard monitor
        clipboard_thread = threading.Thread(target=self._monitor_clipboard_changes, daemon=True)
        clipboard_thread.start()
        
        # Start focus monitor
        focus_thread = threading.Thread(target=self._monitor_focus_changes, daemon=True)
        focus_thread.start()
        
        time.sleep(1.5)
        
        print("=" * 60)
        print("✓ FOCUS-BASED MONITOR ACTIVE")
        print("=" * 60)
        print("\n🎯 SMART CLIPBOARD:")
        print("  1. Copy text with PII → Detected in background")
        print("  2. Switch to Slack → Clipboard auto-obfuscated")
        print("  3. Switch to Excel → Clipboard auto-restored")
        print("  4. Paste normally with Ctrl+V")
        print("\n⚡ How it works:")
        print("  • Monitors which app has focus (every 100ms)")
        print("  • Auto-adjusts clipboard based on app safety")
        print("  • No keyboard hooks = no admin privileges needed")
        print("\n🎯 Dangerous apps:")
        for app in list(self.DANGEROUS_APPS.values())[:6]:
            print(f"  • {app}")
        print("\n  Press Ctrl+C to stop\n")
        print("=" * 60 + "\n")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nInterrupted")
    
    def stop(self):
        if not self.running:
            return
        
        print("\nStopping monitor...")
        self.running = False
        
        # Restore original if obfuscated
        if self.clipboard_is_obfuscated and self.clipboard_cache.get('original'):
            print("Restoring original clipboard...")
            self._set_clipboard_text(self.clipboard_cache['original'])
        
        if self.text_obfuscator:
            try:
                self.text_obfuscator.close()
            except:
                pass
        
        print("✓ Monitor stopped")
    
    def print_stats(self):
        print("\n" + "=" * 60)
        print("STATISTICS")
        print("=" * 60)
        print(f"  Copies monitored: {self.stats['copies_monitored']}")
        print(f"  Clipboard swaps: {self.stats['clipboard_swaps']}")
        print(f"  Dangerous app switches: {self.stats['dangerous_app_focused']}")
        print(f"  Safe app switches: {self.stats['safe_app_focused']}")
        print(f"  Total PII items detected: {self.stats['pii_items_detected']}")
        print("=" * 60)


def main():
    monitor = FocusBasedClipboardMonitor()
    
    try:
        monitor.start()
    finally:
        monitor.stop()
        monitor.print_stats()


if __name__ == "__main__":
    main()