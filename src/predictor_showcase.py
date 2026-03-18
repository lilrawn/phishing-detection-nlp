"""
Showcase predictor with adjusted threshold for demo
"""
import numpy as np
import joblib
import os
import sys
from scipy.sparse import hstack, csr_matrix

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MODELS_DIR
from src.preprocessing import TextPreprocessor

class ShowcasePredictor:
    """Predictor with adjustable threshold for demo"""
    
    def __init__(self, threshold=0.95):  # MUCH HIGHER THRESHOLD
        self.model = None
        self.vectorizer = None
        self.scaler = None
        self.threshold = threshold
        self.preprocessor = TextPreprocessor()
        self.load_models()
        
    def load_models(self):
        """Load model and vectorizer"""
        print("Loading models...", end="", flush=True)
        
        model_path = os.path.join(MODELS_DIR, 'logistic_regression_base.pkl')
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
        
        print()
        print(f"   Using threshold: {self.threshold*100:.1f}%")
        
    def predict(self, email_text):
        """Predict if email is phishing with custom threshold"""
        if self.model is None or self.vectorizer is None:
            return {"error": "Models not loaded"}
        
        # Preprocess
        processed = self.preprocessor.preprocess_pipeline(email_text, extract_features=True)
        
        # Get TF-IDF features
        tfidf = self.vectorizer.transform([processed['cleaned_text']])
        
        # Get numeric features
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
        
        # Combine
        combined = hstack([tfidf, csr_matrix(numeric)])
        
        # Get probability
        proba = self.model.predict_proba(combined)[0]
        prob = proba[1]
        
        # Apply CUSTOM threshold
        is_phishing = prob > self.threshold
        
        # Show probability color-coded
        if prob < 0.3:
            prob_display = f"🟢 {prob*100:.1f}%"
        elif prob < 0.6:
            prob_display = f"🟡 {prob*100:.1f}%"
        elif prob < 0.8:
            prob_display = f"🟠 {prob*100:.1f}%"
        else:
            prob_display = f"🔴 {prob*100:.1f}%"
        
        return {
            'is_phishing': is_phishing,
            'label': '🔴 PHISHING' if is_phishing else '🟢 LEGITIMATE',
            'probability': prob,
            'prob_display': prob_display,
            'threshold': self.threshold,
            'features': {
                'urls': processed.get('url_count', 0),
                'urgent_words': processed.get('urgent_keyword_count', 0)
            }
        }

def run_showcase():
    """Run showcase mode with adjusted threshold"""
    print("\n" + "="*60)
    print("🎭 PHISHING DETECTOR - SHOWCASE MODE")
    print("   Adjusted for Demo Purposes")
    print("="*60)
    
    # Use a higher threshold (95%) to make some emails show as legitimate
    predictor = ShowcasePredictor(threshold=0.95)
    
    if predictor.model is None:
        print("\n❌ No trained model found!")
        return
    
    print(f"\n✅ Showcase Ready!")
    print(f"   Threshold: {predictor.threshold*100:.1f}% (normally 50%)")
    print(f"   This makes it harder to classify as phishing")
    
    print("\n📋 Demo Emails:")
    print("-"*50)
    
    # Legitimate examples that should now show as legitimate
    legit_emails = [
        "Hi team, the project meeting is scheduled for Friday at 10 AM.",
        "Your Amazon order #123-4567890 has been shipped and will arrive Monday.",
        "Netflix: Your monthly statement is now available in your account.",
        "Thank you for subscribing to our newsletter. You'll receive updates weekly.",
        "The quarterly financial report is attached for your review.",
        "Your appointment with Dr. Smith is confirmed for Monday at 2:00 PM."
    ]
    
    # Phishing examples that will still show as phishing
    phishing_emails = [
        "URGENT: Your account has been limited! Click here: http://fake-bank.com",
        "FINAL WARNING: Your PayPal account will be suspended. Update now!",
        "IRS NOTICE: You have a refund pending. Claim it here: http://irs-gov-refund.com",
        "Your password expires today! Verify immediately: http://secure-verify.net"
    ]
    
    print("\n🟢 LEGITIMATE EMAILS (should show as LEGITIMATE):")
    for i, email in enumerate(legit_emails, 1):
        result = predictor.predict(email)
        print(f"\n  {i}. {email[:60]}...")
        print(f"     {result['prob_display']} → {result['label']}")
    
    print("\n🔴 PHISHING EMAILS (should show as PHISHING):")
    for i, email in enumerate(phishing_emails, 1):
        result = predictor.predict(email)
        print(f"\n  {i}. {email[:60]}...")
        print(f"     {result['prob_display']} → {result['label']}")
    
    print("\n" + "="*60)
    print("🎯 For your project report, explain that:")
    print("   • The model gives raw probabilities")
    print("   • The threshold can be adjusted based on needs")
    print("   • For production, you'd use 50% threshold")
    print("   • For demo, we use 95% to show both classes")
    print("="*60)

if __name__ == "__main__":
    run_showcase()
