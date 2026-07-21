"""
Gmail watcher - Monitors Gmail for new emails
"""
import time
import threading
import random
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.predictor import PhishingPredictor
from src.database import db

class GmailWatcher(threading.Thread):
    """Background thread that monitors Gmail"""
    
    def __init__(self, permission_manager, callback=None):
        super().__init__()
        self.permission_manager = permission_manager
        self.callback = callback
        self.running = False
        self.daemon = True
        ml_weight = self.permission_manager.permissions['settings'].get('ml_weight', 0.7)
        self.predictor = PhishingPredictor(ml_weight=ml_weight)
        self.email_counter = 1000
        self.paused = False
        
        self.email_database = {
            'phishing': [
                {
                    'from': 'security@paypal-security.com',
                    'subject': 'URGENT: Your PayPal account has been limited',
                    'body': 'Dear Customer,\n\nWe have detected unusual activity on your account. Click here to verify: http://paypal-verify.com/secure\n\nFailure to verify will result in account suspension.\n\nPayPal Security Team'
                },
                {
                    'from': 'support@apple-id-verify.net',
                    'subject': 'Apple ID Verification Required',
                    'body': 'Your Apple ID was used to sign in from a new device. Verify now: http://apple.com-verify.info\n\nApple Support'
                }
            ],
            'legitimate': [
                {
                    'from': 'orders@amazon.com',
                    'subject': 'Your Amazon order has shipped',
                    'body': 'Hello,\n\nYour Amazon order #123-4567890 has shipped and will arrive Monday.\n\nTrack your package at amazon.com/tracking\n\nThank you for shopping with Amazon!'
                },
                {
                    'from': 'info@netflix.com',
                    'subject': 'Netflix: Your monthly statement',
                    'body': 'Your Netflix statement is now available.\n\nView billing at netflix.com/account'
                },
                {
                    'from': 'meeting@company.com',
                    'subject': 'Team meeting tomorrow',
                    'body': 'Hi team,\n\nMeeting at 10am in Conference Room B.\n\nThanks'
                }
            ]
        }
    
    def run(self):
        self.running = True
        print("🚀 Enhanced Gmail watcher started")
        
        while self.running:
            try:
                if not self.paused:
                    self.simulate_check_emails()
                time.sleep(self.permission_manager.permissions['settings']['check_interval'])
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)
    
    def simulate_check_emails(self):
        if random.random() < 0.7:
            email_type = 'phishing' if random.random() < 0.3 else 'legitimate'
            email_data = random.choice(self.email_database[email_type]).copy()
            
            self.email_counter += 1
            email_data['id'] = self.email_counter
            email_data['timestamp'] = datetime.now()
            
            self.process_email(email_data, email_type)
    
    def process_email(self, email_data, email_type):
        full_text = f"{email_data['subject']}\n\n{email_data['body']}"
        
        # Run prediction
        result = self.predictor.predict(full_text, email_data['from'])
        
        try:
            email_id = db.save_email({
                'email_text': full_text,
                'source': 'gmail_simulation',
                'predicted_label': 'PHISHING' if result.get('is_phishing', False) else 'LEGITIMATE',
                'probability': result.get('probability', 0),
                'confidence': result.get('confidence', 0)
            })

            display_id = email_id if email_id else self.email_counter
            print(f"\n📧 New email (ID: {display_id})")
            print(f"   From: {email_data['from']}")
            print(f"   Subject: {email_data['subject']}")
            print(f"   Result: {result.get('classification', 'UNKNOWN')}")
            print(f"   Confidence: {result.get('confidence', 0):.1f}%")
            
            # Send to dashboard
            if self.callback:
                self.callback({
                    'type': 'phishing_detected' if result.get('is_phishing', False) else 'legitimate_detected',
                    'email': email_data,
                    'result': result,
                    'email_id': display_id,
                    'source': 'sample'
                })
            
        except Exception as e:
            print(f"❌ Error saving to database: {e}")
            display_id = self.email_counter
    
    def stop(self):
        self.running = False
        print("🛑 Gmail watcher stopped")