"""
Central monitoring system that coordinates all watchers
"""
import threading
import time
import queue
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import db
from src.predictor import PhishingPredictor
from .gmail_watcher import GmailWatcher
from .browser_watcher import BrowserWatcher
from .permission_manager import PermissionManager

class EmailMonitor:
    """
    Central monitoring system that coordinates all email monitoring activities
    """
    
    def __init__(self, callback=None):
        self.callback = callback
        self.permission_manager = PermissionManager()
        ml_weight = self.permission_manager.permissions['settings'].get('ml_weight', 0.7)
        self.predictor = PhishingPredictor(ml_weight=ml_weight)
        self.gmail_watcher = None
        self.browser_watcher = None
        self.running = False
        self.alert_queue = queue.Queue()
        self.stats = {
            'total_scanned': 0,
            'phishing_found': 0,
            'safe_found': 0,
            'last_scan': None
        }
        
    def start(self):
        """Start all monitoring services"""
        print("🚀 Starting Email Monitor...")
        self.running = True
        
        # Start Gmail watcher if permitted
        if self.permission_manager.check_permission('gmail_access'):
            self.gmail_watcher = GmailWatcher(
                self.permission_manager, 
                self.on_phishing_detected
            )
            self.gmail_watcher.start()
            print("✅ Gmail watcher started")
        
        # Start browser watcher if permitted
        if self.permission_manager.check_permission('browser_monitoring'):
            self.browser_watcher = BrowserWatcher(
                self.permission_manager,
                self.on_browser_event
            )
            self.browser_watcher.start()
            print("✅ Browser watcher started")
        
        # Start alert processor
        self.alert_processor = threading.Thread(target=self.process_alerts)
        self.alert_processor.daemon = True
        self.alert_processor.start()
        
        # Start stats updater
        self.stats_updater = threading.Thread(target=self.update_stats)
        self.stats_updater.daemon = True
        self.stats_updater.start()
    
    def stop(self):
        """Stop all monitoring services"""
        print("🛑 Stopping Email Monitor...")
        self.running = False
        
        if self.gmail_watcher:
            self.gmail_watcher.stop()
        
        if self.browser_watcher:
            self.browser_watcher.stop()
    
    def on_phishing_detected(self, data):
        """Handle phishing detection from Gmail watcher"""
        self.alert_queue.put({
            'type': 'phishing',
            'data': data,
            'timestamp': datetime.now()
        })
        
        # Update stats
        result = data.get('result', {})

        if result.get('is_phishing', False):
            self.stats['phishing_found'] += 1
        else:
            self.stats['safe_found'] += 1
        
        self.stats['total_scanned'] += 1
        self.stats['last_scan'] = datetime.now()
        
        # Save to database
        self.save_to_database(data)
        
        # Trigger callback
        if self.callback:
            self.callback(data)
    
    def on_browser_event(self, data):
        """Handle browser events"""
        if data['type'] == 'gmail_page_detected':
            print(f"🌐 Gmail page detected: {data['url']}")
    
    def process_alerts(self):
        """Process alerts from the queue"""
        while self.running:
            try:
                alert = self.alert_queue.get(timeout=1)
                self.show_alert(alert)
            except queue.Empty:
                continue
    
    def show_alert(self, alert):
        """Show alert to user"""
        if alert['type'] == 'phishing':
            data = alert['data']
            result = data.get('result', {})
            confidence = result.get('confidence', 0)
            classification = result.get('classification', 'UNKNOWN')
            reasons = result.get('reasons', [])

            print(f"""
⚠️ PHISHING ALERT!
   From: {data['email']['from']}
   Subject: {data['email']['subject']}
   Classification: {classification}
   Confidence: {confidence:.1f}%
   Reasons: {', '.join(reasons[:3]) if reasons else 'No specific reasons'}
            """)
    
    def save_to_database(self, data):
        """Save detection to database"""
        try:
            result = data.get('result', {})
            is_phishing = result.get('is_phishing', False)

            email_id = db.save_email({
                'email_text': f"{data['email']['subject']}\n{data['email']['body']}",
                'source': 'gmail_monitor',
                'predicted_label': 'PHISHING' if is_phishing else 'LEGITIMATE',
                'probability': result.get('probability', 0),
                'confidence': result.get('confidence', 0),
                'url_count': data['email']['body'].count('http'),
                'urgent_count': len([r for r in result.get('reasons', []) if 'urgent' in r])
            })
            print(f"✅ Saved to database (ID: {email_id})")
        except Exception as e:
            print(f"❌ Failed to save to database: {e}")
    
    def update_stats(self):
        """Update statistics periodically"""
        while self.running:
            try:
                db_stats = db.get_statistics()
                self.stats.update({
                    'db_total': db_stats['total_emails'],
                    'db_phishing': db_stats['phishing'],
                    'db_legitimate': db_stats['legitimate']
                })
                time.sleep(10)
            except Exception as e:
                print(f"Stats update error: {e}")
                time.sleep(30)
    
    def manual_scan_email(self, email_text):
        """Manually scan an email"""
        result = self.predictor.predict(email_text)

        self.stats['total_scanned'] += 1
        if result.get('is_phishing', False):
            self.stats['phishing_found'] += 1
        else:
            self.stats['safe_found'] += 1
        
        return result
    
    def get_status(self):
        """Get current monitoring status"""
        return {
            'gmail': self.gmail_watcher is not None and self.gmail_watcher.running,
            'browser': self.browser_watcher is not None and self.browser_watcher.running,
            'stats': self.stats,
            'permissions': self.permission_manager.permissions
        }