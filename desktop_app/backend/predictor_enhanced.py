"""
Enhanced phishing predictor with multi-stage confidence scoring
"""
import numpy as np
import joblib
import os
import sys
import re
import json
from datetime import datetime
from urllib.parse import urlparse
from scipy.sparse import hstack, csr_matrix
import hashlib

# Optional imports with graceful fallbacks
try:
    import Levenshtein
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False

class EnhancedPhishingPredictor:
    def __init__(self, models_dir='data/models'):
        self.models_dir = models_dir
        self.model = None
        self.vectorizer = None
        self.scaler = None
        self.ml_weight = 0.3
        self.rule_weight = 0.7
        self.load_models()
        
        # Legitimate domains database
        self.legitimate_domains = self.load_legitimate_domains()
        
    def load_legitimate_domains(self):
        return {
            'paypal.com': {'brand': 'PayPal', 'trust_score': 100},
            'amazon.com': {'brand': 'Amazon', 'trust_score': 100},
            'netflix.com': {'brand': 'Netflix', 'trust_score': 100},
            'apple.com': {'brand': 'Apple', 'trust_score': 100},
            'microsoft.com': {'brand': 'Microsoft', 'trust_score': 100},
            'linkedin.com': {'brand': 'LinkedIn', 'trust_score': 100},
            'google.com': {'brand': 'Google', 'trust_score': 100},
            'github.com': {'brand': 'GitHub', 'trust_score': 100},
            'zoom.us': {'brand': 'Zoom', 'trust_score': 100},
            'slack.com': {'brand': 'Slack', 'trust_score': 100},
            'dropbox.com': {'brand': 'Dropbox', 'trust_score': 100},
            'twitter.com': {'brand': 'Twitter', 'trust_score': 100},
            'facebook.com': {'brand': 'Facebook', 'trust_score': 100},
            'instagram.com': {'brand': 'Instagram', 'trust_score': 100},
            'whatsapp.com': {'brand': 'WhatsApp', 'trust_score': 100}
        }
    
    def load_models(self):
        model_path = os.path.join(self.models_dir, 'logistic_regression_base.pkl')
        vec_path = os.path.join(self.models_dir, 'tfidf_vectorizer.pkl')
        
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        if os.path.exists(vec_path):
            self.vectorizer = joblib.load(vec_path)
    
    def extract_urls(self, text):
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)
    
    def calculate_similarity(self, str1, str2):
        if LEVENSHTEIN_AVAILABLE:
            return Levenshtein.distance(str1, str2)
        else:
            max_len = max(len(str1), len(str2))
            if max_len == 0:
                return 0
            matches = sum(1 for a, b in zip(str1, str2) if a == b)
            return max_len - matches
    
    def verify_link(self, url):
        parsed = urlparse(url if url.startswith('http') else f'http://{url}')
        domain = re.sub(r'^www\.', '', parsed.netloc or parsed.path.split('/')[0])
        
        for legit_domain, info in self.legitimate_domains.items():
            if domain == legit_domain:
                return {'is_suspicious': False, 'confidence': 100, 'brand': info['brand']}
            
            distance = self.calculate_similarity(domain, legit_domain)
            if distance <= 2 and distance > 0:
                return {
                    'is_suspicious': True,
                    'confidence': max(0, 100 - (distance * 30)),
                    'brand': info['brand'],
                    'reason': f'Typosquatting: {domain} vs {legit_domain}'
                }
        
        return {'is_suspicious': True, 'confidence': 70, 'reason': 'Unknown domain'}
    
    def check_sender(self, sender):
        match = re.search(r'@([^>\s]+)', sender)
        if not match:
            return {'is_suspicious': True, 'confidence': 50, 'reason': 'Invalid email format'}
        
        domain = match.group(1).lower()
        
        for legit_domain, info in self.legitimate_domains.items():
            if domain == legit_domain:
                return {'is_suspicious': False, 'confidence': 100, 'brand': info['brand']}
            
            distance = self.calculate_similarity(domain, legit_domain)
            if distance <= 2 and distance > 0:
                return {
                    'is_suspicious': True,
                    'confidence': max(0, 100 - (distance * 30)),
                    'brand': info['brand'],
                    'reason': f'Suspicious sender domain: {domain}'
                }
        
        return {'is_suspicious': True, 'confidence': 50, 'reason': f'Unrecognized domain: {domain}'}
    
    def calculate_rule_score(self, text):
        score = 0
        reasons = []
        
        urgent_words = ['urgent', 'immediately', 'asap', 'warning', 'alert', 'suspended']
        urgent_count = sum(1 for w in urgent_words if w in text.lower())
        if urgent_count > 0:
            score += min(15, urgent_count * 5)
            reasons.append(f"Contains {urgent_count} urgent word(s)")
        
        personal_info = ['password', 'credit card', 'ssn', 'social security', 'login', 'verify']
        if any(w in text.lower() for w in personal_info):
            score += 10
            reasons.append("Requests personal information")
        
        if text.count('!') > 3 or text.count('?') > 3:
            score += 5
            reasons.append("Excessive punctuation")
        
        words = text.split()
        caps_count = sum(1 for w in words if w.isupper() and len(w) > 2)
        if caps_count > 3:
            score += min(10, caps_count * 2)
            reasons.append(f"Excessive capitalization ({caps_count} words)")
        
        return min(40, score), reasons
    
    def predict(self, email_text, sender='unknown@example.com'):
        reasons = []
        stage_scores = {}
        
        # Stage 1: Rules (0-40)
        rule_score, rule_reasons = self.calculate_rule_score(email_text)
        stage_scores['rules'] = rule_score
        reasons.extend(rule_reasons)
        
        # Stage 2: Links (0-30)
        urls = self.extract_urls(email_text)
        link_score = 0
        suspicious_links = []
        
        if urls:
            for url in urls[:3]:
                result = self.verify_link(url)
                if result.get('is_suspicious'):
                    link_score += result['confidence'] / len(urls) * 0.3
                    suspicious_links.append({'url': url, 'reason': result.get('reason', 'Suspicious')})
            stage_scores['links'] = min(30, link_score)
            if suspicious_links:
                reasons.append(f"{len(suspicious_links)} suspicious link(s)")
        else:
            stage_scores['links'] = 0
        
        # Stage 3: Sender (0-30)
        sender_result = self.check_sender(sender)
        stage_scores['sender'] = (sender_result['confidence'] / 100) * 30 if sender_result['is_suspicious'] else 0
        if sender_result['is_suspicious']:
            reasons.append(sender_result.get('reason', 'Suspicious sender'))
        
        # Calculate total
        total_confidence = sum(stage_scores.values())
        
        # Classification
        if total_confidence >= 85:
            classification = '🔴 PHISHING (HIGH)'
            is_phishing = True
        elif total_confidence >= 70:
            classification = '🔴 PHISHING'
            is_phishing = True
        elif total_confidence >= 50:
            classification = '🟡 SUSPICIOUS'
            is_phishing = True
        else:
            classification = '🟢 LEGITIMATE'
            is_phishing = False
        
        return {
            'is_phishing': is_phishing,
            'classification': classification,
            'total_confidence': total_confidence,
            'stage_scores': stage_scores,
            'reasons': reasons[:5],
            'suspicious_links': suspicious_links,
            'has_links': len(urls) > 0
        }
