"""
Notification System for PII Guard
Small, non-intrusive notifications with undo functionality.
Uses Windows toast notifications for minimal UI footprint.
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
    Manages small notification popups for PII detections.
    
    Features:
    - Small, side-positioned notifications
    - Auto-dismiss after timeout
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
        notification = PIINotificationPopup(
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


class PIINotificationPopup:
    """
    Small notification popup window.
    Positioned at bottom-right of screen, minimal and unobtrusive.
    """
    
    # Notification positioning
    NOTIFICATION_WIDTH = 320
    NOTIFICATION_HEIGHT = 130
    MARGIN_RIGHT = 20
    MARGIN_BOTTOM = 20
    STACK_OFFSET = 140  # Vertical offset for stacked notifications
    
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
        
        # Track instance number for stacking
        with PIINotificationPopup._instance_lock:
            self.instance_num = PIINotificationPopup._instance_count
            PIINotificationPopup._instance_count += 1
        
        # Create window (must be called from main thread)
        self.root = tk.Toplevel()
        self.root.title("PII Guard")
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.attributes('-topmost', True)  # Always on top
        
        # Set size and position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = screen_width - self.NOTIFICATION_WIDTH - self.MARGIN_RIGHT
        y = screen_height - self.NOTIFICATION_HEIGHT - self.MARGIN_BOTTOM
        y -= self.instance_num * self.STACK_OFFSET  # Stack vertically
        
        self.root.geometry(f"{self.NOTIFICATION_WIDTH}x{self.NOTIFICATION_HEIGHT}+{x}+{y}")
        
        # Configure style
        style = ttk.Style(self.root)
        style.configure('Notification.TFrame', background='#2d2d2d')
        style.configure('NotificationTitle.TLabel', 
                       background='#2d2d2d', 
                       foreground='#ffa500',
                       font=('Segoe UI', 10, 'bold'))
        style.configure('NotificationText.TLabel',
                       background='#2d2d2d',
                       foreground='#ffffff',
                       font=('Segoe UI', 9))
        style.configure('Undo.TButton', 
                       font=('Segoe UI', 9, 'bold'),
                       padding=6)
        
        # Create UI
        self._create_ui(num_items, items_preview, source)
        
        # Auto-dismiss timer
        if auto_dismiss_seconds > 0:
            self.root.after(auto_dismiss_seconds * 1000, self._auto_dismiss)
        
        # Fade in animation
        self.root.attributes('-alpha', 0.0)
        self._fade_in()
    
    def _create_ui(self, num_items: int, items_preview: str, source: str):
        """Create notification UI"""
        # Main frame
        main_frame = ttk.Frame(self.root, style='Notification.TFrame', padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame, style='Notification.TFrame')
        header_frame.pack(fill=tk.X)
        
        # Icon + Title
        icon_label = ttk.Label(header_frame, text="🛡️", 
                              background='#2d2d2d', font=('Segoe UI', 14))
        icon_label.pack(side=tk.LEFT, padx=(0, 5))
        
        title_label = ttk.Label(header_frame, text="PII Protected",
                               style='NotificationTitle.TLabel')
        title_label.pack(side=tk.LEFT)
        
        # Close button
        close_btn = ttk.Button(header_frame, text="✕", width=3,
                               command=self.close)
        close_btn.pack(side=tk.RIGHT)
        
        # Message
        if num_items == 1:
            message = f"1 item obfuscated in {source}"
        else:
            message = f"{num_items} items obfuscated in {source}"
        
        msg_label = ttk.Label(main_frame, text=message,
                             style='NotificationText.TLabel',
                             wraplength=260)
        msg_label.pack(pady=(5, 0))
        
        # Preview (truncated)
        if items_preview and len(items_preview) > 0:
            preview = items_preview[:50] + "..." if len(items_preview) > 50 else items_preview
            preview_label = ttk.Label(main_frame, text=preview,
                                     style='NotificationText.TLabel',
                                     wraplength=260)
            preview_label.pack(pady=(2, 0))
        
        # Undo button (more prominent)
        if self.undo_callback:
            button_frame = ttk.Frame(main_frame, style='Notification.TFrame')
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            undo_btn = ttk.Button(button_frame, text="↶ Undo", 
                                 style='Undo.TButton',
                                 command=self._handle_undo,
                                 width=10)
            undo_btn.pack(side=tk.RIGHT)
    
    def _fade_in(self, alpha=0.0):
        """Fade in animation"""
        if alpha < 0.95:
            alpha += 0.05
            try:
                self.root.attributes('-alpha', alpha)
                self.root.after(20, lambda: self._fade_in(alpha))
            except:
                pass
        else:
            try:
                self.root.attributes('-alpha', 0.95)
            except:
                pass
    
    def _fade_out(self, alpha=0.95):
        """Fade out animation"""
        if alpha > 0.0:
            alpha -= 0.1
            try:
                self.root.attributes('-alpha', alpha)
                self.root.after(20, lambda: self._fade_out(alpha))
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
        with PIINotificationPopup._instance_lock:
            PIINotificationPopup._instance_count = max(0, PIINotificationPopup._instance_count - 1)
        
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
    # Test notifications
    print("Testing notification system...")
    print("Will show 3 test notifications")
    
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
        
        time.sleep(1)
        
        show_pii_notification(
            num_items=1,
            items_preview="555-123-4567",
            source="typing",
            undo_callback=test_undo
        )
        
        time.sleep(1)
        
        show_pii_notification(
            num_items=3,
            items_preview="alice@company.com, 123-45-6789, Alice Johnson",
            source="clipboard",
            undo_callback=None  # No undo
        )
        
        print("Notifications shown. They will auto-dismiss after 5 seconds.")
        print("Close the window or press Ctrl+C to exit")
    
    # Start notification thread
    threading.Thread(target=schedule_notifications, daemon=True).start()
    
    # Start manager in main thread (this will block)
    try:
        manager.start()
    except KeyboardInterrupt:
        print("\nExiting...")
        manager.stop()