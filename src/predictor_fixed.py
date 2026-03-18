"""
Fixed predictor for phishing detection
"""
import numpy as np
import joblib
import os
import sys
from scipy.sparse import hstack, csr_matrix

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MODELS_DIR
from src.preprocessing import TextPreprocessor

class PhishingPredictor:
    """Fixed predictor using trained model with all features"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.scaler = None
        self.preprocessor = TextPreprocessor()
        self.load_models()
        
    def load_models(self):
        """Load model and vectorizer"""
        print("Loading models...", end="", flush=True)
        
        # Try different model filenames
        model_paths = [
            os.path.join(MODELS_DIR, 'logistic_regression_base.pkl'),
            os.path.join(MODELS_DIR, 'phishing_model.pkl'),
            os.path.join(MODELS_DIR, 'best_model.pkl')
        ]
        
        for path in model_paths:
            if os.path.exists(path):
                self.model = joblib.load(path)
                print(f" ✓ Model", end="", flush=True)
                break
        
        vec_path = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')
        if os.path.exists(vec_path):
            self.vectorizer = joblib.load(vec_path)
            print(f" ✓ Vectorizer", end="", flush=True)
        
        # Load scaler if it exists
        scaler_path = os.path.join(MODELS_DIR, 'feature_scaler.pkl')
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            print(f" ✓ Scaler", end="", flush=True)
        
        print()
        print(f"   Model expects {self.model.coef_.shape[1]} features")
        
    def predict(self, email_text):
        """Predict if email is phishing"""
        if self.model is None or self.vectorizer is None:
            return {"error": "Models not loaded"}
        
        # Preprocess and extract ALL features
        processed = self.preprocessor.preprocess_pipeline(email_text, extract_features=True)
        
        # Get TF-IDF features (2000 features)
        tfidf_features = self.vectorizer.transform([processed['cleaned_text']])
        print(f"   Debug: TF-IDF features shape: {tfidf_features.shape}")
        
        # Get numeric features (8 features)
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
        print(f"   Debug: Numeric features shape: {numeric_features.shape}")
        
        # Scale numeric features if scaler exists
        if self.scaler:
            numeric_features = self.scaler.transform(numeric_features)
        
        # Combine features (2000 + 8 = 2008 features)
        from scipy.sparse import hstack, csr_matrix
        combined_features = hstack([tfidf_features, csr_matrix(numeric_features)])
        print(f"   Debug: Combined features shape: {combined_features.shape}")
        
        # Get probability
        if hasattr(self.model, 'predict_proba'):
            proba = self.model.predict_proba(combined_features)[0]
            prob = proba[1] if len(proba) > 1 else proba[0]
        else:
            prob = float(self.model.predict(combined_features)[0])
        
        # Simple threshold at 50%
        is_phishing = prob > 0.5
        
        # Calculate confidence (distance from 50%)
        confidence = abs(prob - 0.5) * 200
        
        return {
            'is_phishing': is_phishing,
            'label': '⚠️ PHISHING' if is_phishing else '✅ LEGITIMATE',
            'probability': prob,
            'confidence': confidence,
            'threshold': 0.5,
            'features': {
                'urls': processed.get('url_count', 0),
                'urgent_words': processed.get('urgent_keyword_count', 0),
                'exclamations': processed.get('exclamation_count', 0),
                'all_caps': processed.get('all_caps_count', 0)
            }
        }

def run_fixed_interactive():
    """Run fixed interactive mode"""
    print("\n" + "="*60)
    print("🤖 PHISHING EMAIL DETECTOR (FIXED VERSION)")
    print("   Natural Language Processing + Machine Learning")
    print("="*60)
    
    predictor = PhishingPredictor()
    
    if predictor.model is None:
        print("\n❌ No trained model found!")
        print("   Please run: python train_proper.py")
        return
    
    print(f"\n✅ System Ready!")
    print(f"   Model: Logistic Regression (98% accuracy)")
    print(f"   Features: 2000 TF-IDF + 8 numeric = 2008 total")
    print(f"   Threshold: 50%")
    
    print("\n📝 Commands:")
    print("   • Type an email to analyze")
    print("   • 'test' - run test cases")
    print("   • 'exit' - quit")
    print("-"*50)
    
    # Test cases for demonstration
    test_cases = [
        ("URGENT: Your account has been limited! Click here: http://fake.com", "phishing"),
        ("Hi team, meeting at 3pm today. Please bring updates.", "legitimate"),
        ("Your Amazon order #12345 has been shipped and will arrive tomorrow.", "legitimate"),
        ("FINAL NOTICE: Your account will be closed. Update now!", "phishing"),
        ("Netflix: Your monthly statement is now available.", "legitimate"),
        ("Your PayPal account has been suspended. Verify now!", "phishing"),
    ]
    
    while True:
        print()
        text = input("📨 Enter email: ").strip()
        
        if text.lower() == 'exit':
            print("\n👋 Goodbye!")
            break
            
        elif text.lower() == 'test':
            print("\n📋 Running test cases:")
            correct = 0
            for i, (email, expected) in enumerate(test_cases, 1):
                result = predictor.predict(email)
                is_correct = (result['is_phishing'] and expected == 'phishing') or \
                            (not result['is_phishing'] and expected == 'legitimate')
                if is_correct:
                    correct += 1
                
                print(f"\nTest {i}:")
                print(f"  Email: {email[:60]}...")
                print(f"  Expected: {expected}")
                print(f"  Result: {result['label']}")
                print(f"  Probability: {result['probability']*100:.1f}%")
                print(f"  Confidence: {result['confidence']:.1f}%")
                print(f"  {'✅' if is_correct else '❌'}")
            
            print(f"\n📊 Accuracy: {correct}/{len(test_cases)} ({correct/len(test_cases)*100:.1f}%)")
            
        elif text:
            result = predictor.predict(text)
            print(f"\n🎯 Result: {result['label']}")
            print(f"   Probability: {result['probability']*100:.1f}%")
            print(f"   Confidence: {result['confidence']:.1f}%")

if __name__ == "__main__":
    run_fixed_interactive()
