#!/usr/bin/env python3
"""
Test the base model directly
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
print("🧪 TESTING BASE MODEL")
print("="*60)

# Load model and vectorizer
model_path = os.path.join(MODELS_DIR, 'logistic_regression_base.pkl')
vec_path = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')

if not os.path.exists(model_path):
    print("❌ Base model not found!")
    sys.exit(1)

model = joblib.load(model_path)
vectorizer = joblib.load(vec_path)
preprocessor = TextPreprocessor()

print("✅ Model loaded successfully!")

# Test cases
test_emails = [
    "URGENT: Your account has been limited! Click here: http://fake.com",
    "Hi team, meeting at 3pm today. Please bring updates.",
    "Your Amazon order #12345 has been shipped.",
    "FINAL NOTICE: Your account will be closed. Update now!",
    "Netflix: Your monthly statement is now available.",
    "Your PayPal account has been suspended. Verify now!"
]

print("\n📊 Testing predictions:")
print("-" * 60)

for i, email in enumerate(test_emails, 1):
    # Preprocess
    processed = preprocessor.preprocess_pipeline(email, extract_features=True)
    
    # Get features
    tfidf = vectorizer.transform([processed['cleaned_text']])
    
    # Predict
    proba = model.predict_proba(tfidf)[0]
    prob = proba[1]
    pred = "⚠️ PHISHING" if prob > 0.5 else "✅ LEGITIMATE"
    
    print(f"\nTest {i}:")
    print(f"  Email: {email[:60]}...")
    print(f"  Probability: {prob*100:.1f}%")
    print(f"  Prediction: {pred}")
    
print("\n" + "="*60)
