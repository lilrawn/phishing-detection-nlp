#!/usr/bin/env python3
"""
Test that all features are being used correctly
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
print("🧪 TESTING FEATURE DIMENSIONS")
print("="*60)

# Load model and vectorizer
model_path = os.path.join(MODELS_DIR, 'logistic_regression_base.pkl')
vec_path = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')
scaler_path = os.path.join(MODELS_DIR, 'feature_scaler.pkl')

if not os.path.exists(model_path):
    print("❌ Base model not found!")
    sys.exit(1)

model = joblib.load(model_path)
vectorizer = joblib.load(vec_path)
scaler = joblib.load(scaler_path) if os.path.exists(scaler_path) else None
preprocessor = TextPreprocessor()

print(f"✅ Model expects: {model.coef_.shape[1]} features")
print(f"✅ Vectorizer produces: {len(vectorizer.get_feature_names_out())} TF-IDF features")
print(f"✅ Numeric features: 8")
print(f"✅ Total expected: {len(vectorizer.get_feature_names_out()) + 8} features")

# Test with a sample email
test_email = "URGENT: Your account has been limited! Click here: http://fake.com"

print(f"\n📧 Testing with: {test_email[:50]}...")

# Preprocess
processed = preprocessor.preprocess_pipeline(test_email, extract_features=True)

# Get features
tfidf = vectorizer.transform([processed['cleaned_text']])
print(f"   TF-IDF shape: {tfidf.shape}")

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
print(f"   Numeric shape: {numeric.shape}")

if scaler:
    numeric = scaler.transform(numeric)
    print(f"   Numeric (scaled) shape: {numeric.shape}")

# Combine
combined = hstack([tfidf, csr_matrix(numeric)])
print(f"   Combined shape: {combined.shape}")

# Predict
proba = model.predict_proba(combined)[0]
prob = proba[1]

print(f"\n🎯 Prediction: {'PHISHING' if prob > 0.5 else 'LEGITIMATE'}")
print(f"   Probability: {prob*100:.1f}%")
print("="*60)
