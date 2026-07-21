"""
System tray notifications for phishing detector
"""
import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
import sys
import os

class NotificationManager:
    """Manage system notifications and tray icon"""
    
    def __init__(self, root, callback=None):
        self.root = root
        self.callback = callback
        self.notifications = []
        self.notification_window = None
        self.has_tray = False
        self.tray_icon = None
        
        # Try to import pystray and PIL (optional)
        try:
            import pystray
            import PIL.Image
            import PIL.ImageDraw
            self.pystray = pystray
            self.PIL = PIL
            self.has_tray = True
            print("✅ System tray available")
        except ImportError as e:
            print(f"ℹ️ System tray disabled: {e}")
    
    def setup_tray_icon(self):
        """Setup system tray icon"""
        if not self.has_tray:
            return
            
        try:
            # Create a simple icon using PIL
            icon_size = 64
            image = self.PIL.Image.new('RGB', (icon_size, icon_size), color='white')
            draw = self.PIL.ImageDraw.Draw(image)
            
            # Draw shield icon
            draw.ellipse([10, 10, 54, 54], fill='blue', outline='darkblue', width=2)
            
            # Add text (simulating the shield emoji)
            draw.text([22, 22], "🛡️", fill='white')
            
            # Create menu
            menu = self.pystray.Menu(
                self.pystray.MenuItem("Open Dashboard", self.open_dashboard),
                self.pystray.MenuItem("Scan Now", self.scan_now),
                self.pystray.MenuItem("Settings", self.open_settings),
                self.pystray.Menu.SEPARATOR,
                self.pystray.MenuItem("Exit", self.exit_app)
            )
            
            # Create icon
            self.tray_icon = self.pystray.Icon(
                "phishing_detector",
                image,
                "Phishing Detector",
                menu
            )
            
            # Run tray icon in separate thread (don't start automatically)
            # We'll start it when needed
            
        except Exception as e:
            print(f"⚠️ Failed to setup system tray: {e}")
            self.has_tray = False
    
    def show_tray(self):
        """Show the system tray icon"""
        if self.has_tray and self.tray_icon and not self.tray_icon.visible:
            try:
                self.tray_icon.run_detached()
            except Exception as e:
                print(f"⚠️ Failed to show tray: {e}")
    
    def hide_tray(self):
        """Hide the system tray icon"""
        if self.has_tray and self.tray_icon and self.tray_icon.visible:
            try:
                self.tray_icon.stop()
            except:
                pass
    
    def open_dashboard(self):
        """Open main dashboard"""
        if self.callback:
            self.callback('open_dashboard')
    
    def scan_now(self):
        """Trigger manual scan"""
        if self.callback:
            self.callback('scan_now')
    
    def open_settings(self):
        """Open settings"""
        if self.callback:
            self.callback('open_settings')
    
    def exit_app(self):
        """Exit application"""
        if self.callback:
            self.callback('exit')
    
    def show_notification(self, title, message, notification_type='info'):
        """Show a desktop notification"""
        # Try using plyer for cross-platform notifications
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name='Phishing Detector',
                timeout=5
            )
            return
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️ Notification error: {e}")
        
        # Fallback to custom notification window
        self.show_custom_notification(title, message, notification_type)
    
    def show_custom_notification(self, title, message, notification_type):
        """Show custom notification window"""
        # Close existing notification
        if self.notification_window:
            self.notification_window.destroy()
        
        # Create new notification window
        self.notification_window = tk.Toplevel(self.root)
        self.notification_window.overrideredirect(True)
        self.notification_window.attributes('-topmost', True)
        
        # Set colors based on type
        if notification_type == 'warning':
            bg_color = '#fff3cd'
            fg_color = '#856404'
            icon = "⚠️"
        elif notification_type == 'error':
            bg_color = '#f8d7da'
            fg_color = '#721c24'
            icon = "❌"
        else:
            bg_color = '#d4edda'
            fg_color = '#155724'
            icon = "✅"
        
        # Position in bottom-right corner
        self.notification_window.update_idletasks()
        screen_width = self.notification_window.winfo_screenwidth()
        screen_height = self.notification_window.winfo_screenheight()
        window_width = 350
        window_height = 120
        x = screen_width - window_width - 20
        y = screen_height - window_height - 40
        self.notification_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Style
        self.notification_window.configure(bg=bg_color)
        
        # Content
        frame = tk.Frame(self.notification_window, bg=bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title with icon
        title_label = tk.Label(frame, text=f"{icon} {title}", 
                               font=('Helvetica', 12, 'bold'),
                               bg=bg_color, fg=fg_color)
        title_label.pack(anchor=tk.W)
        
        # Message
        msg_label = tk.Label(frame, text=message, wraplength=300,
                            bg=bg_color, fg=fg_color, justify=tk.LEFT)
        msg_label.pack(anchor=tk.W, pady=5, fill=tk.X)
        
        # Close button
        close_btn = tk.Button(frame, text="×", command=self.close_notification,
                             bg=bg_color, fg=fg_color, bd=0,
                             font=('Helvetica', 14, 'bold'),
                             cursor='hand2')
        close_btn.place(relx=1.0, x=0, y=0, anchor='ne')
        
        # Auto-close after 5 seconds
        self.root.after(5000, self.close_notification)
    
    def close_notification(self):
        """Close notification window"""
        if self.notification_window:
            self.notification_window.destroy()
            self.notification_window = None
    
    def show_phishing_alert(self, email_data, result):
        """Show phishing alert notification"""
        title = "⚠️ PHISHING ALERT!"
        message = f"From: {email_data['from']}\nSubject: {email_data['subject'][:30]}...\nConfidence: {result.get('confidence', 0):.1f}%"
        self.show_notification(title, message, 'warning')
    
    def show_legitimate_alert(self, email_data, result):
        """Show legitimate email notification (optional)"""
        title = "✅ Safe Email"
        message = f"From: {email_data['from']}\nSubject: {email_data['subject'][:30]}..."
        self.show_notification(title, message, 'info')
    
    def show_scan_complete(self, stats):
        """Show scan complete notification"""
        title = "✅ Scan Complete"
        message = f"Scanned {stats['scanned']} emails\nFound {stats['phishing']} phishing attempts"
        self.show_notification(title, message, 'info')