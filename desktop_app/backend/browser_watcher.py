"""
Browser watcher - Monitors browser tabs for Gmail
"""
import threading
import time
import socket
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class BrowserWatcher(threading.Thread):
    """Monitor browser tabs for Gmail pages"""
    
    def __init__(self, permission_manager, callback=None):
        super().__init__()
        self.permission_manager = permission_manager
        self.callback = callback
        self.running = False
        self.daemon = True
        self.server = None
        
    def run(self):
        """Start the browser watcher"""
        self.running = True
        
        # Start a simple socket server for browser extension communication
        self.start_extension_server()
        
        while self.running:
            time.sleep(1)
    
    def start_extension_server(self):
        """Start server for browser extension communication"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind(('localhost', 9876))
            self.server.listen(5)
            self.server.settimeout(1)
            
            # Start listener thread
            listener = threading.Thread(target=self.listen_for_extensions)
            listener.daemon = True
            listener.start()
            
        except Exception as e:
            print(f"Failed to start extension server: {e}")
    
    def listen_for_extensions(self):
        """Listen for messages from browser extension"""
        while self.running:
            try:
                client, addr = self.server.accept()
                data = client.recv(4096)
                if data:
                    self.handle_extension_message(json.loads(data.decode()))
                client.close()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Extension server error: {e}")
    
    def handle_extension_message(self, message):
        """Handle messages from browser extension"""
        if message.get('type') == 'gmail_page':
            self.handle_gmail_page(message)
    
    def handle_gmail_page(self, message):
        """Handle detected Gmail page"""
        if self.callback:
            self.callback({
                'type': 'gmail_page_detected',
                'url': message.get('url'),
                'title': message.get('title'),
                'tab_id': message.get('tab_id')
            })
    
    def stop(self):
        """Stop the browser watcher"""
        self.running = False
        if self.server:
            self.server.close()