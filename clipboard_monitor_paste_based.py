"""
Paste-Based Clipboard Monitor - ENHANCED WITH IMAGE SUPPORT
===========================================================

SMART STRATEGY (No admin privileges needed):
1. On COPY: Detect PII in text AND images, store both versions
2. Monitor active window every 100ms
3. If dangerous app has focus: Keep clipboard obfuscated
4. If safe app has focus: Keep clipboard original

Now supports:
- Text protection (existing)
- Image protection with OCR (NEW)
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
import io
from PIL import Image
import tempfile
import os
import json

from obfuscator import PIIObfuscator
from image_obfuscator import ImagePIIObfuscator
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


class FocusBasedClipboardMonitor:
    """
    Focus-based clipboard monitor with TEXT + IMAGE support.
    
    Strategy:
    - Monitor which app has focus
    - If dangerous app focused: Clipboard = obfuscated (text or image)
    - If safe app focused: Clipboard = original (text or image)
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
        print("Now with IMAGE protection via OCR!")
        print("Integrated with browser extension!")
        print("No admin privileges needed!")
        print("=" * 60)
        
        self.prefs_manager = PreferencesManager()
        print("✓ Loaded preferences")
        
        self.clipboard_cache = {
            'content_type': None,  # 'text' or 'image'
            'original': None,
            'obfuscated': None,
            'has_pii': False,
            'num_items': 0,
        }
        
        self.text_obfuscator = None
        self.image_obfuscator = None
        self.running = False
        
        # Track current clipboard state
        self.clipboard_is_obfuscated = False
        self.last_focused_app = None
        
        self.last_clipboard_seq = 0
        self.processing = False
        
        # Track processed images to avoid reprocessing loop
        self.processed_image_hashes = set()
        self.last_processed_time = 0
        
        # Temporary directory for image processing
        self.temp_dir = tempfile.mkdtemp(prefix="pii_guard_")
        
        # IPC file for extension status (same path as native host uses)
        if sys.platform == 'win32':
            self.extension_status_file = Path.home() / 'AppData' / 'Local' / 'EdgeDLP' / 'extension_status.json'
        else:
            self.extension_status_file = Path('/tmp/edgedlp_extension_status.json')
        
        print(f"[DEBUG] Extension status IPC file: {self.extension_status_file}")
        print(f"[DEBUG] IPC file exists: {self.extension_status_file.exists()}")
        
        # Extension status cache
        self.extension_status = {
            'is_risky_domain': False,
            'hostname': '',
            'timestamp': 0
        }
        
        # Try to read initial extension status
        self._read_extension_status()
        print(f"[DEBUG] Initial extension status: risky={self.extension_status.get('is_risky_domain')}, hostname={self.extension_status.get('hostname')}")
        
        # Browser process names
        self.BROWSER_PROCESSES = {
            'msedge.exe', 'chrome.exe', 'firefox.exe', 'brave.exe',
            'opera.exe', 'vivaldi.exe', 'edge.exe'
        }
        
        self.stats = {
            'copies_monitored': 0,
            'clipboard_swaps': 0,
            'dangerous_app_focused': 0,
            'safe_app_focused': 0,
            'pii_items_detected': 0,
            'images_processed': 0,
            'texts_processed': 0,
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
        
        print("✓ Monitor initialized")
        print("=" * 60)
    
    def _get_clipboard_sequence(self):
        try:
            return win32clipboard.GetClipboardSequenceNumber()
        except:
            return 0
    
    def _get_clipboard_text(self):
        """Get text from clipboard"""
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
    
    def _get_clipboard_image(self):
        """Get image from clipboard as PIL Image"""
        try:
            win32clipboard.OpenClipboard()
            try:
                # Try CF_DIB format (Device Independent Bitmap)
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                    data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                    # Convert DIB to PIL Image
                    image = Image.open(io.BytesIO(data))
                    return image
                # Try CF_BITMAP format
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_BITMAP):
                    # This is trickier, CF_BITMAP returns a handle
                    # For now, we'll skip this format
                    pass
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"Error reading image from clipboard: {e}")
        return None
    
    def _set_clipboard_text(self, text):
        """Set text to clipboard"""
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
    
    def _set_clipboard_image(self, image_path):
        """Set image to clipboard from file path"""
        try:
            # Load image using PIL
            image = Image.open(image_path)
            
            # Convert to DIB format for clipboard
            output = io.BytesIO()
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # Remove BMP file header (14 bytes)
            output.close()
            
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_DIB, data)
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"Error setting image to clipboard: {e}")
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
    
    def _read_extension_status(self):
        """Read extension status from IPC file"""
        try:
            if self.extension_status_file.exists():
                with open(self.extension_status_file, 'r') as f:
                    status = json.load(f)
                    # Only update if timestamp is newer
                    if status.get('timestamp', 0) > self.extension_status.get('timestamp', 0):
                        old_status = self.extension_status.copy()
                        self.extension_status = status
                        print(f"\n[DEBUG] Extension status updated:")
                        print(f"  Old: risky={old_status.get('is_risky_domain')}, hostname={old_status.get('hostname')}")
                        print(f"  New: risky={status.get('is_risky_domain')}, hostname={status.get('hostname')}, timestamp={status.get('timestamp')}")
                    else:
                        # Status unchanged, but log it occasionally for debugging
                        if time.time() % 5 < 0.1:  # Log roughly every 5 seconds
                            print(f"[DEBUG] Extension status (unchanged): risky={status.get('is_risky_domain')}, hostname={status.get('hostname')}")
            else:
                # File doesn't exist - log occasionally
                if time.time() % 5 < 0.1:
                    print(f"[DEBUG] Extension status file not found: {self.extension_status_file}")
        except Exception as e:
            # File might be locked or invalid - log the error
            print(f"[DEBUG] Error reading extension status: {e}")
            traceback.print_exc()
    
    def _is_dangerous_app(self, process_name, skip_extension_read=False):
        """Check if process is dangerous
        
        Args:
            process_name: Name of the process to check
            skip_extension_read: If True, skip reading extension status (already read)
        """
        # Check if it's a browser process
        if process_name in self.BROWSER_PROCESSES:
            # Read extension status (unless already read)
            if not skip_extension_read:
                self._read_extension_status()
            # If extension says risky domain, treat browser as dangerous
            if self.extension_status.get('is_risky_domain', False):
                hostname = self.extension_status.get('hostname', '')
                return True, f"Browser (risky domain: {hostname})"
            # Otherwise, browser is safe
            return False, "Browser (safe domain)"
        
        # Check standard dangerous apps
        if process_name in self.DANGEROUS_APPS:
            print(f"[DEBUG] Dangerous app detected: {self.DANGEROUS_APPS[process_name]}")
            return True, self.DANGEROUS_APPS[process_name]
        
        whitelist = self.prefs_manager.get('whitelist.apps', [])
        if process_name in whitelist:
            print(f"[DEBUG] Whitelisted app: {process_name}")
            return False, f"Whitelisted"
        
        return False, process_name
    
    def _monitor_clipboard_changes(self):
        """Monitor clipboard for copies (text AND images)"""
        print("\n✓ Clipboard monitor started")
        print("Initializing obfuscators in monitoring thread...")
        
        use_regex = self.prefs_manager.get('detectors.regex', True)
        use_spacy = self.prefs_manager.get('detectors.spacy', True)
        use_transformer = self.prefs_manager.get('detectors.transformer', True)
        spacy_model = self.prefs_manager.get('advanced.spacy_model', 'en_core_web_sm')
        transformer_model = self.prefs_manager.get('advanced.transformer_model', 'lakshyakh93/deberta_finetuned_pii')
        use_consensus = self.prefs_manager.get('advanced.use_consensus', False)
        consensus_mode = self.prefs_manager.get('advanced.consensus_mode', 'any_two')
        
        print(f"  Transformer: {'✓' if use_transformer else '✗'}")
        print(f"  spaCy: {'✓' if use_spacy else '✗'}")
        print(f"  Regex: {'✓' if use_regex else '✗'}")
        print(f"  Consensus Mode: {'✓' if use_consensus else '✗'} ({consensus_mode if use_consensus else 'N/A'})")
        
        # Initialize text obfuscator
        self.text_obfuscator = PIIObfuscator(
            use_regex=use_regex,
            use_spacy=use_spacy,
            use_transformer=use_transformer,
            transformer_model=transformer_model,
            spacy_model=spacy_model,
            use_consensus=use_consensus,
            consensus_mode=consensus_mode,
        )
        
        # Initialize image obfuscator
        self.image_obfuscator = ImagePIIObfuscator(
            text_obfuscator=self.text_obfuscator,
            blur_strength=25
        )
        
        print("✓ Obfuscators initialized\n")
        
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
        """User copied something - detect PII in text OR image"""
        self.processing = True
        
        try:
            # First, try to get text
            text = self._get_clipboard_text()
            if text and len(text.strip()) >= 10:
                self._process_text_clipboard(text)
                return
            
            # If no text, try to get image
            image = self._get_clipboard_image()
            if image:
                self._process_image_clipboard(image)
                return
            
            # No text or image - clear cache
            self.clipboard_cache = {
                'content_type': None,
                'original': None,
                'obfuscated': None,
                'has_pii': False,
                'num_items': 0,
            }
            self.clipboard_is_obfuscated = False
            
        except Exception as e:
            print(f"Error processing clipboard: {e}")
            traceback.print_exc()
        finally:
            self.processing = False
    
    def _process_text_clipboard(self, text):
        """Process text clipboard content"""
        try:
            # Check if this matches our cached obfuscated text (user copied obfuscated version)
            was_obfuscated_copy = False
            cached_obfuscated = self.clipboard_cache.get('obfuscated', '')
            cached_original = self.clipboard_cache.get('original', '')
            
            if (self.clipboard_cache.get('content_type') == 'text' and
                cached_obfuscated and text == cached_obfuscated):
                # User copied the obfuscated version - keep it as obfuscated
                was_obfuscated_copy = True
                print(f"[DEBUG] Detected copy of obfuscated text - keeping obfuscated state")
                # Don't re-process - use existing cache
                self.clipboard_is_obfuscated = True
                self.stats['copies_monitored'] += 1
                return
            elif (self.clipboard_cache.get('content_type') == 'text' and
                  cached_original and text == cached_original):
                # User copied the original version - it's a new copy of original
                was_obfuscated_copy = False
                print(f"[DEBUG] Detected copy of original text - resetting to original state")
            
            # Detect PII (new copy or different text)
            start_time = time.time()
            result = self.text_obfuscator.obfuscate(text, source="clipboard")
            detection_time = (time.time() - start_time) * 1000
            
            # Store both versions
            self.clipboard_cache = {
                'content_type': 'text',
                'original': text,
                'obfuscated': result.obfuscated_text,
                'has_pii': result.num_redactions > 0,
                'num_items': result.num_redactions,
                'replacements': result.replacements,
            }
            
            # If user copied obfuscated text, keep it as obfuscated; otherwise it's original
            self.clipboard_is_obfuscated = was_obfuscated_copy
            self.stats['copies_monitored'] += 1
            self.stats['texts_processed'] += 1
            
            if result.num_redactions > 0:
                self.stats['pii_items_detected'] += result.num_redactions
                print(f"\n📋 TEXT COPY: Detected {result.num_redactions} PII items ({detection_time:.0f}ms)")
                print(f"   Clipboard will auto-adjust based on active app")
                print(f"[DEBUG] Clipboard cache updated: has_pii=True, content_type=text, is_obfuscated={self.clipboard_is_obfuscated}")
                print(f"[DEBUG] Original length: {len(text)}, Obfuscated length: {len(result.obfuscated_text)}")
                
                # Track to Amplitude
                if self.amplitude_tracker:
                    try:
                        window_info = self._get_active_window_info()
                        app_name = window_info['process'] if window_info else "unknown"
                        track_pii_detection_from_result(
                            self.amplitude_tracker,
                            result,
                            source="clipboard",
                            app_name=app_name,
                            detection_time_ms=detection_time
                        )
                    except Exception as e:
                        pass  # Don't break main app if tracking fails
            else:
                print(f"[DEBUG] No PII detected in copied text")
        
        except Exception as e:
            print(f"Error processing text: {e}")
            traceback.print_exc()
    
    def _process_image_clipboard(self, image):
        """Process image clipboard content with OCR"""
        try:
            # Check if we just processed this image (prevent loop)
            import hashlib
            image_bytes = image.tobytes()
            image_hash = hashlib.md5(image_bytes).hexdigest()
            
            current_time = time.time()
            if image_hash in self.processed_image_hashes and (current_time - self.last_processed_time) < 2:
                print(f"⏭️  Skipping recently processed image (preventing loop)")
                return
            
            print(f"\n🖼️  IMAGE COPY: Processing image ({image.size[0]}x{image.size[1]})...")
            
            # Save original image to temp file
            original_path = os.path.join(self.temp_dir, f"original_{time.time()}.png")
            image.save(original_path)
            
            # Remember this image hash
            self.processed_image_hashes.add(image_hash)
            self.last_processed_time = current_time
            
            # Clean old hashes (keep last 10)
            if len(self.processed_image_hashes) > 10:
                self.processed_image_hashes.clear()
            
            # Extract text using OCR
            print("   Running OCR to extract text...")
            start_time = time.time()
            extracted_text = self.image_obfuscator.extract_text(original_path)
            ocr_time = (time.time() - start_time) * 1000
            
            if not extracted_text or len(extracted_text.strip()) < 10:
                print(f"   No text found in image (OCR: {ocr_time:.0f}ms)")
                # No text found - let image pass through unchanged
                self.clipboard_cache = {
                    'content_type': 'image',
                    'original': original_path,
                    'obfuscated': original_path,  # Same as original
                    'has_pii': False,
                    'num_items': 0,
                }
                self.clipboard_is_obfuscated = False
                return
            
            print(f"   Extracted text: {extracted_text[:100]}...")
            
            # Detect PII in extracted text
            print("   Detecting PII in extracted text...")
            result = self.text_obfuscator.obfuscate(extracted_text, source="clipboard_image")
            
            if result.num_redactions == 0:
                print("   No PII found in image")
                self.clipboard_cache = {
                    'content_type': 'image',
                    'original': original_path,
                    'obfuscated': original_path,  # Same as original
                    'has_pii': False,
                    'num_items': 0,
                }
                self.clipboard_is_obfuscated = False
                return
            
            # PII found! Create obfuscated version
            print(f"   Found {result.num_redactions} PII items, creating obfuscated image...")
            obfuscated_path = os.path.join(self.temp_dir, f"obfuscated_{time.time()}.png")
            
            obfuscation_result = self.image_obfuscator.obfuscate_image(
                original_path,
                obfuscated_path,
                method='blur'  # Can be 'blur', 'black', or 'pixelate'
            )
            
            total_time = (time.time() - start_time) * 1000
            
            # Store both versions
            self.clipboard_cache = {
                'content_type': 'image',
                'original': original_path,
                'obfuscated': obfuscated_path,
                'has_pii': True,
                'num_items': obfuscation_result['num_redactions'],
                'replacements': result.replacements,
            }
            
            self.clipboard_is_obfuscated = False  # User copied original
            self.stats['copies_monitored'] += 1
            self.stats['images_processed'] += 1
            self.stats['pii_items_detected'] += obfuscation_result['num_redactions']
            
            print(f"   ✓ Image processed: {obfuscation_result['num_redactions']} regions obfuscated ({total_time:.0f}ms)")
            print(f"   Clipboard will auto-adjust based on active app")
            
            # Track to Amplitude
            if self.amplitude_tracker:
                try:
                    window_info = self._get_active_window_info()
                    app_name = window_info['process'] if window_info else "unknown"
                    # Create a mock result object for tracking
                    class MockResult:
                        def __init__(self):
                            self.num_redactions = obfuscation_result['num_redactions']
                            self.replacements = result.replacements
                            self.detection_time_ms = total_time
                    mock_result = MockResult()
                    track_pii_detection_from_result(
                        self.amplitude_tracker,
                        mock_result,
                        source="clipboard_image",
                        app_name=app_name,
                        detection_time_ms=total_time
                    )
                except Exception as e:
                    pass  # Don't break main app if tracking fails
        
        except Exception as e:
            print(f"Error processing image: {e}")
            traceback.print_exc()
    
    def _monitor_focus_changes(self):
        """Monitor which app has focus and adjust clipboard (text OR image)"""
        print("✓ Focus monitor started\n")
        
        last_app = None
        last_extension_check = 0
        extension_check_interval = 3.0  # Fallback: Re-check extension status every 3 seconds when browser is active (extension should notify immediately on tab changes)
        cached_danger_status = {}  # Cache danger status per app: {app_name: (is_dangerous, app_name_str)}
        
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
                current_time = time.time()
                
                # Check if app changed
                app_changed = (current_app != last_app)
                
                # For browsers, periodically re-check extension status (fallback - extension should notify immediately)
                is_browser = current_app in self.BROWSER_PROCESSES
                should_check_extension = (is_browser and 
                                         (app_changed or 
                                          (current_time - last_extension_check) >= extension_check_interval))
                
                if app_changed:
                    print(f"\n[DEBUG] App focus changed: {last_app} → {current_app}")
                    last_app = current_app
                
                # Periodically re-read extension status for browsers (fallback)
                extension_status_changed = False
                if should_check_extension:
                    last_extension_check = current_time
                    # Force re-read extension status
                    old_status = self.extension_status.copy()
                    self._read_extension_status()
                    if old_status.get('is_risky_domain') != self.extension_status.get('is_risky_domain'):
                        extension_status_changed = True
                        print(f"[DEBUG] Extension status changed while browser active: risky={self.extension_status.get('is_risky_domain')}, hostname={self.extension_status.get('hostname')}")
                        # Clear cache for this app since status changed
                        if current_app in cached_danger_status:
                            del cached_danger_status[current_app]
                
                # Only check danger status if app changed or extension status changed
                # Otherwise, use cached danger status to avoid unnecessary checks
                if app_changed or extension_status_changed:
                    is_dangerous, app_name = self._is_dangerous_app(current_app, skip_extension_read=True)
                    # Cache the result
                    cached_danger_status[current_app] = (is_dangerous, app_name)
                    print(f"[DEBUG] App danger status: is_dangerous={is_dangerous}, app_name={app_name}")
                    print(f"[DEBUG] Clipboard cache: has_pii={self.clipboard_cache.get('has_pii')}, is_obfuscated={self.clipboard_is_obfuscated}")
                else:
                    # Use cached danger status (don't re-check every loop)
                    if current_app in cached_danger_status:
                        is_dangerous, app_name = cached_danger_status[current_app]
                    else:
                        # First time seeing this app - check it
                        is_dangerous, app_name = self._is_dangerous_app(current_app, skip_extension_read=False)
                        cached_danger_status[current_app] = (is_dangerous, app_name)
                
                # Only adjust if we have PII to protect
                if self.clipboard_cache.get('has_pii', False):
                    content_type = self.clipboard_cache.get('content_type')
                    
                    if is_dangerous and not self.clipboard_is_obfuscated:
                        # Switched to dangerous app - obfuscate clipboard
                        print(f"\n🔒 Switched to {app_name} → Obfuscating clipboard ({content_type})")
                        print(f"[DEBUG] Setting clipboard to obfuscated version")
                        self.processing = True
                        
                        if content_type == 'text':
                            success = self._set_clipboard_text(self.clipboard_cache['obfuscated'])
                            print(f"[DEBUG] Clipboard text set: success={success}")
                        elif content_type == 'image':
                            success = self._set_clipboard_image(self.clipboard_cache['obfuscated'])
                            print(f"[DEBUG] Clipboard image set: success={success}")
                        
                        self.clipboard_is_obfuscated = True
                        self.stats['clipboard_swaps'] += 1
                        self.stats['dangerous_app_focused'] += 1
                        self.processing = False
                        
                    elif not is_dangerous and self.clipboard_is_obfuscated:
                        # Switched to safe app - restore original
                        print(f"\n✓ Switched to safe app → Restoring original ({content_type})")
                        print(f"[DEBUG] Setting clipboard to original version")
                        self.processing = True
                        
                        if content_type == 'text':
                            success = self._set_clipboard_text(self.clipboard_cache['original'])
                            print(f"[DEBUG] Clipboard text set: success={success}")
                        elif content_type == 'image':
                            success = self._set_clipboard_image(self.clipboard_cache['original'])
                            print(f"[DEBUG] Clipboard image set: success={success}")
                        
                        self.clipboard_is_obfuscated = False
                        self.stats['clipboard_swaps'] += 1
                        self.stats['safe_app_focused'] += 1
                        self.processing = False
                elif app_changed:
                    print(f"[DEBUG] No PII in clipboard cache - skipping clipboard adjustment")
                
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
        print("✓ FOCUS-BASED MONITOR ACTIVE (TEXT + IMAGE)")
        print("=" * 60)
        print("\n🎯 SMART CLIPBOARD:")
        print("  1. Copy text/image with PII → Detected in background")
        print("  2. Switch to Slack → Clipboard auto-obfuscated")
        print("  3. Switch to Excel → Clipboard auto-restored")
        print("  4. Paste normally with Ctrl+V")
        print("\n⚡ How it works:")
        print("  • Monitors which app has focus (every 100ms)")
        print("  • Auto-adjusts clipboard based on app safety")
        print("  • OCR extracts text from images")
        print("  • Blurs PII regions in images")
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
            content_type = self.clipboard_cache.get('content_type')
            if content_type == 'text':
                self._set_clipboard_text(self.clipboard_cache['original'])
            elif content_type == 'image':
                self._set_clipboard_image(self.clipboard_cache['original'])
        
        # Cleanup temp files
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except:
            pass
        
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
        print(f"    - Text: {self.stats['texts_processed']}")
        print(f"    - Images: {self.stats['images_processed']}")
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