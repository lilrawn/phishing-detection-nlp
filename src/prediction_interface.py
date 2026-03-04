"""
Final prediction interface with calibrated model
"""
import numpy as np
import joblib
import os
import sys

# Suppress all NLTK messages
import nltk
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Completely silence NLTK
nltk.download = lambda *args, **kwargs: None

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODELS_DIR
from src.preprocessing import TextPreprocessor
from src.feature_extraction import FeatureExtractor

class PhishingPredictor:
    """
    Class to make predictions on new emails
    """
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.scaler = None
        self.threshold = 0.50  # Default
        self.calibration_info = None
        self.text_preprocessor = TextPreprocessor()
        self.feature_extractor = FeatureExtractor()
        self.load_artifacts()
        
    def load_artifacts(self):
        """Load trained model and vectorizer"""
        # Try loading calibrated model first
        model_paths = [
            os.path.join(MODELS_DIR, 'logistic_regression_calibrated.pkl'),
            os.path.join(MODELS_DIR, 'logistic_regression_balanced.pkl'),
            os.path.join(MODELS_DIR, 'best_model.pkl')
        ]
        
        for model_path in model_paths:
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                print(f"✅ Model loaded: {os.path.basename(model_path)}")
                break
        
        if self.model is None:
            print("⚠️  No model found. Run train_calibrated_final.py first")
            return
        
        # Load calibration info
        cal_path = os.path.join(MODELS_DIR, 'calibration_info.pkl')
        if os.path.exists(cal_path):
            self.calibration_info = joblib.load(cal_path)
            self.threshold = self.calibration_info.get('optimal_threshold', 0.50)
            print(f"✅ Threshold: {self.threshold:.3f}")
        
        # Load vectorizer
        vec_path = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')
        if os.path.exists(vec_path):
            self.vectorizer = joblib.load(vec_path)
            self.feature_extractor.tfidf_vectorizer = self.vectorizer
            print(f"✅ Vectorizer loaded")
        
        # Load scaler
        scaler_path = os.path.join(MODELS_DIR, 'feature_scaler.pkl')
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            self.feature_extractor.scaler = self.scaler
    
    def predict_single_email(self, email_text):
        """Predict whether email is phishing"""
        if self.model is None:
            return {"error": "No model loaded"}
        
        # Preprocess
        processed = self.text_preprocessor.preprocess_pipeline(email_text, extract_features=True)
        
        # TF-IDF features
        tfidf_features = self.vectorizer.transform([processed['cleaned_text']])
        
        # Numeric features
        numeric_features = np.array([[
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
            numeric_features = self.scaler.transform(numeric_features)
        
        # Combine
        from scipy.sparse import hstack, csr_matrix
        combined = hstack([tfidf_features, csr_matrix(numeric_features)])
        
        # Get probability
        proba = self.model.predict_proba(combined)[0]
        probability = proba[1]
        
        # Apply threshold
        is_phishing = probability > self.threshold
        
        # Calculate confidence
        if is_phishing:
            confidence = min(100, ((probability - self.threshold) / (1 - self.threshold)) * 100)
        else:
            confidence = min(100, ((self.threshold - probability) / self.threshold) * 100)
        
        return {
            'is_phishing': is_phishing,
            'label': '⚠️ PHISHING' if is_phishing else '✅ LEGITIMATE',
            'probability': probability,
            'confidence': confidence,
            'threshold': self.threshold,
            'features': {
                'url_count': processed.get('url_count', 0),
                'urgent_keywords': processed.get('urgent_keyword_count', 0),
                'exclamation_count': processed.get('exclamation_count', 0),
                'all_caps_count': processed.get('all_caps_count', 0)
            }
        }

def run_interactive():
    """Run interactive mode"""
    print("\n" + "="*60)
    print("🤖 AI-POWERED PHISHING DETECTOR")
    print("   Using NLP - Calibrated Model")
    print("="*60)
    
    predictor = PhishingPredictor()
    
    if predictor.model is None:
        print("\n❌ Please run: python train_calibrated_final.py")
        return
    
    print(f"\n✅ System Ready!")
    print(f"   Model: Calibrated Logistic Regression")
    print(f"   Threshold: {predictor.threshold*100:.1f}%")
    
    print("\n📝 Commands:")
    print("   • Enter email text")
    print("   • 'test' for test cases")
    print("   • 'exit' to quit")
    print("-"*50)
    
    test_emails = [
        ("URGENT: Your account has been limited! Click here: http://fake.com", "phishing"),
        ("Hi team, meeting at 3pm today. Please bring updates.", "legitimate"),
        ("Your Amazon order #12345 has shipped and will arrive tomorrow.", "legitimate"),
        ("FINAL NOTICE: Your account will be closed. Update now!", "phishing"),
        ("Netflix: Your monthly statement is now available.", "legitimate"),
        ("Your PayPal account has been suspended. Verify now!", "phishing")
    ]
    
    while True:
        print()
        choice = input("📨 Enter email: ").strip()
        
        if choice.lower() == 'exit':
            print("\n👋 Goodbye!")
            break
        
        elif choice.lower() == 'test':
            print("\n📋 Running test cases:")
            correct = 0
            for i, (email, expected) in enumerate(test_emails, 1):
                result = predictor.predict_single_email(email)
                is_correct = (result['is_phishing'] and expected == 'phishing') or \
                            (not result['is_phishing'] and expected == 'legitimate')
                if is_correct:
                    correct += 1
                
                print(f"\n--- Test {i} ---")
                print(f"Email: {email[:60]}...")
                print(f"Expected: {expected}")
                print(f"Result: {result['label']}")
                print(f"Probability: {result['probability']*100:.1f}%")
                print(f"Confidence: {result['confidence']:.1f}%")
                print(f"{'✅ CORRECT' if is_correct else '❌ INCORRECT'}")
            
            print(f"\n📊 Accuracy: {correct}/{len(test_emails)} ({correct/len(test_emails)*100:.1f}%)")
        
        elif choice:
            result = predictor.predict_single_email(choice)
            print(f"\n🎯 Result: {result['label']}")
            print(f"   Probability: {result['probability']*100:.1f}%")
            print(f"   Confidence: {result['confidence']:.1f}%")
            print(f"   Threshold: {result['threshold']*100:.1f}%")
            
            if result['features']['url_count'] > 0:
                print(f"   ⚠️  Contains {result['features']['url_count']} URL(s)")
            if result['features']['urgent_keywords'] > 2:
                print(f"   ⚠️  {result['features']['urgent_keywords']} urgent keywords")
        
        else:
            print("❌ Please enter some text")

if __name__ == "__main__":
    run_interactive()