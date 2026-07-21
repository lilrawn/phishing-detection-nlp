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

from src.predictor import PhishingPredictor
from src.database import db
from .permission_manager import PermissionManager

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

        permission_manager = PermissionManager()
        ml_weight = permission_manager.permissions['settings'].get('ml_weight', 0.7)
        self.predictor = PhishingPredictor(ml_weight=ml_weight)

        self.active_sessions = {}
        print(f"🔧 BrowserIntegrationServer initialized")
        
    def start(self):
        self.running = True
        self.http_thread = threading.Thread(target=self.start_http_server)
        self.http_thread.daemon = True
        self.http_thread.start()
        print(f"🌐 Browser integration server started on port {self.http_port}")
        print(f"   Test connection: curl http://localhost:{self.http_port}/api/health")
    
    def start_http_server(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def _send_cors_headers(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With')
                self.send_header('Access-Control-Max-Age', '86400')
            
            def do_OPTIONS(self):
                self.send_response(200)
                self._send_cors_headers()
                self.end_headers()
            
            def do_POST(self):
                if self.path == '/api/notification':
                    try:
                        content_length = int(self.headers.get('Content-Length', 0))
                        if content_length > 0:
                            post_data = self.rfile.read(content_length)
                            message = json.loads(post_data.decode())

                            response_data = {'status': 'ok'}
                            if hasattr(self.server, 'integration_server'):
                                result = self.server.integration_server.handle_message(message)
                                if result is not None:
                                    response_data['result'] = result

                            self.send_response(200)
                            self._send_cors_headers()
                            self.end_headers()
                            self.wfile.write(json.dumps(response_data).encode())
                        else:
                            self.send_response(400)
                            self._send_cors_headers()
                            self.end_headers()
                            self.wfile.write(b'{"error":"No content"}')
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
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
                    if self.path == '/api/health':
                        response = {
                            'status': 'running',
                            'service': 'phishing-detector',
                            'timestamp': time.time(),
                            'connected_extensions': len(self.server.integration_server.connected_extensions)
                        }
                        self.send_response(200)
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode())
                    elif self.path == '/api/status':
                        response = {
                            'connected': len(self.server.integration_server.connected_extensions) > 0,
                            'extensions': list(self.server.integration_server.connected_extensions.keys()),
                            'history': self.server.integration_server.connection_history[-5:]
                        }
                        self.send_response(200)
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode())
                    else:
                        self.send_response(200)
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(b'{"status":"running","service":"phishing-detector"}')
                except BrokenPipeError:
                    pass
                except Exception as e:
                    print(f"Error in GET request: {e}")
                    try:
                        self.send_response(500)
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(f'{{"error":"{str(e)}"}}'.encode())
                    except:
                        pass
            
            def log_message(self, format, *args):
                pass

        class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            # Plain TCPServer.handle_request() processes one request at a
            # time -- a scan_email request (which blocks on ML inference)
            # would stall every other connection_status/gmail_opened
            # heartbeat behind it, causing the client-side fetch() calls to
            # time out and the browser extension to retry, piling up
            # connections. ThreadingMixIn handles each request on its own
            # thread instead. db.py opens a fresh sqlite3 connection per
            # call, so it's safe to hit concurrently from multiple threads.
            daemon_threads = True

        try:
            self.server = ThreadedTCPServer(("localhost", self.http_port), Handler)
            self.server.timeout = 1
            self.server.integration_server = self
            
            print(f"   Listening for browser extension connections on port {self.http_port}...")
            
            while self.running:
                try:
                    self.server.handle_request()
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    if "timed out" not in str(e) and "Errno 32" not in str(e):
                        print(f"⚠️ Server error: {e}")
                    continue
                    
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"⚠️ Port {self.http_port} already in use")
                print(f"   Try: lsof -i :{self.http_port} | grep LISTEN")
                print(f"   Then kill the process or use a different port")
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
            return self.handle_scan_email(message)
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

        # Identity must be stable across repeated heartbeats from the same
        # browser/extension, so it can't include a live timestamp -- doing
        # so (as this used to) makes every single heartbeat hash to a
        # different id, so dedup never triggers and connected_extensions
        # grows without bound.
        unique_string = f"{browser}_{extension_version}"
        extension_id = hashlib.md5(unique_string.encode()).hexdigest()[:16]

        current_time = time.time()
        self.processed_connections = {
            k: v for k, v in self.processed_connections.items()
            if current_time - v < 3600
        }

        if status == 'connected':
            is_new_or_stale = (
                extension_id not in self.processed_connections or
                current_time - self.processed_connections[extension_id] >= 300
            )

            self.connected_extensions[extension_id] = {
                'connected_at': timestamp,
                'last_seen': current_time,
                'version': extension_version,
                'browser': browser
            }
            self.processed_connections[extension_id] = current_time

            if not is_new_or_stale:
                return

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
                    'probability': result.get('probability', 0),
                    'confidence': result.get('confidence', 0)
                })
            except Exception as e:
                print(f"❌ Database error: {e}")

            print(f"   ✅ Result: {result.get('classification', 'UNKNOWN')}")
            print(f"   📊 Confidence: {result.get('confidence', 0):.1f}%")

            for reason in result.get('reasons', [])[:3]:
                print(f"   • {reason}")

            # Send result to dashboard. Kept out of the db try/except above
            # so a dashboard-side error doesn't get swallowed and mislabeled
            # as a database error -- this call runs GUI code (Tkinter isn't
            # thread-safe), so any bug here needs to surface clearly.
            if self.callback:
                print(f"   📤 Sending result to dashboard")
                try:
                    self.callback({
                        'type': 'browser_scan_result',
                        'email_id': email_id,
                        'result': result,
                        'subject': subject,
                        'sender': sender,
                        'email_content': email_content,
                        'db_id': db_id,
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    })
                except Exception as e:
                    print(f"❌ Dashboard callback error: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"   ⚠️ No callback registered - results won't appear in dashboard")

            return result

        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def stop(self):
        self.running = False
        if self.server:
            self.server.server_close()
        print("🛑 Browser integration stopped")

# Create singleton instance
browser_server = BrowserIntegrationServer()