"""
Desktop App Monitor V2 - Fixed infinite loop & cursor position
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import uiautomation as auto
from pynput import keyboard
from pynput.keyboard import Key
import win32gui
import win32process
import psutil
import threading
import time
import re

from notification_system import show_pii_notification
from preference_gui import PreferencesManager

# Amplitude tracking integration
try:
    sys.path.insert(0, str(Path(__file__).parent / 'amplitude_integration'))
    from integration_helper import get_amplitude_tracker, track_pii_detection_from_result, track_user_undo
    AMPLITUDE_TRACKING_AVAILABLE = True
except Exception as e:
    AMPLITUDE_TRACKING_AVAILABLE = False
    print(f"⚠ Amplitude tracking not available: {e}")


class DesktopAppMonitorV2:
    """
    PII replacement monitor using Windows UI Automation.
    Fixed: Infinite loop prevention & cursor preservation
    """
    
    MONITORED_APPS = {
        'slack.exe': 'Slack',
        'teams.exe': 'Microsoft Teams',
        'outlook.exe': 'Outlook',
        'discord.exe': 'Discord',
        'skype.exe': 'Skype',
        'zoom.exe': 'Zoom',
    }
    
    # Pattern to detect our placeholders
    PLACEHOLDER_PATTERN = re.compile(r'\{[A-Z_]+_\d+\}')
    
    def __init__(self):
        print("=" * 60)
        print("PII GUARD - DESKTOP MONITOR V2")
        print("=" * 60)
        
        # Load preferences
        self.prefs_manager = PreferencesManager()
        print("✓ Loaded preferences")
        
        self.pause_threshold = 1.5
        
        # Track typing activity
        self.last_keystroke_time = time.time()
        self.is_typing = False
        self.check_scheduled = False  # NEW: Track if check is already scheduled
        
        # Obfuscator (initialized in monitor thread)
        self.obfuscator = None
        self.obfuscator_initialized = False
        
        # State
        self.last_processed_text = None
        self.last_original_text = None  # For undo
        self.last_element = None  # Store element for undo
        self.processing = False
        
        # Stats
        self.stats = {
            'keystrokes': 0,
            'replacements': 0,
            'pii_items': 0
        }
        
        # Initialize Amplitude tracker
        self.amplitude_tracker = None
        if AMPLITUDE_TRACKING_AVAILABLE:
            try:
                self.amplitude_tracker = get_amplitude_tracker()
                if self.amplitude_tracker:
                    print("✓ Amplitude tracking enabled")
            except:
                pass
        
        print("✓ Initialized")
        print("=" * 60)
    
    def get_active_app(self):
        """Get active app name"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name()
        except:
            return None
    
    def is_monitored_app(self, app_name):
        """Check if app should be monitored"""
        # Check if typing protection is enabled
        if not self.prefs_manager.get('sources.typing', True):
            return False
        
        # Check if app is whitelisted
        whitelist_apps = self.prefs_manager.get('whitelist.apps', [])
        if app_name in whitelist_apps:
            return False
        
        return app_name in self.MONITORED_APPS
    
    def has_placeholders(self, text):
        """Check if text already contains our placeholders"""
        return bool(self.PLACEHOLDER_PATTERN.search(text))
    
    def get_focused_text_element(self):
        """Get the currently focused text input element"""
        try:
            focused_element = auto.GetFocusedControl()
            
            if not focused_element:
                return None
            
            control_type = focused_element.ControlType
            
            if control_type == auto.ControlType.EditControl:
                return focused_element
            elif control_type == auto.ControlType.DocumentControl:
                return focused_element
            elif hasattr(focused_element, 'GetValuePattern'):
                value_pattern = focused_element.GetValuePattern()
                if value_pattern and not value_pattern.IsReadOnly:
                    return focused_element
            
            return None
        
        except Exception as e:
            return None
    
    def get_text_from_element(self, element):
        """Read text from UI element"""
        try:
            if hasattr(element, 'GetValuePattern'):
                value_pattern = element.GetValuePattern()
                if value_pattern:
                    return value_pattern.Value
            
            if hasattr(element, 'GetTextPattern'):
                text_pattern = element.GetTextPattern()
                if text_pattern:
                    return text_pattern.DocumentRange.GetText(-1)
            
            return element.Name
        
        except Exception as e:
            return None
    
    def set_text_in_element(self, element, new_text):
        """
        Set text in UI element while preserving cursor position.
        Actually, for better UX, we'll put cursor at the END.
        """
        try:
            if hasattr(element, 'GetValuePattern'):
                value_pattern = element.GetValuePattern()
                if value_pattern and not value_pattern.IsReadOnly:
                    # Set the text
                    value_pattern.SetValue(new_text)
                    
                    # Try to move cursor to end (better UX)
                    try:
                        # For some controls, we can use TextPattern to set cursor
                        if hasattr(element, 'GetTextPattern'):
                            text_pattern = element.GetTextPattern()
                            if text_pattern:
                                doc_range = text_pattern.DocumentRange
                                # Move to end
                                doc_range.MoveEndpointByUnit(
                                    auto.TextPatternRangeEndpoint.Start,
                                    auto.TextUnit.Character,
                                    len(new_text)
                                )
                                doc_range.Select()
                    except:
                        # If cursor positioning fails, that's okay
                        # At least the text is replaced
                        pass
                    
                    return True
            
            return False
        
        except Exception as e:
            print(f"  Error setting text: {e}")
            return False
    
    def on_press(self, key):
        """Handle keypress"""
        try:
            if self.processing:
                return
            
            self.stats['keystrokes'] += 1
            self.is_typing = True
            self.last_keystroke_time = time.time()
        
        except Exception as e:
            pass
    
    def replace_all_text(self, element, new_text):
        """Replace all text in element (helper for undo)"""
        return self.set_text_in_element(element, new_text)
    
    def check_and_replace(self):
        """Check focused element for PII and replace"""
        try:
            # Initialize obfuscator in monitor thread
            if not self.obfuscator_initialized:
                print("\n→ Initializing detection engine...")
                from obfuscator import PIIObfuscator
                
                # Load detector preferences
                use_regex = self.prefs_manager.get('detectors.regex', False)
                use_spacy = self.prefs_manager.get('detectors.spacy', False)
                use_transformer = self.prefs_manager.get('detectors.transformer', True)
                spacy_model = self.prefs_manager.get('advanced.spacy_model', 'en_core_web_sm')
                transformer_model = self.prefs_manager.get('advanced.transformer_model', 'lakshyakh93/deberta_finetuned_pii')
                confidence_threshold = self.prefs_manager.get('advanced.confidence_threshold', 0.85)  # Higher threshold to avoid false positives
                use_consensus = self.prefs_manager.get('advanced.use_consensus', False)
                consensus_mode = self.prefs_manager.get('advanced.consensus_mode', 'any_two')
                
                print(f"  Regex: {'✓' if use_regex else '✗'}")
                print(f"  spaCy: {'✓' if use_spacy else '✗'}")
                print(f"  Transformer: {'✓' if use_transformer else '✗'}")
                print(f"  Consensus Mode: {'✓' if use_consensus else '✗'} ({consensus_mode if use_consensus else 'N/A'})")
                if use_transformer:
                    print(f"  Model: {transformer_model}")
                
                self.obfuscator = PIIObfuscator(
                    use_regex=use_regex,
                    use_spacy=use_spacy,
                    use_transformer=use_transformer,
                    transformer_model=transformer_model,
                    spacy_model=spacy_model,
                    confidence_threshold=confidence_threshold,
                    use_consensus=use_consensus,
                    consensus_mode=consensus_mode,
                )
                self.obfuscator_initialized = True
                print("✓ Ready\n")
            
            self.processing = True
            
            # Get focused text element
            element = self.get_focused_text_element()
            if not element:
                print("→ No text element focused")
                return
            
            # Read actual text from element
            text = self.get_text_from_element(element)
            min_length = self.prefs_manager.get('advanced.min_text_length', 10)
            if not text or len(text.strip()) < min_length:
                return
            
            # CRITICAL FIX 1: Skip if already contains placeholders
            if self.has_placeholders(text):
                print("→ Text already contains placeholders, skipping")
                self.last_processed_text = text
                return
            
            # CRITICAL FIX 2: Don't reprocess exact same text
            if text == self.last_processed_text:
                return
            
            print(f"\n→ Checking {len(text)} chars for PII...")
            print(f"   Text: {text[:80]}...")
            
            # Detect PII
            start_time = time.time()
            result = self.obfuscator.obfuscate(text, source="desktop_app")
            detection_time = (time.time() - start_time) * 1000
            
            # Filter out very short/single character detections (false positives)
            valid_replacements = {
                k: v for k, v in result.replacements.items()
                if len(str(v).strip()) >= 3  # Must be at least 3 characters
            }
            
            if len(valid_replacements) > 0:
                print(f"✓ Found {len(valid_replacements)} PII items:")
                for placeholder, original in list(valid_replacements.items())[:5]:
                    entity_type = placeholder.split('_')[0].replace('{', '')
                    print(f"   • {entity_type}: {original[:40]}")
                
                # Store original for undo
                self.last_original_text = text
                self.last_element = element
                
                self.stats['pii_items'] += len(valid_replacements)
                
                # Replace text in element
                print(f"→ Replacing text...")
                success = self.set_text_in_element(element, result.obfuscated_text)
                
                if success:
                    self.last_processed_text = result.obfuscated_text
                    self.stats['replacements'] += 1
                    print(f"✓ Protected!\n")
                    
                    # Track to Amplitude
                    if self.amplitude_tracker:
                        try:
                            app_name = self.get_active_app() or "unknown"
                            # Update result with valid replacements
                            result.replacements = valid_replacements
                            result.num_redactions = len(valid_replacements)
                            track_pii_detection_from_result(
                                self.amplitude_tracker,
                                result,
                                source="typing",
                                app_name=app_name,
                                detection_time_ms=detection_time
                            )
                        except Exception as e:
                            pass  # Don't break main app if tracking fails
                    
                    # Show notification with undo
                    if self.prefs_manager.get('notifications.enabled', True):
                        # Create undo callback
                        original_text = text  # Capture in closure
                        stored_element = element
                        
                        undo_start_time = time.time()
                        def undo_replacement():
                            try:
                                # Replace text back to original
                                self.replace_all_text(stored_element, original_text)
                                self.last_processed_text = original_text
                                # Update stats
                                self.stats['replacements'] -= 1
                                self.stats['pii_items'] -= len(valid_replacements)
                                print("✓ Undo: Original text restored")
                                
                                # Track undo to Amplitude
                                if self.amplitude_tracker:
                                    try:
                                        time_to_undo = time.time() - undo_start_time
                                        track_user_undo(self.amplitude_tracker, "typing", time_to_undo)
                                    except:
                                        pass
                            except Exception as e:
                                print(f"Error in undo: {e}")
                        
                        # Get preview text
                        items_preview = ""
                        if self.prefs_manager.get('notifications.show_preview', True):
                            preview_items = list(valid_replacements.values())[:3]
                            items_preview = ", ".join(str(item)[:30] for item in preview_items)
                        
                        show_pii_notification(
                            num_items=len(valid_replacements),
                            items_preview=items_preview,
                            source="typing",
                            undo_callback=undo_replacement
                        )
                else:
                    print(f"✗ Could not replace text\n")
            else:
                # No PII found, remember this text
                self.last_processed_text = text
        
        except Exception as e:
            print(f"✗ Error: {e}")
        
        finally:
            self.processing = False
    
    def monitor_loop(self):
        """Background monitoring loop with COM initialization"""
        with auto.UIAutomationInitializerInThread():
            print("✓ COM initialized in monitor thread\n")
            
            while True:
                try:
                    time.sleep(0.3)
                    
                    idle_time = time.time() - self.last_keystroke_time
                    
                    # Only check once after 1.5s pause
                    if self.is_typing and idle_time >= self.pause_threshold:
                        # Only run if not already scheduled/running
                        if not self.check_scheduled and not self.processing:
                            self.is_typing = False
                            self.check_scheduled = True
                            
                            app = self.get_active_app()
                            
                            if app and self.is_monitored_app(app):
                                print(f"[Typing paused in {self.MONITORED_APPS[app]}]", end=" ")
                                self.check_and_replace()
                            
                            self.check_scheduled = False
                
                except Exception as e:
                    pass
    
    def start(self):
        """Start monitoring"""
        # Start notification system in background if enabled
        if self.prefs_manager.get('notifications.enabled', True):
            from notification_system import get_notification_manager
            notification_thread = threading.Thread(
                target=lambda: get_notification_manager().start(),
                daemon=True
            )
            notification_thread.start()
            time.sleep(0.5)  # Give notification system time to initialize
            print("✓ Notification system started")
        
        print("\n✓ Monitor started")
        print("  Type in Slack/Teams/Outlook/Discord")
        print("  System will check 1.5s after you stop typing")
        print("  Press Ctrl+C to stop\n")
        
        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()
        
        with keyboard.Listener(on_press=self.on_press) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                pass
    
    def print_stats(self):
        """Print statistics"""
        print("\n" + "=" * 60)
        print("STATISTICS")
        print("=" * 60)
        print(f"  Keystrokes: {self.stats['keystrokes']}")
        print(f"  PII detected: {self.stats['pii_items']}")
        print(f"  Successful replacements: {self.stats['replacements']}")
        print("=" * 60)
    
    def close(self):
        """Cleanup"""
        if self.obfuscator:
            try:
                self.obfuscator.close()
            except:
                pass


def main():
    """Main entry point"""
    monitor = DesktopAppMonitorV2()
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        monitor.print_stats()
        monitor.close()


if __name__ == "__main__":
    main()