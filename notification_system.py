"""
Notification System for PII Guard - ULTRA MODERN UI
Beautiful, abstract, light-themed notifications with glass-morphism effects.
Inspired by iOS 16, macOS Ventura, and Material Design 3.
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
    - Ultra-modern glass-morphism design
    - Light, airy color palette
    - Beautiful animations
    - Auto-dismiss with progress indicator
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
    Ultra-modern notification with glass-morphism and abstract design.
    Light, airy, and beautiful.
    """
    
    # Modern design constants
    NOTIFICATION_WIDTH = 400
    NOTIFICATION_HEIGHT = 160
    MARGIN_RIGHT = 24
    MARGIN_BOTTOM = 24
    STACK_OFFSET = 180
    BORDER_RADIUS = 24  # Large rounded corners
    
    # Light, modern color palette (iOS/Material Design 3 inspired)
    BG_COLOR = "#FFFFFF"  # Pure white
    BG_GRADIENT_START = "#F8FAFC"  # Very light blue-gray
    BG_GRADIENT_END = "#FFFFFF"
    
    ACCENT_GRADIENT_1 = "#667EEA"  # Soft purple
    ACCENT_GRADIENT_2 = "#764BA2"  # Deep purple
    
    SUCCESS_GRADIENT_1 = "#4F46E5"  # Indigo
    SUCCESS_GRADIENT_2 = "#7C3AED"  # Purple
    
    TEXT_PRIMARY = "#1E293B"  # Slate 800
    TEXT_SECONDARY = "#64748B"  # Slate 500
    TEXT_TERTIARY = "#94A3B8"  # Slate 400
    
    BUTTON_BG = "#F1F5F9"  # Slate 100
    BUTTON_HOVER = "#E2E8F0"  # Slate 200
    BUTTON_TEXT = "#475569"  # Slate 600
    
    CLOSE_COLOR = "#94A3B8"
    CLOSE_HOVER = "#EF4444"  # Red 500
    
    SHADOW_COLOR = "rgba(0, 0, 0, 0.08)"
    
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
        self.root.title("")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        # Set size and position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = screen_width - self.NOTIFICATION_WIDTH - self.MARGIN_RIGHT
        y = screen_height - self.NOTIFICATION_HEIGHT - self.MARGIN_BOTTOM
        y -= self.instance_num * self.STACK_OFFSET
        
        self.root.geometry(f"{self.NOTIFICATION_WIDTH}x{self.NOTIFICATION_HEIGHT}+{x}+{y}")
        
        # Configure background (white)
        self.root.configure(bg='white')
        
        # Create UI
        self._create_modern_ui(num_items, items_preview, source)
        
        # Auto-dismiss with progress
        if auto_dismiss_seconds > 0:
            self._start_auto_dismiss()
        
        # Smooth entrance animation
        self.root.attributes('-alpha', 0.0)
        self._animate_entrance()
    
    def _create_rounded_rectangle(self, canvas, x1, y1, x2, y2, radius=20, **kwargs):
        """Create a rounded rectangle on canvas"""
        points = [
            x1+radius, y1,
            x1+radius, y1,
            x2-radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1+radius,
            x1, y1
        ]
        return canvas.create_polygon(points, **kwargs, smooth=True)
    
    def _create_modern_ui(self, num_items: int, items_preview: str, source: str):
        """Create ultra-modern notification UI"""
        # Main canvas for custom drawing
        self.canvas = tk.Canvas(
            self.root,
            width=self.NOTIFICATION_WIDTH,
            height=self.NOTIFICATION_HEIGHT,
            bg='white',
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw shadow (multiple layers for soft shadow)
        shadow_layers = 3
        for i in range(shadow_layers):
            offset = 4 + i * 2
            alpha_value = int(30 - i * 8)
            shadow_color = f"#{alpha_value:02x}{alpha_value:02x}{alpha_value:02x}"
            self._create_rounded_rectangle(
                self.canvas,
                2 + i, 2 + i,
                self.NOTIFICATION_WIDTH - 2 - i,
                self.NOTIFICATION_HEIGHT - 2 - i,
                radius=self.BORDER_RADIUS - i,
                fill=shadow_color,
                outline=''
            )
        
        # Draw main card with gradient effect
        self.card_bg = self._create_rounded_rectangle(
            self.canvas,
            6, 6,
            self.NOTIFICATION_WIDTH - 6,
            self.NOTIFICATION_HEIGHT - 6,
            radius=self.BORDER_RADIUS,
            fill=self.BG_COLOR,
            outline=self.TEXT_TERTIARY,
            width=1
        )
        
        # Draw accent bar (gradient)
        self.accent_bar = self.canvas.create_rectangle(
            16, 16,
            24, self.NOTIFICATION_HEIGHT - 16,
            fill=self.ACCENT_GRADIENT_1,
            outline=''
        )
        
        # Add gradient effect to accent bar
        bar_height = self.NOTIFICATION_HEIGHT - 32
        steps = 20
        for i in range(steps):
            y = 16 + (bar_height * i / steps)
            h = bar_height / steps
            # Interpolate colors
            ratio = i / steps
            color = self._interpolate_color(self.ACCENT_GRADIENT_1, self.ACCENT_GRADIENT_2, ratio)
            self.canvas.create_rectangle(
                16, y,
                24, y + h,
                fill=color,
                outline=''
            )
        
        # === CONTENT FRAME ===
        content_frame = tk.Frame(self.canvas, bg=self.BG_COLOR)
        self.canvas.create_window(
            44, 20,
            window=content_frame,
            anchor='nw',
            width=self.NOTIFICATION_WIDTH - 88
        )
        
        # === HEADER ===
        header = tk.Frame(content_frame, bg=self.BG_COLOR)
        header.pack(fill=tk.X, pady=(0, 8))
        
        # Icon (modern shield)
        icon = tk.Label(
            header,
            text="🛡",
            bg=self.BG_COLOR,
            font=('Segoe UI Emoji', 22)
        )
        icon.pack(side=tk.LEFT, padx=(0, 12))
        
        # Title
        title_frame = tk.Frame(header, bg=self.BG_COLOR)
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title = tk.Label(
            title_frame,
            text="PII Protected",
            bg=self.BG_COLOR,
            fg=self.ACCENT_GRADIENT_1,
            font=('Segoe UI', 13, 'bold')
        )
        title.pack(anchor='w')
        
        # Subtitle
        subtitle = tk.Label(
            title_frame,
            text="Data secured automatically",
            bg=self.BG_COLOR,
            fg=self.TEXT_TERTIARY,
            font=('Segoe UI', 8)
        )
        subtitle.pack(anchor='w')
        
        # Close button (modern, minimal)
        close_container = tk.Frame(header, bg=self.BG_COLOR)
        close_container.pack(side=tk.RIGHT)
        
        self.close_btn = tk.Label(
            close_container,
            text="✕",
            bg=self.BG_COLOR,
            fg=self.CLOSE_COLOR,
            font=('Segoe UI', 16),
            cursor='hand2',
            padx=6,
            pady=2
        )
        self.close_btn.pack()
        self.close_btn.bind('<Button-1>', lambda e: self.close())
        self.close_btn.bind('<Enter>', lambda e: self.close_btn.config(fg=self.CLOSE_HOVER))
        self.close_btn.bind('<Leave>', lambda e: self.close_btn.config(fg=self.CLOSE_COLOR))
        
        # === MESSAGE ===
        if num_items == 1:
            message = f"Protected 1 item • {source}"
        else:
            message = f"Protected {num_items} items • {source}"
        
        msg = tk.Label(
            content_frame,
            text=message,
            bg=self.BG_COLOR,
            fg=self.TEXT_PRIMARY,
            font=('Segoe UI', 10, 'bold'),
            anchor='w',
            justify='left'
        )
        msg.pack(fill=tk.X, pady=(0, 6))
        
        # === PREVIEW ===
        if items_preview and len(items_preview) > 0:
            preview = items_preview[:70] + "..." if len(items_preview) > 70 else items_preview
            preview_label = tk.Label(
                content_frame,
                text=preview,
                bg=self.BG_COLOR,
                fg=self.TEXT_SECONDARY,
                font=('Segoe UI', 9),
                anchor='w',
                justify='left',
                wraplength=280
            )
            preview_label.pack(fill=tk.X, pady=(0, 12))
        
        # === BOTTOM ROW ===
        bottom = tk.Frame(content_frame, bg=self.BG_COLOR)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Undo button (pill-shaped, modern)
        if self.undo_callback:
            undo_container = tk.Frame(bottom, bg=self.BUTTON_BG, bd=0)
            undo_container.pack(side=tk.RIGHT)
            
            self.undo_btn = tk.Label(
                undo_container,
                text="↶  Undo",
                bg=self.BUTTON_BG,
                fg=self.BUTTON_TEXT,
                font=('Segoe UI', 9, 'bold'),
                cursor='hand2',
                padx=16,
                pady=7
            )
            self.undo_btn.pack()
            self.undo_btn.bind('<Button-1>', lambda e: self._handle_undo())
            self.undo_btn.bind('<Enter>', lambda e: self._undo_hover_in())
            self.undo_btn.bind('<Leave>', lambda e: self._undo_hover_out())
        
        # Progress indicator (circular dots)
        if self.auto_dismiss_seconds > 0:
            self.progress_container = tk.Frame(bottom, bg=self.BG_COLOR)
            self.progress_container.pack(side=tk.LEFT)
            
            self.progress_dots = []
            dot_count = 5
            for i in range(dot_count):
                dot = tk.Label(
                    self.progress_container,
                    text="●",
                    bg=self.BG_COLOR,
                    fg=self.TEXT_TERTIARY,
                    font=('Segoe UI', 8)
                )
                dot.pack(side=tk.LEFT, padx=2)
                self.progress_dots.append(dot)
    
    def _interpolate_color(self, color1, color2, ratio):
        """Interpolate between two hex colors"""
        # Convert hex to RGB
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
        
        # Interpolate
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _undo_hover_in(self):
        """Undo button hover in"""
        self.undo_btn.config(bg=self.BUTTON_HOVER, fg=self.TEXT_PRIMARY)
    
    def _undo_hover_out(self):
        """Undo button hover out"""
        self.undo_btn.config(bg=self.BUTTON_BG, fg=self.BUTTON_TEXT)
    
    def _start_auto_dismiss(self):
        """Start auto-dismiss countdown with dot animation"""
        self.progress_start_time = time.time()
        self._update_progress_dots()
    
    def _update_progress_dots(self):
        """Update progress dot animation"""
        if self.dismissed or not hasattr(self, 'progress_dots'):
            return
        
        try:
            elapsed = time.time() - self.progress_start_time
            progress = elapsed / self.auto_dismiss_seconds
            
            if progress >= 1.0:
                self._auto_dismiss()
                return
            
            # Update dots based on progress
            filled_dots = int(progress * len(self.progress_dots))
            for i, dot in enumerate(self.progress_dots):
                if i < filled_dots:
                    dot.config(fg=self.ACCENT_GRADIENT_1)
                else:
                    dot.config(fg=self.TEXT_TERTIARY)
            
            # Schedule next update
            self.root.after(100, self._update_progress_dots)
        except:
            pass
    
    def _animate_entrance(self, scale=0.8, alpha=0.0):
        """Smooth entrance animation with scale and fade"""
        if scale < 1.0 or alpha < 1.0:
            scale = min(1.0, scale + 0.05)
            alpha = min(1.0, alpha + 0.1)
            
            try:
                self.root.attributes('-alpha', alpha)
                self.root.after(16, lambda: self._animate_entrance(scale, alpha))
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
            alpha -= 0.15
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
    # Test notifications with ultra-modern design
    print("Testing ULTRA-MODERN notification system...")
    print("Light theme, glass-morphism, rounded corners!")
    
    def test_undo():
        print("Undo clicked!")
    
    manager = get_notification_manager()
    
    def schedule_notifications():
        """Schedule test notifications"""
        time.sleep(0.5)
        
        show_pii_notification(
            num_items=2,
            items_preview="john@email.com, John Smith",
            source="clipboard",
            undo_callback=test_undo
        )
        
        time.sleep(2)
        
        show_pii_notification(
            num_items=1,
            items_preview="555-123-4567",
            source="typing",
            undo_callback=test_undo
        )
        
        time.sleep(2)
        
        show_pii_notification(
            num_items=4,
            items_preview="alice@company.com, 123-45-6789, Alice Johnson, Credit Card",
            source="clipboard",
            undo_callback=test_undo
        )
        
        print("\nModern notifications shown!")
        print("Features:")
        print("  ✓ Large rounded corners (24px)")
        print("  ✓ Light color scheme")
        print("  ✓ Purple gradient accent bar")
        print("  ✓ Soft shadows")
        print("  ✓ Animated progress dots")
        print("  ✓ Smooth entrance/exit")
        print("\nThey will auto-dismiss after 5 seconds.")
    
    threading.Thread(target=schedule_notifications, daemon=True).start()
    
    try:
        manager.start()
    except KeyboardInterrupt:
        print("\nExiting...")
        manager.stop()