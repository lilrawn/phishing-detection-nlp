"""
Permission manager - Handles user permissions and system integration
"""
import os
import sys
import json
import platform
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog

class PermissionManager:
    """Manage user permissions for email access and system integration"""
    
    def __init__(self):
        self.os_name = platform.system()
        self.config_dir = Path.home() / '.phishing_detector'
        self.config_file = self.config_dir / 'config.json'
        self.permissions = self.load_permissions()
        
    def load_permissions(self):
        """Load saved permissions"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return self.get_default_permissions()
        return self.get_default_permissions()
    
    def get_default_permissions(self):
        """Default permission structure"""
        return {
            'gmail_access': False,
            'browser_monitoring': False,
            'notifications': True,
            'background_running': False,
            'gmail_accounts': [],
            'settings': {
                'check_interval': 30,  # seconds
                'auto_scan': True,
                'show_notifications': True,
                'sound_alerts': True
            }
        }
    
    def save_permissions(self):
        """Save permissions to config file"""
        self.config_dir.mkdir(exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.permissions, f, indent=2)
    
    def request_gmail_permission(self):
        """Request Gmail access permission"""
        root = tk.Tk()
        root.withdraw()
        
        message = (
            "🔐 Gmail Access Required\n\n"
            "Phishing Detector needs access to your Gmail account to:\n"
            "• Scan incoming emails for phishing attempts\n"
            "• Protect you from malicious links\n"
            "• Alert you about suspicious messages\n\n"
            "Your email credentials will be stored locally and encrypted.\n"
            "No data is ever sent to external servers.\n\n"
            "Do you want to grant access?"
        )
        
        result = messagebox.askyesno("Permission Required", message)
        
        if result:
            # Get Gmail credentials
            email = simpledialog.askstring("Gmail Login", "Enter your Gmail address:", parent=root)
            if email:
                password = simpledialog.askstring("Gmail Login", "Enter your App Password:", 
                                                 parent=root, show='*')
                if password:
                    self.permissions['gmail_access'] = True
                    self.permissions['gmail_accounts'].append({
                        'email': email,
                        'password': self.encrypt_password(password),
                        'enabled': True
                    })
                    self.save_permissions()
                    messagebox.showinfo("Success", "✅ Gmail access granted!")
                    return True
        
        return False
    
    def request_browser_permission(self):
        """Request browser monitoring permission"""
        root = tk.Tk()
        root.withdraw()
        
        message = (
            "🌐 Browser Monitoring Permission\n\n"
            "Phishing Detector can monitor your browser tabs to:\n"
            "• Detect when you're on Gmail\n"
            "• Scan emails you're reading\n"
            "• Alert you about phishing websites\n\n"
            "This requires browser extension installation.\n\n"
            "Do you want to enable browser monitoring?"
        )
        
        result = messagebox.askyesno("Permission Required", message)
        
        if result:
            self.permissions['browser_monitoring'] = True
            self.save_permissions()
            self.show_browser_extension_instructions()
            return True
        return False
    
    def show_browser_extension_instructions(self):
        """Show instructions for browser extension"""
        root = tk.Tk()
        root.withdraw()
        
        message = (
            "📦 Browser Extension Setup\n\n"
            "To enable browser monitoring:\n\n"
            "1. Open Chrome/Edge/Firefox\n"
            "2. Go to extensions page\n"
            "3. Enable 'Developer Mode'\n"
            "4. Load unpacked extension from:\n"
            f"   {self.config_dir / 'extension'}\n\n"
            "The extension files have been copied to this location."
        )
        
        messagebox.showinfo("Browser Extension", message)
    
    def request_background_permission(self):
        """Request permission to run in background"""
        root = tk.Tk()
        root.withdraw()
        
        message = (
            "🔄 Background Running Permission\n\n"
            "Phishing Detector can run in the background to:\n"
            "• Continuously monitor for threats\n"
            "• Show real-time notifications\n"
            "• Start automatically with your computer\n\n"
            "Do you want to enable background running?"
        )
        
        result = messagebox.askyesno("Permission Required", message)
        
        if result:
            self.permissions['background_running'] = True
            self.save_permissions()
            self.setup_autostart()
            return True
        return False
    
    def setup_autostart(self):
        """Setup application to start with system"""
        if self.os_name == 'Windows':
            self.setup_windows_autostart()
        elif self.os_name == 'Darwin':
            self.setup_macos_autostart()
    
    def setup_windows_autostart(self):
        """Add to Windows startup"""
        import winreg
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_path = sys.executable
        script_path = Path(__file__).parent.parent / 'main.py'
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, 'PhishingDetector', 0, winreg.REG_SZ, f'"{app_path}" "{script_path}" --background')
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to set autostart: {e}")
    
    def setup_macos_autostart(self):
        """Add to macOS startup items"""
        plist_path = Path.home() / 'Library/LaunchAgents/com.phishingdetector.plist'
        app_path = sys.executable
        script_path = Path(__file__).parent.parent / 'main.py'
        
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.phishingdetector</string>
    <key>ProgramArguments</key>
    <array>
        <string>{app_path}</string>
        <string>{script_path}</string>
        <string>--background</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>'''
        
        plist_path.write_text(plist_content)
        os.system(f'launchctl load {plist_path}')
    
    def encrypt_password(self, password):
        """Simple encryption (in production, use proper encryption)"""
        # For demo purposes - in production, use cryptography library
        return ''.join(chr(ord(c) + 1) for c in password)
    
    def decrypt_password(self, encrypted):
        """Simple decryption"""
        return ''.join(chr(ord(c) - 1) for c in encrypted)
    
    def check_permission(self, permission_name):
        """Check if specific permission is granted"""
        return self.permissions.get(permission_name, False)