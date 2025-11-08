"""
System Tray Desktop App Monitor
Runs desktop app PII monitor with system tray controls.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pystray
from PIL import Image, ImageDraw
import threading
from desktop_app_monitor import DesktopAppMonitor


class TrayDesktopMonitor:
    """System tray application for desktop app monitoring"""
    
    def __init__(self):
        self.monitor = None
        self.monitoring = False
        self.monitor_thread = None
        self.icon = None
    
    def create_icon_image(self, color='green'):
        """Create tray icon"""
        img = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw shield with app icon
        if color == 'green':
            fill_color = (0, 200, 0)
        elif color == 'red':
            fill_color = (200, 0, 0)
        else:
            fill_color = (128, 128, 128)
        
        # Shield shape
        draw.polygon([
            (32, 5),
            (55, 15),
            (55, 40),
            (32, 55),
            (9, 40),
            (9, 15)
        ], fill=fill_color, outline='black')
        
        # "D" for Desktop
        draw.text((22, 20), "D", fill='white', font_size=20)
        
        return img
    
    def start_monitoring(self, icon, item):
        """Start monitoring"""
        if self.monitoring:
            return
        
        print("Starting desktop app monitoring...")
        
        # Create monitor
        self.monitor = DesktopAppMonitor(
            buffer_size=500,
            check_interval=1.5,
            enable_replacement=True,
            enable_notifications=True
        )
        
        # Start in background thread
        self.monitor_thread = threading.Thread(target=self.monitor.start, daemon=True)
        self.monitor_thread.start()
        
        self.monitoring = True
        
        # Update icon
        icon.icon = self.create_icon_image('green')
        icon.title = "PII Guard Desktop - Active"
    
    def stop_monitoring(self, icon, item):
        """Stop monitoring"""
        if not self.monitoring:
            return
        
        print("Stopping desktop app monitoring...")
        
        if self.monitor:
            self.monitor.close()
            self.monitor = None
        
        self.monitoring = False
        
        # Update icon
        icon.icon = self.create_icon_image('red')
        icon.title = "PII Guard Desktop - Stopped"
    
    def show_stats(self, icon, item):
        """Show statistics"""
        if self.monitor:
            self.monitor.print_stats()
        else:
            print("Monitor not running")
    
    def quit_app(self, icon, item):
        """Quit application"""
        print("Quitting...")
        
        if self.monitoring:
            self.stop_monitoring(icon, item)
        
        icon.stop()
    
    def run(self):
        """Run system tray application"""
        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem(
                'Start Protection',
                self.start_monitoring,
                default=True,
                visible=lambda item: not self.monitoring
            ),
            pystray.MenuItem(
                'Stop Protection',
                self.stop_monitoring,
                visible=lambda item: self.monitoring
            ),
            pystray.MenuItem('Show Statistics', self.show_stats),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', self.quit_app)
        )
        
        # Create icon
        self.icon = pystray.Icon(
            name="PII Guard Desktop",
            icon=self.create_icon_image('red'),
            title="PII Guard Desktop - Stopped",
            menu=menu
        )
        
        print("=" * 60)
        print("PII GUARD DESKTOP - SYSTEM TRAY")
        print("=" * 60)
        print("✓ System tray icon created")
        print("✓ Right-click icon to control")
        print("=" * 60 + "\n")
        
        # Auto-start monitoring
        self.start_monitoring(self.icon, None)
        
        # Run icon (blocks until quit)
        self.icon.run()


def main():
    """Main entry point"""
    try:
        app = TrayDesktopMonitor()
        app.run()
    except KeyboardInterrupt:
        print("\nReceived interrupt")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()