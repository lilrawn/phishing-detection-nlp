#!/usr/bin/env python3
"""
Test fixed hybrid model
"""
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.predictor_hybrid import HybridPredictor

def test_fixed():
    """Test fixed hybrid model"""
    print("="*60)
    print("🔍 Testing Fixed Hybrid Model")
    print("="*60)
    
    predictor = HybridPredictor(ml_weight=0.3)
    
    test_emails = [
        {
            'name': 'Amazon Shipping (Legitimate)',
            'text': """From: orders@amazon.com
Subject: Your Amazon order has shipped

Your order #123-4567890 has shipped and will arrive Monday.
Track your package at amazon.com/tracking"""
        },
        {
            'name': 'PayPal Phishing',
            'text': """From: security@paypal-verify.net
Subject: URGENT: Account Limited

Click here to verify: http://fake-paypal.com/secure"""
        },
        {
            'name': 'Netflix Statement (Legitimate)',
            'text': """From: info@netflix.com
Subject: Your Netflix statement

Your monthly statement is now available at netflix.com/account"""
        },
        {
            'name': 'Suspicious Nigerian Prince',
            'text': """From: prince@unknown-domain.com
Subject: URGENT: Please help me

I need your help to transfer $10 million out of my country.
Click here to claim your share: http://scam.com/claim"""
        }
    ]
    
    for test in test_emails:
        print(f"\n📧 Testing: {test['name']}")
        result = predictor.predict(test['text'])
        print(f"   Result: {result['label']}")
        print(f"   Confidence: {result['final_score']:.1f}%")
        print(f"   Rules Score: {result['rule_score']:.1f}%")
        print(f"   ML Score: {result['ml_score']:.1f}%")
        if result.get('reasons'):
            print("   Reasons:")
            for r in result['reasons']:
                print(f"     • {r}")
        print("-" * 40)
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_fixed()
