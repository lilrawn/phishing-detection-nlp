#!/usr/bin/env python3
"""
Quick test of the phishing model
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.predictor import PhishingPredictor, TEST_CASES

print("=" * 60)
print("🔍 QUICK MODEL TEST")
print("=" * 60)

predictor = PhishingPredictor()

if predictor.model is None:
    print("❌ Model not found!")
    sys.exit(1)

print(f"✅ Model loaded: {type(predictor.model).__name__}")

print("\n📧 Testing emails:\n")

for i, (email, expected) in enumerate(TEST_CASES, 1):
    result = predictor.predict(email)
    print(f"Test {i}:")
    print(f"  Email: {email[:60]}...")
    print(f"  Expected: {expected}")
    print(f"  Probability: {result['probability'] * 100:.1f}%")
    print(f"  Prediction: {result['label']}")
    print("-" * 40)
