"""
System-Wide Keystroke Monitor
Monitors keyboard input across all Windows applications in real-time.
Detects PII being typed and shows warnings for dangerous applications.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from pynput import keyboard
from pynput.keyboard import Key, Controller
import win32gui
import win32process
import psutil
import threading
import time
from collections import deque
from obfuscator import PIIObfuscator
from datetime import datetime
import re

class KeystrokeMonitor:
    """
    System-wide keystroke monitor.
    
    Features:
    - Monitors all keyboard input
    - Buffers last N keystrokes
    - Detects PII in real-time
    - Shows warnings for dangerous applications
    - Can block/clear input on detection
    """
    
    # Dangerous applications where PII should not be typed
    DANGEROUS_APPS = {
        'chrome.exe': ['ChatGPT', 'Claude', 'Gemini', 'Copilot', 'Slack'],
        'msedge.exe': ['ChatGPT', 'Claude', 'Gemini', 'Copilot', 'Slack'],
        'firefox.exe': ['ChatGPT', 'Claude', 'Gemini', 'Copilot', 'Slack'],
        'slack.exe': ['Slack'],
        'teams.exe': ['Teams'],
        'discord.exe': ['Discord'],
    }
    
    def __init__(
        self,
        buffer_size: int = 500,
        check_interval: float = 2.0,
        enable_warnings: bool = True,
        enable_blocking: bool = False
    ):
        """
        Initialize keystroke monitor.
        
        Args:
            buffer_size: How many characters to buffer
            check_interval: How often to check buffer (seconds)
            enable_warnings: Show warning notifications
            enable_blocking: Block input when PII detected (experimental)
        """
        print("=" * 60)
        print("PII GUARD - KEYSTROKE MONITOR")
        print("=" * 60)
        
        self.buffer_size = buffer_size
        self.check_interval = check_interval
        self.enable_warnings = enable_warnings
        self.enable_blocking = enable_blocking
        
        # Keystroke buffer
        self.buffer = deque(maxlen=buffer_size)
        self.last_check_time = time.time()
        
        # Create obfuscator (lightweight - no transformer)
        print("\nInitializing obfuscator...")
        self.obfuscator = PIIObfuscator(
            use_regex=True,
            use_spacy=True,
            use_transformer=False,
            spacy_model="en_core_web_sm"  # Fast model
        )
        
        # Statistics
        self.stats = {
            'keystrokes_monitored': 0,
            'pii_detected': 0,
            'warnings_shown': 0,
            'dangerous_apps_detected': 0
        }
        
        # Keyboard controller for blocking
        self.keyboard_controller = Controller()
        
        # Current window tracking
        self.current_app = None
        self.current_window = None
        
        print("✓ Keystroke monitor initialized")
        print("=" * 60)
    
    def get_active_window_info(self):
        """Get information about currently active window"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            process = psutil.Process(pid)
            app_name = process.name()
            window_title = win32gui.GetWindowText(hwnd)
            
            return {
                'app': app_name,
                'window': window_title,
                'pid': pid
            }
        except:
            return None
    
    def is_dangerous_context(self, window_info):
        """Check if current context is dangerous"""
        if not window_info:
            return False
        
        app = window_info['app']
        title = window_info['window']
        
        # Check if app is in dangerous list
        if app in self.DANGEROUS_APPS:
            keywords = self.DANGEROUS_APPS[app]
            for keyword in keywords:
                if keyword.lower() in title.lower():
                    return True
        
        return False
    
    def get_buffer_text(self):
        """Convert buffer to text string"""
        return ''.join(self.buffer)
    
    def check_buffer_for_pii(self):
        """Check current buffer for PII"""
        text = self.get_buffer_text()
        
        if len(text.strip()) < 10:  # Too short to check
            return None
        
        # Run detection
        result = self.obfuscator.obfuscate(text, source="keystroke")
        
        if result.num_redactions > 0:
            return result
        
        return None
    
    def show_warning(self, pii_result, window_info):
        """Show warning notification"""
        print("\n" + "!" * 60)
        print("⚠️  PII DETECTED IN DANGEROUS APPLICATION")
        print("!" * 60)
        print(f"Application: {window_info['app']}")
        print(f"Window: {window_info['window']}")
        print(f"PII detected: {pii_result.num_redactions} items")
        print("\nDetected entities:")
        for placeholder, original in list(pii_result.replacements.items())[:5]:
            entity_type = placeholder.split('_')[0].replace('{', '')
            print(f"  - {entity_type}: {original}")
        print("\n⚠️  WARNING: You are typing sensitive information!")
        print("!" * 60)
        
        self.stats['warnings_shown'] += 1
        
        # Could also show Windows toast notification here
        # from win10toast import ToastNotifier
        # toaster = ToastNotifier()
        # toaster.show_toast("PII Guard", "PII detected in sensitive app!", duration=5)
    
    def on_press(self, key):
        """Handle key press event"""
        try:
            # Get character
            if hasattr(key, 'char') and key.char:
                char = key.char
            elif key == Key.space:
                char = ' '
            elif key == Key.enter:
                char = '\n'
            elif key == Key.tab:
                char = '\t'
            else:
                return  # Ignore other special keys
            
            # Add to buffer
            self.buffer.append(char)
            self.stats['keystrokes_monitored'] += 1
            
            # Check buffer periodically
            current_time = time.time()
            if current_time - self.last_check_time >= self.check_interval:
                self.last_check_time = current_time
                self.check_buffer()
        
        except Exception as e:
            print(f"Error in key handler: {e}")
    
    def on_release(self, key):
        """Handle key release event"""
        # Stop on Ctrl+Shift+Q
        if key == Key.esc:
            # Check for stop command
            pass
    
    def check_buffer(self):
        """Periodic buffer check"""
        # Get current window
        window_info = self.get_active_window_info()
        
        if not window_info:
            return
        
        # Check if dangerous context
        is_dangerous = self.is_dangerous_context(window_info)
        
        if is_dangerous:
            self.stats['dangerous_apps_detected'] += 1
        
        # Check for PII
        pii_result = self.check_buffer_for_pii()
        
        if pii_result:
            self.stats['pii_detected'] += pii_result.num_redactions
            
            if is_dangerous and self.enable_warnings:
                self.show_warning(pii_result, window_info)
            
            # Optional: Clear buffer after detection
            # self.buffer.clear()
    
    def start(self):
        """Start monitoring keystrokes"""
        print("\n✓ Keystroke monitor started")
        print("  Monitoring all keyboard input...")
        print(f"  Buffer size: {self.buffer_size} characters")
        print(f"  Check interval: {self.check_interval} seconds")
        print(f"  Warnings: {'Enabled' if self.enable_warnings else 'Disabled'}")
        print("\n  Press Ctrl+C to stop\n")
        
        # Start keyboard listener
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                pass
    
    def print_stats(self):
        """Print statistics"""
        print("\n" + "=" * 60)
        print("KEYSTROKE MONITOR STATISTICS")
        print("=" * 60)
        print(f"  Keystrokes monitored: {self.stats['keystrokes_monitored']}")
        print(f"  PII items detected: {self.stats['pii_detected']}")
        print(f"  Warnings shown: {self.stats['warnings_shown']}")
        print(f"  Dangerous apps detected: {self.stats['dangerous_apps_detected']}")
        print("=" * 60)
    
    def close(self):
        """Clean up"""
        self.obfuscator.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PII Guard Keystroke Monitor - System-wide PII detection"
    )
    parser.add_argument('--buffer-size', type=int, default=500,
                       help='Keystroke buffer size')
    parser.add_argument('--check-interval', type=float, default=2.0,
                       help='How often to check buffer (seconds)')
    parser.add_argument('--no-warnings', action='store_true',
                       help='Disable warning notifications')
    parser.add_argument('--enable-blocking', action='store_true',
                       help='Enable input blocking (experimental)')
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = KeystrokeMonitor(
        buffer_size=args.buffer_size,
        check_interval=args.check_interval,
        enable_warnings=not args.no_warnings,
        enable_blocking=args.enable_blocking
    )
    
    try:
        # Start monitoring
        monitor.start()
    
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal")
    
    finally:
        monitor.print_stats()
        monitor.close()


if __name__ == "__main__":
    main()
