"""
Browser integration server for desktop app
"""
import threading
import json
import http.server
import socketserver
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

# Import with error handling
try:
    from src.predictor_enhanced import EnhancedPhishingPredictor
    PREDICTOR_AVAILABLE = True
except ImportError:
    from src.predictor_hybrid import HybridPredictor
    PREDICTOR_AVAILABLE = False
    print("⚠️ Using standard predictor (enhanced features disabled)")

from src.database import db

class BrowserIntegrationServer:
    def __init__(self, callback=None):
        self.callback = callback
        self.running = False
        self.http_port = 9877
        self.server = None
        self.connected_extensions = {}
        self.last_heartbeat = {}
        self.connection_history = []
        self.processed_connections = {}
        
        if PREDICTOR_AVAILABLE:
            self.predictor = EnhancedPhishingPredictor()
        else:
            self.predictor = HybridPredictor(ml_weight=0.3)
        
        self.active_sessions = {}
        print(f"🔧 BrowserIntegrationServer initialized with callback: {callback is not None}")
        
    def start(self):
        self.running = True
        self.http_thread = threading.Thread(target=self.start_http_server)
        self.http_thread.daemon = True
        self.http_thread.start()
        print(f"🌐 Browser integration server started on port {self.http_port}")
    
    def start_http_server(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def _send_cors_headers(self):
                """Send CORS headers to allow extension connections"""
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With')
                self.send_header('Access-Control-Max-Age', '86400')  # 24 hours
            
            def do_OPTIONS(self):
                """Handle preflight requests"""
                self.send_response(200)
                self._send_cors_headers()
                self.end_headers()
            
            def do_POST(self):
                if self.path == '/api/notification':
                    try:
                        # Send CORS headers
                        self.send_response(200)
                        self._send_cors_headers()
                        self.end_headers()
                        
                        content_length = int(self.headers.get('Content-Length', 0))
                        if content_length > 0:
                            post_data = self.rfile.read(content_length)
                            message = json.loads(post_data.decode())
                            
                            if hasattr(self.server, 'integration_server'):
                                self.server.integration_server.handle_message(message)
                            
                            self.wfile.write(b'{"status":"ok"}')
                        else:
                            self.wfile.write(b'{"error":"No content"}')
                    except json.JSONDecodeError:
                        self.send_response(400)
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(b'{"error":"Invalid JSON"}')
                    except Exception as e:
                        print(f"Error handling request: {e}")
                        self.send_response(500)
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(f'{{"error":"{str(e)}"}}'.encode())
                else:
                    self.send_response(404)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(b'{"error":"Not found"}')
            
            def do_GET(self):
                try:
                    # Send CORS headers
                    self.send_response(200)
                    self._send_cors_headers()
                    self.end_headers()
                    
                    if self.path == '/api/health':
                        response = {
                            'status': 'running',
                            'service': 'phishing-detector',
                            'timestamp': time.time(),
                            'connected_extensions': len(self.server.integration_server.connected_extensions)
                        }
                        self.wfile.write(json.dumps(response).encode())
                    elif self.path == '/api/status':
                        response = {
                            'connected': len(self.server.integration_server.connected_extensions) > 0,
                            'extensions': list(self.server.integration_server.connected_extensions.keys()),
                            'history': self.server.integration_server.connection_history[-5:]
                        }
                        self.wfile.write(json.dumps(response).encode())
                    else:
                        self.wfile.write(b'{"status":"running","service":"phishing-detector"}')
                except BrokenPipeError:
                    pass
                except Exception as e:
                    print(f"Error in GET request: {e}")
            
            def log_message(self, format, *args):
                pass  # Suppress logging
        
        try:
            self.server = socketserver.TCPServer(("localhost", self.http_port), Handler)
            self.server.timeout = 1
            self.server.integration_server = self
            
            print(f"   Listening for browser extension connections on port {self.http_port}...")
            
            while self.running:
                try:
                    self.server.handle_request()
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    if "timed out" not in str(e):
                        print(f"⚠️ Server error: {e}")
                    continue
                    
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"⚠️ Port {self.http_port} already in use")
            else:
                print(f"⚠️ Failed to start HTTP server: {e}")
        except Exception as e:
            print(f"⚠️ Unexpected server error: {e}")
    
    def handle_message(self, message):
        if not message:
            return
            
        msg_type = message.get('type')
        print(f"📨 Received browser message: {msg_type}")
        
        if msg_type == 'connection_status':
            self.handle_connection_status(message)
        elif msg_type == 'scan_email':
            self.handle_scan_email(message)
        elif msg_type == 'gmail_opened':
            print(f"📧 Gmail opened: {message.get('tabId')}")
            if self.callback:
                self.callback({
                    'type': 'browser_gmail_opened',
                    'tab_id': message.get('tabId'),
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
        elif msg_type == 'gmail_closed':
            print(f"📧 Gmail closed: {message.get('tabId')}")
            if self.callback:
                self.callback({
                    'type': 'browser_gmail_closed',
                    'tab_id': message.get('tabId')
                })
    
    def handle_connection_status(self, message):
        status = message.get('status')
        timestamp = message.get('timestamp')
        extension_version = message.get('extension_version', 'unknown')
        browser = message.get('browser', 'unknown')
        
        unique_string = f"{browser}_{timestamp}_{extension_version}_{time.time()}"
        extension_id = hashlib.md5(unique_string.encode()).hexdigest()[:16]
        
        current_time = time.time()
        self.processed_connections = {
            k: v for k, v in self.processed_connections.items() 
            if current_time - v < 3600
        }
        
        if status == 'connected':
            connection_key = f"{browser}_{timestamp}"
            if connection_key in self.processed_connections:
                if current_time - self.processed_connections[connection_key] < 300:
                    return
            
            self.connected_extensions[extension_id] = {
                'connected_at': timestamp,
                'last_seen': current_time,
                'version': extension_version,
                'browser': browser
            }
            self.processed_connections[connection_key] = current_time
            
            self.connection_history.append({
                'time': datetime.now().strftime("%H:%M:%S"),
                'event': 'connected',
                'browser': browser[:30] + '...' if len(browser) > 30 else browser
            })
            print(f"✅ Browser extension connected - Version: {extension_version}")
            
            if self.callback:
                self.callback({
                    'type': 'browser_connected',
                    'extension_id': extension_id,
                    'version': extension_version,
                    'browser': browser,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
        else:
            if extension_id in self.connected_extensions:
                del self.connected_extensions[extension_id]
            self.connection_history.append({
                'time': datetime.now().strftime("%H:%M:%S"),
                'event': 'disconnected',
                'browser': browser[:30] + '...' if len(browser) > 30 else browser
            })
            print("🔴 Browser extension disconnected")
            
            if self.callback:
                self.callback({
                    'type': 'browser_disconnected',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
    
    def handle_scan_email(self, message):
        email_id = message.get('emailId', 'unknown')
        email_content = message.get('emailContent', '')
        sender = message.get('sender', 'unknown@example.com')
        subject = message.get('subject', '')
        
        if not email_content:
            print("⚠️ Empty email content received")
            return
        
        print(f"\n🔍 Scanning email from browser: {subject[:50]}...")
        
        try:
            result = self.predictor.predict(email_content, sender)
            
            db_id = None
            try:
                db_id = db.save_email({
                    'email_text': email_content[:1000],
                    'source': 'browser_extension',
                    'predicted_label': 'PHISHING' if result.get('is_phishing', False) else 'LEGITIMATE',
                    'probability': result.get('total_confidence', 50) / 100,
                    'confidence': result.get('total_confidence', 50)
                })
                print(f"   ✅ Result: {result.get('classification', 'UNKNOWN')}")
                print(f"   📊 Confidence: {result.get('total_confidence', 0):.1f}%")
                
                for reason in result.get('reasons', [])[:3]:
                    print(f"   • {reason}")
                    
                # IMPORTANT: Send result to dashboard
                if self.callback:
                    print(f"   📤 Sending result to dashboard via callback")
                    self.callback({
                        'type': 'browser_scan_result',
                        'email_id': email_id,
                        'result': result,
                        'subject': subject,
                        'sender': sender,
                        'db_id': db_id,
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    })
                else:
                    print(f"   ⚠️ No callback registered - results won't appear in dashboard")
                    
            except Exception as e:
                print(f"❌ Database error: {e}")
            
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
    
    def stop(self):
        self.running = False
        if self.server:
            self.server.server_close()
        print("🛑 Browser integration stopped")

# Create singleton instance
browser_server = BrowserIntegrationServer()