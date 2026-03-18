"""
Gmail watcher with enhanced phishing detection
"""
import time
import threading
import random
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.predictor_enhanced import EnhancedPhishingPredictor
from src.database import db

class GmailWatcher(threading.Thread):
    def __init__(self, permission_manager, callback=None):
        super().__init__()
        self.permission_manager = permission_manager
        self.callback = callback
        self.running = False
        self.daemon = True
        self.predictor = EnhancedPhishingPredictor()
        self.email_counter = 1000
        
        self.email_database = {
            'phishing': [
                {
                    'from': 'security@paypal-security.com',
                    'subject': 'URGENT: Your PayPal account has been limited',
                    'body': 'Click here to verify: http://paypal-verify.com/secure'
                },
                {
                    'from': 'support@apple-id-verify.net',
                    'subject': 'Apple ID Verification Required',
                    'body': 'Verify now: http://apple.com-verify.info'
                }
            ],
            'legitimate': [
                {
                    'from': 'orders@amazon.com',
                    'subject': 'Your Amazon order has shipped',
                    'body': 'Track at amazon.com/tracking'
                },
                {
                    'from': 'info@netflix.com',
                    'subject': 'Netflix: Your monthly statement',
                    'body': 'View at netflix.com/account'
                },
                {
                    'from': 'meeting@company.com',
                    'subject': 'Team meeting tomorrow',
                    'body': 'Meeting at 10am in Conference Room B'
                }
            ]
        }
    
    def run(self):
        self.running = True
        print("🚀 Enhanced Gmail watcher started")
        
        while self.running:
            try:
                if self.permission_manager.check_permission('gmail_access'):
                    self.simulate_check_emails()
                time.sleep(self.permission_manager.permissions['settings']['check_interval'])
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)
    
    def simulate_check_emails(self):
        if random.random() < 0.5:
            email_type = 'phishing' if random.random() < 0.3 else 'legitimate'
            email_data = random.choice(self.email_database[email_type]).copy()
            
            self.email_counter += 1
            email_data['id'] = self.email_counter
            email_data['timestamp'] = datetime.now()
            
            self.process_email(email_data, email_type)
    
    def process_email(self, email_data, email_type):
        full_text = f"{email_data['subject']}\n\n{email_data['body']}"
        
        # Use enhanced predictor with sender email
        result = self.predictor.predict(full_text, email_data['from'])
        
        try:
            email_id = db.save_email({
                'email_text': full_text,
                'source': 'gmail_simulation',
                'predicted_label': 'PHISHING' if result['is_phishing'] else 'LEGITIMATE',
                'probability': result['total_confidence'] / 100,
                'confidence': result['total_confidence'],
                'url_count': full_text.count('http'),
                'urgent_count': len([r for r in result.get('reasons', []) if 'urgent' in r])
            })
            
            display_id = email_id if email_id else self.email_counter
            print(f"\n📧 New email (ID: {display_id})")
            print(f"   From: {email_data['from']}")
            print(f"   Subject: {email_data['subject']}")
            print(f"   Enhanced Analysis: {result['classification']}")
            print(f"   Confidence: {result['total_confidence']:.1f}%")
            print(f"   Stage Scores: Rules={result['stage_scores'].get('rules', 0):.1f}%, "
                  f"ML={result['stage_scores'].get('ml', 0):.1f}%, "
                  f"Links={result['stage_scores'].get('links', 0):.1f}%, "
                  f"Sender={result['stage_scores'].get('sender', 0):.1f}%")
            
            for reason in result['reasons']:
                print(f"   • {reason}")
            
            if result.get('suspicious_links'):
                for link in result['suspicious_links']:
                    print(f"   ⚠️ Suspicious link: {link['url']}")
                    print(f"     Reason: {link['reason']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            display_id = self.email_counter
        
        if self.callback:
            self.callback({
                'type': 'phishing_detected' if result['is_phishing'] else 'legitimate_detected',
                'email': email_data,
                'result': result,
                'email_id': display_id
            })
    
    def stop(self):
        self.running = False
        print("🛑 Gmail watcher stopped")