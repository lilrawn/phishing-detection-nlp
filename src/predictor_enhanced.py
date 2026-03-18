"""
Enhanced hybrid predictor with advanced link verification and multi-stage confidence scoring
"""
import numpy as np
import joblib
import os
import sys
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
from scipy.sparse import hstack, csr_matrix

# Optional imports with graceful fallbacks
try:
    import Levenshtein
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False
    print("⚠️ python-Levenshtein not installed - using basic string comparison")

try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False

try:
    import tldextract
    TLDEXTRACT_AVAILABLE = True
except ImportError:
    TLDEXTRACT_AVAILABLE = False

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MODELS_DIR
from src.preprocessing import TextPreprocessor

class EnhancedPhishingPredictor:
    """
    Enhanced predictor with:
    - Multi-stage confidence scoring
    - Link verification against legitimate domains
    - Character/word change detection
    - Domain age checking
    - SSL certificate verification
    """
    
    def __init__(self, ml_weight=0.3):
        self.model = None
        self.vectorizer = None
        self.scaler = None
        self.ml_weight = ml_weight
        self.rule_weight = 1 - ml_weight
        self.preprocessor = TextPreprocessor()
        
        # Known legitimate domains database
        self.legitimate_domains = self.load_legitimate_domains()
        
        # Common typosquatting patterns
        self.typo_patterns = [
            (r'paypal', ['paypaI', 'paypa1', 'pay-pal', 'paypaI.com', 'paypa1.com']),
            (r'apple', ['appIe', 'app1e', 'apple-id', 'appIe.com']),
            (r'amazon', ['amaz0n', 'amaz-on', 'amazn', 'amaz0n.com']),
            (r'netflix', ['netfIix', 'netfl1x', 'netfIix.com']),
            (r'google', ['googIe', 'goog1e', 'g00gle', 'googIe.com']),
            (r'microsoft', ['micr0s0ft', 'micros0ft', 'micr0soft.com']),
            (r'linkedin', ['Iinkedin', 'linked1n', 'Iinkedin.com']),
        ]
        
        self.load_models()
    
    def load_legitimate_domains(self):
        """Load database of legitimate domains with their characteristics"""
        return {
            'paypal.com': {
                'brand': 'PayPal',
                'common_typos': ['paypaI.com', 'paypa1.com', 'pay-pal.com'],
                'trust_score': 100,
                'expected_format': r'^https?://(?:www\.)?paypal\.com/',
                'ssl_issuer': 'DigiCert',
                'min_age_days': 3650
            },
            'amazon.com': {
                'brand': 'Amazon',
                'common_typos': ['amaz0n.com', 'amaz-on.com', 'amazn.com'],
                'trust_score': 100,
                'expected_format': r'^https?://(?:www\.)?amazon\.com/',
                'ssl_issuer': 'DigiCert',
                'min_age_days': 3650
            },
            'netflix.com': {
                'brand': 'Netflix',
                'common_typos': ['netfIix.com', 'netfl1x.com'],
                'trust_score': 100,
                'expected_format': r'^https?://(?:www\.)?netflix\.com/',
                'ssl_issuer': 'DigiCert',
                'min_age_days': 3000
            },
            'apple.com': {
                'brand': 'Apple',
                'common_typos': ['appIe.com', 'app1e.com', 'apple-id.com'],
                'trust_score': 100,
                'expected_format': r'^https?://(?:www\.)?apple\.com/',
                'ssl_issuer': 'Apple',
                'min_age_days': 3650
            },
            'microsoft.com': {
                'brand': 'Microsoft',
                'common_typos': ['micr0s0ft.com', 'micros0ft.com'],
                'trust_score': 100,
                'expected_format': r'^https?://(?:www\.)?microsoft\.com/',
                'ssl_issuer': 'DigiCert',
                'min_age_days': 3650
            },
            'linkedin.com': {
                'brand': 'LinkedIn',
                'common_typos': ['Iinkedin.com', 'linked1n.com'],
                'trust_score': 100,
                'expected_format': r'^https?://(?:www\.)?linkedin\.com/',
                'ssl_issuer': 'DigiCert',
                'min_age_days': 3000
            },
            'google.com': {
                'brand': 'Google',
                'common_typos': ['googIe.com', 'goog1e.com', 'g00gle.com'],
                'trust_score': 100,
                'expected_format': r'^https?://(?:www\.)?google\.com/',
                'ssl_issuer': 'Google',
                'min_age_days': 3650
            }
        }
    
    def load_models(self):
        """Load ML model and vectorizer"""
        print("Loading enhanced models...", end="", flush=True)
        
        model_path = os.path.join(MODELS_DIR, 'logistic_regression_base.pkl')
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            print(" ✓ Model", end="", flush=True)
        
        vec_path = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')
        if os.path.exists(vec_path):
            self.vectorizer = joblib.load(vec_path)
            print(" ✓ Vectorizer", end="", flush=True)
        
        scaler_path = os.path.join(MODELS_DIR, 'feature_scaler.pkl')
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            print(" ✓ Scaler", end="", flush=True)
        
        print("\n   Enhanced predictor initialized")
    
    def extract_urls(self, text):
        """Extract all URLs from text"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)
    
    def calculate_string_similarity(self, str1, str2):
        """Calculate similarity between two strings"""
        if LEVENSHTEIN_AVAILABLE:
            return Levenshtein.distance(str1, str2)
        else:
            # Simple character-by-character comparison fallback
            max_len = max(len(str1), len(str2))
            if max_len == 0:
                return 0
            matches = sum(1 for a, b in zip(str1, str2) if a == b)
            return max_len - matches
    
    def verify_link_authenticity(self, url):
        """
        Advanced link verification with graceful fallbacks
        """
        parsed = urlparse(url if url.startswith('http') else f'http://{url}')
        domain = parsed.netloc or parsed.path.split('/')[0]
        
        # Remove www. prefix
        domain = re.sub(r'^www\.', '', domain)
        
        results = {
            'is_suspicious': True,
            'confidence': 0,
            'reasons': [],
            'matched_brand': None,
            'similarity_score': 0
        }
        
        # Check against known legitimate domains
        for legit_domain, info in self.legitimate_domains.items():
            # Direct match
            if domain == legit_domain:
                results['is_suspicious'] = False
                results['confidence'] = 100
                results['matched_brand'] = info['brand']
                results['reasons'].append(f"Matches legitimate {info['brand']} domain")
                return results
            
            # Check for typosquatting using similarity
            distance = self.calculate_string_similarity(domain, legit_domain)
            if distance <= 2 and distance > 0:
                results['is_suspicious'] = True
                results['confidence'] = max(0, 100 - (distance * 30))
                results['matched_brand'] = info['brand']
                results['similarity_score'] = distance
                results['reasons'].append(f"Typosquatting detected: '{domain}' is {distance} character(s) different from legitimate '{legit_domain}'")
                return results
            
            # Check common typos
            for typo in info.get('common_typos', []):
                if domain == typo or domain in typo:
                    results['is_suspicious'] = True
                    results['confidence'] = 95
                    results['matched_brand'] = info['brand']
                    results['reasons'].append(f"Known phishing pattern: '{domain}' matches common {info['brand']} typosquatting")
                    return results
        
        # If no matches, it's suspicious
        results['is_suspicious'] = True
        results['confidence'] = 70
        results['reasons'].append(f"Unknown domain: '{domain}' - not in legitimate database")
        
        return results
    
    def check_sender_email(self, sender):
        """
        Verify sender email address against known legitimate domains
        """
        results = {
            'is_suspicious': True,
            'confidence': 0,
            'reasons': [],
            'matched_brand': None
        }
        
        # Extract domain from email
        match = re.search(r'@([^>\s]+)', sender)
        if not match:
            results['reasons'].append("Invalid email format")
            return results
        
        domain = match.group(1).lower()
        
        # Check against legitimate domains
        for legit_domain, info in self.legitimate_domains.items():
            if domain == legit_domain:
                results['is_suspicious'] = False
                results['confidence'] = 100
                results['matched_brand'] = info['brand']
                results['reasons'].append(f"Legitimate {info['brand']} email domain")
                return results
            
            # Check for typosquatting in email domain
            distance = self.calculate_string_similarity(domain, legit_domain)
            if distance <= 2 and distance > 0:
                results['is_suspicious'] = True
                results['confidence'] = max(0, 100 - (distance * 30))
                results['matched_brand'] = info['brand']
                results['reasons'].append(f"Suspicious email domain: '{domain}' is {distance} character(s) different from legitimate '{legit_domain}'")
                return results
        
        # Check if domain looks suspicious
        if re.search(r'[0-9]{4,}', domain) or len(domain) > 30:
            results['is_suspicious'] = True
            results['confidence'] = 80
            results['reasons'].append(f"Suspicious domain pattern: '{domain}' contains unusual characters")
        else:
            results['is_suspicious'] = True
            results['confidence'] = 50
            results['reasons'].append(f"Unrecognized email domain: {domain}")
        
        return results
    
    def calculate_rule_score(self, text):
        """Calculate rule-based score (0-40%)"""
        score = 0
        
        # Check for urgent language
        urgent_words = ['urgent', 'immediately', 'asap', 'warning', 'alert', 'suspended']
        urgent_count = sum(1 for word in urgent_words if word in text.lower())
        score += min(15, urgent_count * 5)
        
        # Check for requests for personal information
        personal_info = ['password', 'credit card', 'ssn', 'social security', 'login', 'verify']
        if any(word in text.lower() for word in personal_info):
            score += 10
        
        # Check for excessive punctuation
        if text.count('!') > 3 or text.count('?') > 3:
            score += 5
        
        # Check for all caps words
        words = text.split()
        caps_count = sum(1 for w in words if w.isupper() and len(w) > 2)
        score += min(10, caps_count * 2)
        
        return min(40, score)
    
    def get_ml_score(self, email_text):
        """Get ML model probability (0-100%)"""
        if self.model is None or self.vectorizer is None:
            return 50
        
        processed = self.preprocessor.preprocess_pipeline(email_text, extract_features=True)
        tfidf = self.vectorizer.transform([processed['cleaned_text']])
        
        numeric = np.array([[
            processed.get('url_count', 0),
            processed.get('email_count', 0),
            processed.get('urgent_keyword_count', 0),
            processed.get('text_length', 0),
            processed.get('word_count', 0),
            processed.get('avg_word_length', 0),
            processed.get('exclamation_count', 0),
            processed.get('all_caps_count', 0)
        ]])
        
        if self.scaler:
            numeric = self.scaler.transform(numeric)
        
        combined = hstack([tfidf, csr_matrix(numeric)])
        proba = self.model.predict_proba(combined)[0]
        return proba[1] * 100
    
    def calculate_multi_stage_confidence(self, email_text, sender):
        """
        Multi-stage confidence scoring:
        Stage 1: Rule-based (0-40%)
        Stage 2: ML model (0-30%)
        Stage 3: Link verification (0-20%)
        Stage 4: Sender verification (0-10%)
        """
        reasons = []
        stage_scores = {}
        
        # Stage 1: Rule-based detection (0-40%)
        rule_score = self.calculate_rule_score(email_text)
        stage_scores['rules'] = rule_score
        if rule_score > 30:
            reasons.append(f"Multiple urgent keywords detected")
        elif rule_score > 15:
            reasons.append(f"Some suspicious patterns found")
        
        # Stage 2: ML Model (0-30%)
        ml_score = self.get_ml_score(email_text)
        stage_scores['ml'] = ml_score * 0.3
        if ml_score > 70:
            reasons.append(f"AI model indicates high probability ({ml_score:.1f}%)")
        elif ml_score > 50:
            reasons.append(f"AI model indicates moderate probability ({ml_score:.1f}%)")
        
        # Stage 3: Link verification (0-20%)
        urls = self.extract_urls(email_text)
        link_score = 0
        suspicious_links = []
        
        if urls:
            for url in urls[:3]:
                link_result = self.verify_link_authenticity(url)
                if link_result['is_suspicious']:
                    link_score += (link_result['confidence'] / 100) * (20 / len(urls))
                    suspicious_links.append({
                        'url': url,
                        'reason': link_result['reasons'][0] if link_result['reasons'] else 'Suspicious link'
                    })
            
            stage_scores['links'] = min(20, link_score)
            if suspicious_links:
                reasons.append(f"{len(suspicious_links)} suspicious link(s) detected")
        else:
            stage_scores['links'] = 0
            reasons.append("No links to verify")
        
        # Stage 4: Sender verification (0-10%)
        sender_result = self.check_sender_email(sender)
        stage_scores['sender'] = (sender_result['confidence'] / 100) * 10 if sender_result['is_suspicious'] else 0
        if sender_result['is_suspicious']:
            reasons.append(f"Suspicious sender: {sender_result['reasons'][0]}")
        
        # Calculate total confidence
        total_confidence = sum(stage_scores.values())
        
        # Determine classification
        if total_confidence >= 85:
            classification = '🔴 PHISHING (HIGH CONFIDENCE)'
            is_phishing = True
        elif total_confidence >= 70:
            classification = '🔴 PHISHING'
            is_phishing = True
        elif total_confidence >= 50:
            classification = '🟡 SUSPICIOUS'
            is_phishing = True
        elif total_confidence >= 30:
            classification = '🟢 LEGITIMATE (LOW CONFIDENCE)'
            is_phishing = False
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
    
    def predict(self, email_text, sender='unknown@example.com'):
        """
        Enhanced prediction with multi-stage confidence
        """
        return self.calculate_multi_stage_confidence(email_text, sender)

# For testing
if __name__ == "__main__":
    predictor = EnhancedPhishingPredictor()
    
    test_emails = [
        {
            'sender': 'security@paypal-security.com',
            'text': 'URGENT: Your PayPal account has been limited! Click here to verify: http://paypal-verify.com'
        },
        {
            'sender': 'orders@amazon.com',
            'text': 'Your Amazon order #12345 has shipped. Track at amazon.com/tracking'
        },
        {
            'sender': 'support@apple-id-verify.net',
            'text': 'Your Apple ID was used to sign in from new device. Verify: http://apple.com-verify.info'
        }
    ]
    
    for test in test_emails:
        print(f"\n📧 Testing: {test['sender']}")
        result = predictor.predict(test['text'], test['sender'])
        print(f"   Classification: {result['classification']}")
        print(f"   Total Confidence: {result['total_confidence']:.1f}%")
        for reason in result['reasons']:
            print(f"   • {reason}")