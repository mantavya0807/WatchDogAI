"""
Notification System for PII Guard - MODERN UI REDESIGN
Small, beautiful notifications with modern design.
Uses Windows toast notifications with polished, contemporary styling.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import threading
import time
import queue
from typing import Callable, Optional, Dict
import tkinter as tk
from tkinter import ttk


class NotificationManager:
    """
    Manages modern notification popups for PII detections.
    
    Features:
    - Modern, clean design (2024 UI standards)
    - Beautiful animations
    - Auto-dismiss with progress bar
    - Undo button for reverting obfuscation
    - Non-blocking, thread-safe
    """
    
    def __init__(self, auto_dismiss_seconds: int = 5):
        """
        Initialize notification manager.
        
        Args:
            auto_dismiss_seconds: Seconds before auto-dismiss (0 = never)
        """
        self.auto_dismiss_seconds = auto_dismiss_seconds
        self.active_notifications = []
        self.notification_lock = threading.Lock()
        self.notification_queue = queue.Queue()
        self.root = None
        self.running = False
        
    def start(self):
        """Start the notification manager main loop (must be called from main thread)"""
        if self.running:
            return
            
        self.running = True
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main window
        
        # Process queued notifications periodically
        self._process_queue()
        
        # Start main loop
        self.root.mainloop()
    
    def stop(self):
        """Stop the notification manager"""
        self.running = False
        self.dismiss_all()
        if self.root:
            try:
                self.root.quit()
            except:
                pass
    
    def _process_queue(self):
        """Process pending notifications from queue"""
        if not self.running:
            return
            
        try:
            while not self.notification_queue.empty():
                notification_data = self.notification_queue.get_nowait()
                self._create_notification(**notification_data)
        except queue.Empty:
            pass
        
        # Schedule next check
        if self.root and self.running:
            self.root.after(100, self._process_queue)
    
    def _create_notification(self, num_items, items_preview, source, undo_callback):
        """Create a notification window (must be called from main thread)"""
        notification = ModernPIINotification(
            num_items=num_items,
            items_preview=items_preview,
            source=source,
            undo_callback=undo_callback,
            auto_dismiss_seconds=self.auto_dismiss_seconds,
            on_close=lambda n: self._remove_notification(n)
        )
        
        with self.notification_lock:
            self.active_notifications.append(notification)
        
    def show_pii_detected(
        self,
        num_items: int,
        items_preview: str,
        source: str,
        undo_callback: Optional[Callable] = None
    ):
        """
        Show notification for PII detection (thread-safe).
        
        Args:
            num_items: Number of PII items detected
            items_preview: Brief preview of what was detected
            source: Where it was detected (clipboard/typing)
            undo_callback: Function to call if user clicks undo
        """
        # Queue the notification to be created in main thread
        self.notification_queue.put({
            'num_items': num_items,
            'items_preview': items_preview,
            'source': source,
            'undo_callback': undo_callback
        })
    
    def _remove_notification(self, notification):
        """Remove notification from active list"""
        with self.notification_lock:
            if notification in self.active_notifications:
                self.active_notifications.remove(notification)
    
    def dismiss_all(self):
        """Dismiss all active notifications"""
        with self.notification_lock:
            for notification in self.active_notifications[:]:
                try:
                    notification.close()
                except:
                    pass
            self.active_notifications.clear()


class ModernPIINotification:
    """
    Modern, beautiful notification popup.
    Inspired by Windows 11, macOS Big Sur design language.
    """
    
    # Modern design constants
    NOTIFICATION_WIDTH = 380
    NOTIFICATION_HEIGHT = 140
    MARGIN_RIGHT = 20
    MARGIN_BOTTOM = 20
    STACK_OFFSET = 150
    
    # Modern color scheme
    BG_COLOR = "#1a1a1a"  # Deep black
    ACCENT_COLOR = "#00d9ff"  # Bright cyan accent
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0a0"
    BUTTON_BG = "#2a2a2a"
    BUTTON_HOVER = "#3a3a3a"
    PROGRESS_BG = "#2a2a2a"
    CLOSE_HOVER = "#ff4444"
    
    # Counter for stacking notifications
    _instance_count = 0
    _instance_lock = threading.Lock()
    
    def __init__(
        self,
        num_items: int,
        items_preview: str,
        source: str,
        undo_callback: Optional[Callable],
        auto_dismiss_seconds: int,
        on_close: Optional[Callable]
    ):
        self.undo_callback = undo_callback
        self.on_close = on_close
        self.dismissed = False
        self.auto_dismiss_seconds = auto_dismiss_seconds
        
        # Track instance number for stacking
        with ModernPIINotification._instance_lock:
            self.instance_num = ModernPIINotification._instance_count
            ModernPIINotification._instance_count += 1
        
        # Create window
        self.root = tk.Toplevel()
        self.root.title("PII Guard")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        # Modern rounded corners (Windows 11 style)
        try:
            self.root.attributes('-transparentcolor', '#000001')
        except:
            pass
        
        # Set size and position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = screen_width - self.NOTIFICATION_WIDTH - self.MARGIN_RIGHT
        y = screen_height - self.NOTIFICATION_HEIGHT - self.MARGIN_BOTTOM
        y -= self.instance_num * self.STACK_OFFSET
        
        self.root.geometry(f"{self.NOTIFICATION_WIDTH}x{self.NOTIFICATION_HEIGHT}+{x}+{y}")
        
        # Configure background
        self.root.configure(bg=self.BG_COLOR)
        
        # Create UI
        self._create_modern_ui(num_items, items_preview, source)
        
        # Auto-dismiss with progress bar
        if auto_dismiss_seconds > 0:
            self._start_auto_dismiss()
        
        # Fade in animation
        self.root.attributes('-alpha', 0.0)
        self._fade_in()
    
    def _create_modern_ui(self, num_items: int, items_preview: str, source: str):
        """Create modern notification UI"""
        # Main container with padding
        container = tk.Frame(self.root, bg=self.BG_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        
        # === HEADER ROW ===
        header = tk.Frame(container, bg=self.BG_COLOR)
        header.pack(fill=tk.X, pady=(0, 12))
        
        # Shield icon + Title
        icon_title_frame = tk.Frame(header, bg=self.BG_COLOR)
        icon_title_frame.pack(side=tk.LEFT)
        
        # Modern shield emoji
        icon = tk.Label(
            icon_title_frame,
            text="🛡️",
            bg=self.BG_COLOR,
            font=('Segoe UI Emoji', 18)
        )
        icon.pack(side=tk.LEFT, padx=(0, 8))
        
        # Title with accent color
        title = tk.Label(
            icon_title_frame,
            text="PII Protected",
            bg=self.BG_COLOR,
            fg=self.ACCENT_COLOR,
            font=('Segoe UI', 12, 'bold')
        )
        title.pack(side=tk.LEFT)
        
        # Close button (modern X)
        self.close_btn = tk.Label(
            header,
            text="✕",
            bg=self.BG_COLOR,
            fg=self.TEXT_SECONDARY,
            font=('Segoe UI', 14),
            cursor='hand2',
            padx=8,
            pady=4
        )
        self.close_btn.pack(side=tk.RIGHT)
        self.close_btn.bind('<Button-1>', lambda e: self.close())
        self.close_btn.bind('<Enter>', lambda e: self.close_btn.config(fg=self.CLOSE_HOVER, bg=self.BUTTON_HOVER))
        self.close_btn.bind('<Leave>', lambda e: self.close_btn.config(fg=self.TEXT_SECONDARY, bg=self.BG_COLOR))
        
        # === MESSAGE ===
        if num_items == 1:
            message = f"Protected 1 item in {source}"
        else:
            message = f"Protected {num_items} items in {source}"
        
        msg = tk.Label(
            container,
            text=message,
            bg=self.BG_COLOR,
            fg=self.TEXT_PRIMARY,
            font=('Segoe UI', 10),
            anchor='w',
            justify='left'
        )
        msg.pack(fill=tk.X, pady=(0, 4))
        
        # === PREVIEW (if available) ===
        if items_preview and len(items_preview) > 0:
            preview = items_preview[:60] + "..." if len(items_preview) > 60 else items_preview
            preview_label = tk.Label(
                container,
                text=preview,
                bg=self.BG_COLOR,
                fg=self.TEXT_SECONDARY,
                font=('Segoe UI', 9),
                anchor='w',
                justify='left'
            )
            preview_label.pack(fill=tk.X, pady=(0, 12))
        
        # === BOTTOM ROW (Progress + Undo) ===
        bottom = tk.Frame(container, bg=self.BG_COLOR)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Progress bar (if auto-dismiss enabled)
        if self.auto_dismiss_seconds > 0:
            self.progress_canvas = tk.Canvas(
                bottom,
                bg=self.PROGRESS_BG,
                height=3,
                highlightthickness=0,
                bd=0
            )
            self.progress_canvas.pack(fill=tk.X, pady=(0, 10))
            
            # Progress fill
            self.progress_bar = self.progress_canvas.create_rectangle(
                0, 0, 0, 3,
                fill=self.ACCENT_COLOR,
                outline=''
            )
        
        # Undo button (modern, rounded)
        if self.undo_callback:
            self.undo_btn = tk.Label(
                bottom,
                text="↶  Undo",
                bg=self.BUTTON_BG,
                fg=self.TEXT_PRIMARY,
                font=('Segoe UI', 10, 'bold'),
                cursor='hand2',
                padx=20,
                pady=8
            )
            self.undo_btn.pack(side=tk.RIGHT)
            self.undo_btn.bind('<Button-1>', lambda e: self._handle_undo())
            self.undo_btn.bind('<Enter>', lambda e: self.undo_btn.config(bg=self.BUTTON_HOVER))
            self.undo_btn.bind('<Leave>', lambda e: self.undo_btn.config(bg=self.BUTTON_BG))
    
    def _start_auto_dismiss(self):
        """Start auto-dismiss countdown with progress bar"""
        if not hasattr(self, 'progress_canvas'):
            # No progress bar, just use timer
            self.root.after(self.auto_dismiss_seconds * 1000, self._auto_dismiss)
            return
        
        # Animate progress bar
        self.progress_start_time = time.time()
        self._update_progress()
    
    def _update_progress(self):
        """Update progress bar animation"""
        if self.dismissed or not hasattr(self, 'progress_canvas'):
            return
        
        try:
            elapsed = time.time() - self.progress_start_time
            progress = elapsed / self.auto_dismiss_seconds
            
            if progress >= 1.0:
                self._auto_dismiss()
                return
            
            # Update progress bar width
            canvas_width = self.progress_canvas.winfo_width()
            if canvas_width > 1:  # Ensure canvas is rendered
                fill_width = canvas_width * progress
                self.progress_canvas.coords(self.progress_bar, 0, 0, fill_width, 3)
            
            # Schedule next update (60 FPS)
            self.root.after(16, self._update_progress)
        except:
            pass
    
    def _fade_in(self, alpha=0.0):
        """Smooth fade in animation"""
        if alpha < 1.0:
            alpha += 0.08
            try:
                self.root.attributes('-alpha', alpha)
                self.root.after(16, lambda: self._fade_in(alpha))
            except:
                pass
        else:
            try:
                self.root.attributes('-alpha', 1.0)
            except:
                pass
    
    def _fade_out(self, alpha=1.0):
        """Smooth fade out animation"""
        if alpha > 0.0:
            alpha -= 0.12
            try:
                self.root.attributes('-alpha', alpha)
                self.root.after(16, lambda: self._fade_out(alpha))
            except:
                pass
        else:
            self._destroy()
    
    def _handle_undo(self):
        """Handle undo button click"""
        if self.undo_callback and not self.dismissed:
            self.dismissed = True
            try:
                self.undo_callback()
            except Exception as e:
                print(f"Error in undo callback: {e}")
        self.close()
    
    def _auto_dismiss(self):
        """Auto-dismiss after timeout"""
        if not self.dismissed:
            self.close()
    
    def close(self):
        """Close notification with fade out"""
        if not self.dismissed:
            self.dismissed = True
            self._fade_out()
    
    def _destroy(self):
        """Actually destroy the window"""
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        
        # Decrement instance counter
        with ModernPIINotification._instance_lock:
            ModernPIINotification._instance_count = max(0, ModernPIINotification._instance_count - 1)
        
        # Call on_close callback
        if self.on_close:
            try:
                self.on_close(self)
            except:
                pass


# Global notification manager instance
_notification_manager = None

def get_notification_manager() -> NotificationManager:
    """Get global notification manager instance"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager(auto_dismiss_seconds=5)
    return _notification_manager


def show_pii_notification(
    num_items: int,
    items_preview: str = "",
    source: str = "system",
    undo_callback: Optional[Callable] = None
):
    """
    Convenience function to show PII detection notification.
    
    Args:
        num_items: Number of PII items detected
        items_preview: Brief preview text
        source: Source of detection (clipboard/typing)
        undo_callback: Function to call on undo
    """
    manager = get_notification_manager()
    manager.show_pii_detected(num_items, items_preview, source, undo_callback)


if __name__ == "__main__":
    # Test notifications with modern design
    print("Testing MODERN notification system...")
    print("Will show 3 test notifications with new design")
    
    def test_undo():
        print("Undo clicked!")
    
    # Get the notification manager
    manager = get_notification_manager()
    
    # Schedule test notifications to appear after a delay
    def schedule_notifications():
        """Schedule notifications from a background thread"""
        time.sleep(0.5)
        
        show_pii_notification(
            num_items=2,
            items_preview="john@email.com, John Smith",
            source="clipboard",
            undo_callback=test_undo
        )
        
        time.sleep(1.5)
        
        show_pii_notification(
            num_items=1,
            items_preview="555-123-4567",
            source="typing",
            undo_callback=test_undo
        )
        
        time.sleep(1.5)
        
        show_pii_notification(
            num_items=4,
            items_preview="alice@company.com, 123-45-6789, Alice Johnson, 4532-0151-1283",
            source="clipboard",
            undo_callback=test_undo
        )
        
        print("Modern notifications shown. They will auto-dismiss after 5 seconds.")
        print("Watch the progress bar animation!")
        print("Close the window or press Ctrl+C to exit")
    
    # Start notification thread
    threading.Thread(target=schedule_notifications, daemon=True).start()
    
    # Start manager in main thread (this will block)
    try:
        manager.start()
    except KeyboardInterrupt:
        print("\nExiting...")
        manager.stop()