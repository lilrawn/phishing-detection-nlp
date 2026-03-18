#!/usr/bin/env python3
"""
Quick test of the phishing model
"""
import sys
import os
import joblib
import numpy as np
from scipy.sparse import hstack, csr_matrix

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.preprocessing import TextPreprocessor
from config import MODELS_DIR

print("="*60)
print("🔍 QUICK MODEL TEST")
print("="*60)

# Load model and vectorizer
model_path = os.path.join(MODELS_DIR, 'phishing_model.pkl')
vec_path = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')

if not os.path.exists(model_path):
    print("❌ Model not found!")
    sys.exit(1)

model = joblib.load(model_path)
vectorizer = joblib.load(vec_path)
preprocessor = TextPreprocessor()

print(f"✅ Model loaded: {type(model).__name__}")
print(f"✅ Vectorizer loaded: {vectorizer}")

# Test cases
test_emails = [
    "URGENT: Your account has been limited! Click here: http://fake.com",
    "Hi team, meeting at 3pm today. Please bring updates.",
    "Your Amazon order #12345 has been shipped and will arrive tomorrow.",
    "FINAL NOTICE: Your account will be closed. Update now!",
    "Netflix: Your monthly statement is now available.",
    "Your PayPal account has been suspended. Verify now!"
]

print("\n📧 Testing emails:\n")

for i, email in enumerate(test_emails, 1):
    # Preprocess
    processed = preprocessor.preprocess_pipeline(email, extract_features=True)
    
    # Vectorize
    features = vectorizer.transform([processed['cleaned_text']])
    
    # Add numeric features (if model expects them)
    if hasattr(model, 'coef_') and model.coef_.shape[1] > features.shape[1]:
        # Model expects more features, add zeros for numeric
        numeric = np.zeros((1, model.coef_.shape[1] - features.shape[1]))
        features = hstack([features, csr_matrix(numeric)])
    
    # Predict
    if hasattr(model, 'predict_proba'):
        prob = model.predict_proba(features)[0][1]
    else:
        prob = model.predict(features)[0]
    
    print(f"Test {i}:")
    print(f"  Email: {email[:60]}...")
    print(f"  Probability: {prob*100:.1f}%")
    print(f"  Prediction: {'⚠️ PHISHING' if prob > 0.5 else '✅ LEGITIMATE'}")
    print("-" * 40)
