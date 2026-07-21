#!/usr/bin/env python3
"""
Local smoke test for the phishing predictor (no browser/Gmail integration required).
Consolidates what were three near-identical scripts (test_local.py, test_fixed.py,
text_fixed_final.py) that only differed in which subset of test emails they ran.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.predictor import PhishingPredictor

TEST_EMAILS = [
    {
        'name': 'Amazon Shipping (Legitimate)',
        'text': """Subject: Your Amazon order has shipped

Your order #123-4567890 has shipped and will arrive Monday.
Track your package at amazon.com/tracking""",
        'sender': 'orders@amazon.com',
    },
    {
        'name': 'PayPal Phishing',
        'text': """Subject: URGENT: Account Limited

Click here to verify: http://fake-paypal.com/secure""",
        'sender': 'security@paypal-verify.net',
    },
    {
        'name': 'Netflix Statement (Legitimate)',
        'text': """Subject: Your Netflix statement

Your monthly statement is now available at netflix.com/account""",
        'sender': 'info@netflix.com',
    },
    {
        'name': 'Team Meeting (Legitimate)',
        'text': """Subject: Team meeting tomorrow

Hi team, meeting at 10am in Conference Room B.
Please bring your updates.""",
        'sender': 'manager@company.com',
    },
    {
        'name': 'Suspicious Nigerian Prince',
        'text': """Subject: URGENT: Please help me

I need your help to transfer $10 million out of my country.
Click here to claim your share: http://scam.com/claim""",
        'sender': 'prince@unknown-domain.com',
    },
]


def run_smoke_test():
    print("=" * 60)
    print("🔍 Phishing Predictor Smoke Test")
    print("=" * 60)

    predictor = PhishingPredictor()

    for test in TEST_EMAILS:
        print(f"\n📧 Testing: {test['name']}")
        result = predictor.predict(test['text'], sender=test['sender'])
        print(f"   Result: {result['label']}")
        print(f"   Probability: {result['probability'] * 100:.1f}% (ML: {result['ml_probability'] * 100:.1f}%)")
        print(f"   Confidence: {result['confidence']:.1f}%")
        if result['reasons']:
            print("   Reasons:")
            for reason in result['reasons']:
                print(f"     • {reason}")
        if result['suspicious_links']:
            print(f"   Suspicious links: {len(result['suspicious_links'])}")
        print("-" * 40)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_smoke_test()
