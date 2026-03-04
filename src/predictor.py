"""
Clean prediction interface for phishing detection
"""
import numpy as np
import joblib
import os
import sys
from scipy.sparse import hstack, csr_matrix
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MODELS_DIR
from src.preprocessing import TextPreprocessor
from src.feature_extraction import FeatureExtractor
from src.database import db

class PhishingPredictor:
    """Make predictions on emails"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.scaler = None
        self.base_threshold = 0.70
        self.text_preprocessor = TextPreprocessor()
        self.feature_extractor = FeatureExtractor()
        self.load_models()
        
    def load_models(self):
        """Load all required models"""
        print("Loading models...", end="", flush=True)
        
        model_path = os.path.join(MODELS_DIR, 'logistic_regression_base.pkl')
        if not os.path.exists(model_path):
            model_path = os.path.join(MODELS_DIR, 'logistic_regression_balanced.pkl')
        if not os.path.exists(model_path):
            model_path = os.path.join(MODELS_DIR, 'best_model.pkl')
            
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            print(f" ✓ Model", end="", flush=True)
        
        vec_path = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')
        if os.path.exists(vec_path):
            self.vectorizer = joblib.load(vec_path)
            print(f" ✓ Vectorizer", end="", flush=True)
        
        scaler_path = os.path.join(MODELS_DIR, 'feature_scaler.pkl')
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            print(f" ✓ Scaler", end="", flush=True)
        
        print(f" ✓ Threshold: {self.base_threshold:.3f}", end="", flush=True)
        print()
        
    def predict(self, email_text):
        """Predict if email is phishing and save to database"""
        if self.model is None:
            return {"error": "No model loaded"}
        
        # Preprocess
        processed = self.text_preprocessor.preprocess_pipeline(email_text, extract_features=True)
        
        # Get features
        if self.vectorizer:
            tfidf = self.vectorizer.transform([processed['cleaned_text']])
        else:
            tfidf = self.feature_extractor.transform_tfidf([processed['cleaned_text']])
        
        # Get numeric features
        url_count = processed.get('url_count', 0)
        urgent_count = processed.get('urgent_keyword_count', 0)
        exclaim_count = processed.get('exclamation_count', 0)
        caps_count = processed.get('all_caps_count', 0)
        
        numeric_features = np.array([[
            url_count,
            processed.get('email_count', 0),
            urgent_count,
            processed.get('text_length', 0),
            processed.get('word_count', 0),
            processed.get('avg_word_length', 0),
            exclaim_count,
            caps_count
        ]])
        
        if self.scaler:
            numeric_features = self.scaler.transform(numeric_features)
        
        # Combine
        combined = hstack([tfidf, csr_matrix(numeric_features)])
        
        # Get probability
        proba = self.model.predict_proba(combined)[0]
        prob = proba[1]
        
        # Adaptive threshold based on indicators
        phishing_indicators = 0
        if url_count > 0:
            phishing_indicators += 1
        if urgent_count > 2:
            phishing_indicators += 1
        if exclaim_count > 2:
            phishing_indicators += 1
        if caps_count > 3:
            phishing_indicators += 1
        
        adaptive_threshold = self.base_threshold - (phishing_indicators * 0.05)
        adaptive_threshold = max(0.5, min(0.8, adaptive_threshold))
        
        is_phishing = prob > adaptive_threshold
        label = 'PHISHING' if is_phishing else 'LEGITIMATE'
        
        # Calculate confidence
        if is_phishing:
            confidence = min(100, ((prob - adaptive_threshold) / (1 - adaptive_threshold)) * 100)
        else:
            confidence = min(100, ((adaptive_threshold - prob) / adaptive_threshold) * 100)
        
        # Prepare result
        result = {
            'is_phishing': is_phishing,
            'label': f'⚠️ {label}' if is_phishing else f'✅ {label}',
            'probability': prob,
            'confidence': confidence,
            'threshold': adaptive_threshold,
            'base_threshold': self.base_threshold,
            'phishing_indicators': phishing_indicators,
            'features': {
                'urls': url_count,
                'urgent_words': urgent_count,
                'exclamations': exclaim_count,
                'all_caps': caps_count
            },
            'email_text': email_text,
            'cleaned_text': processed['cleaned_text'],
            'predicted_label': label
        }
        
        # Save to database
        email_id = db.save_email({
            'email_text': email_text,
            'cleaned_text': processed['cleaned_text'],
            'source': 'user_input',
            'predicted_label': label,
            'probability': prob,
            'confidence': confidence,
            'threshold': adaptive_threshold,
            'url_count': url_count,
            'urgent_count': urgent_count,
            'exclaim_count': exclaim_count,
            'caps_count': caps_count
        })
        
        result['email_id'] = email_id
        
        return result

def run_interactive():
    """Run interactive prediction mode"""
    print("\n" + "="*60)
    print("🤖 PHISHING EMAIL DETECTOR")
    print("   Natural Language Processing + Machine Learning")
    print("="*60)
    
    predictor = PhishingPredictor()
    
    if predictor.model is None:
        print("\n❌ No trained model found!")
        return
    
    # Show database stats
    stats = db.get_statistics()
    print(f"\n📊 Database: {stats['total_emails']} emails stored")
    print(f"   Phishing: {stats['phishing']} | Legitimate: {stats['legitimate']}")
    
    print(f"\n✅ System Ready!")
    print(f"   Model: Logistic Regression")
    print(f"   Base threshold: {predictor.base_threshold*100:.1f}%")
    
    print("\n📝 Commands:")
    print("   • Type an email to analyze")
    print("   • 'test' - run test cases")
    print("   • 'stats' - show database stats")
    print("   • 'export' - export data for retraining")
    print("   • 'exit' - quit")
    print("-"*50)
    
    test_cases = [
        ("URGENT: Your account has been limited! Click here: http://fake.com", "phishing"),
        ("Hi team, meeting at 3pm today. Please bring updates.", "legitimate"),
        ("Your Amazon order #12345 has been shipped.", "legitimate"),
        ("FINAL NOTICE: Your account will be closed. Update now!", "phishing"),
    ]
    
    while True:
        print()
        text = input("📨 Enter email: ").strip()
        
        if text.lower() == 'exit':
            print("\n👋 Goodbye!")
            break
            
        elif text.lower() == 'stats':
            stats = db.get_statistics()
            print(f"\n📊 Database Statistics:")
            print(f"   Total emails: {stats['total_emails']}")
            print(f"   Phishing: {stats['phishing']}")
            print(f"   Legitimate: {stats['legitimate']}")
            print(f"   Avg confidence: {stats['avg_confidence']:.1f}%")
            print(f"\n   By source:")
            for source in stats['by_source']:
                print(f"     • {source['source']}: {source['count']}")
            
        elif text.lower() == 'export':
            df = db.export_for_training()
            filename = f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"\n✅ Exported {len(df)} emails to {filename}")
            
        elif text.lower() == 'test':
            print("\n📋 Running tests:")
            for i, (email, expected) in enumerate(test_cases, 1):
                result = predictor.predict(email)
                is_correct = (result['is_phishing'] and expected == 'phishing') or \
                            (not result['is_phishing'] and expected == 'legitimate')
                
                print(f"\nTest {i}:")
                print(f"  Email: {email[:60]}...")
                print(f"  Expected: {expected}")
                print(f"  Result: {result['label']}")
                print(f"  Probability: {result['probability']*100:.1f}%")
                print(f"  Confidence: {result['confidence']:.1f}%")
                print(f"  {'✅' if is_correct else '❌'}")
            
        elif text:
            result = predictor.predict(text)
            print(f"\n🎯 Result: {result['label']}")
            print(f"   Probability: {result['probability']*100:.1f}%")
            print(f"   Confidence: {result['confidence']:.1f}%")
            print(f"   (Saved to database ID: {result['email_id']})")
            
        else:
            print("❌ Please enter some text")

if __name__ == "__main__":
    run_interactive()