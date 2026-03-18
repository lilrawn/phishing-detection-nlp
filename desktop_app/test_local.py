#!/usr/bin/env python3
"""
Test local phishing detection without API
"""
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.predictor_hybrid import HybridPredictor

def test_local():
    """Test local hybrid model"""
    print("="*60)
    print("🔍 Testing Local Hybrid Phishing Detection")
    print("="*60)
    
    predictor = HybridPredictor(ml_weight=0.3)
    
    test_emails = [
        {
            'name': 'Legitimate Amazon',
            'text': """From: orders@amazon.com
Subject: Your Amazon order has shipped

Your order #123-4567890 has shipped and will arrive Monday."""
        },
        {
            'name': 'Phishing PayPal',
            'text': """From: security@paypal-verify.net
Subject: URGENT: Account Limited

Click here to verify: http://fake-paypal.com"""
        },
        {
            'name': 'Legitimate Netflix',
            'text': """From: info@netflix.com
Subject: Your Netflix statement

Your monthly statement is now available."""
        }
    ]
    
    for test in test_emails:
        print(f"\n📧 Testing: {test['name']}")
        result = predictor.predict(test['text'])
        print(f"   Result: {result['label']}")
        print(f"   Confidence: {result['final_score']:.1f}%")
        if result.get('reasons'):
            print("   Reasons:")
            for r in result['reasons']:
                print(f"     • {r}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_local()