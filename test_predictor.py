#!/usr/bin/env python3
"""
Quick test for the phishing detector
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.prediction_interface import PhishingPredictor

print("="*60)
print("🧪 TESTING PHISHING DETECTOR")
print("="*60)

# Initialize predictor
predictor = PhishingPredictor()

if predictor.model is None:
    print("❌ Model not found. Please run training first.")
    sys.exit(1)

# Test emails
test_emails = [
    "URGENT: Your PayPal account has been limited. Click here to verify: http://fake-paypal.com",
    "Hi team, meeting at 3pm today. Please bring your updates.",
    "Your Amazon order #12345 has been shipped and will arrive tomorrow.",
    "FINAL NOTICE: Your account will be closed. Update now: http://scam-bank.com"
]

print("\n🔍 Testing with sample emails:\n")

for i, email in enumerate(test_emails, 1):
    print(f"\n--- Test {i} ---")
    result = predictor.predict_single_email(email)
    print(f"Email: {email[:50]}...")
    print(f"Result: {result['label']}")
    if result['probability']:
        print(f"Confidence: {result['probability']*100:.1f}%")
    print("-" * 40)

print("\n✅ Test complete!")
