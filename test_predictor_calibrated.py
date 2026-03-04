#!/usr/bin/env python3
"""
Test phishing detector with calibrated threshold
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.prediction_interface import PhishingPredictor

print("="*60)
print("🧪 TESTING PHISHING DETECTOR (With Calibrated Threshold)")
print("="*60)

# Initialize predictor
predictor = PhishingPredictor('logistic_regression_model')
predictor.threshold = 0.65  # Set calibrated threshold

if predictor.model is None:
    print("❌ Model not found.")
    sys.exit(1)

# Test emails
test_emails = [
    {
        'text': "URGENT: Your PayPal account has been limited. Click here to verify: http://fake-paypal.com",
        'expected': 'phishing'
    },
    {
        'text': "Hi team, meeting at 3pm today. Please bring your updates.",
        'expected': 'legitimate'
    },
    {
        'text': "Your Amazon order #12345 has been shipped and will arrive tomorrow.",
        'expected': 'legitimate'
    },
    {
        'text': "FINAL NOTICE: Your account will be closed. Update now: http://scam-bank.com",
        'expected': 'phishing'
    },
    {
        'text': "Netflix: Your monthly statement is now available. View at netflix.com/billing",
        'expected': 'legitimate'
    },
    {
        'text': "Your LinkedIn connection request was accepted by Sarah Johnson.",
        'expected': 'legitimate'
    }
]

print(f"\n🔍 Testing with threshold = {predictor.threshold*100:.0f}%\n")

correct = 0
for i, test in enumerate(test_emails, 1):
    print(f"\n--- Test {i} ---")
    print(f"Email: {test['text'][:60]}...")
    print(f"Expected: {test['expected']}")
    
    result = predictor.predict_single_email(test['text'])
    
    print(f"Result: {result['label']}")
    print(f"Raw probability: {result['raw_probability']*100:.1f}%")
    print(f"Confidence: {result['display_confidence']:.1f}%")
    
    # Check if correct
    is_correct = (result['is_phishing'] and test['expected'] == 'phishing') or \
                 (not result['is_phishing'] and test['expected'] == 'legitimate')
    if is_correct:
        correct += 1
        print("✅ CORRECT")
    else:
        print("❌ INCORRECT")
    print("-" * 40)

print(f"\n📊 Results: {correct}/{len(test_emails)} correct ({correct/len(test_emails)*100:.1f}%)")
print("\n👉 Run 'python main.py --mode interactive' for interactive mode")
