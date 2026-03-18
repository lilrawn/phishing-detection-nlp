#!/usr/bin/env python3
"""
Test Gemini API integration
"""
import sys
import os
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from desktop_app.backend.gemini_analyzer import gemini_analyzer

def test_gemini():
    """Test Gemini API with sample emails"""
    print("="*60)
    print("🤖 Testing Gemini AI Phishing Detection")
    print("="*60)
    
    # Test legitimate email
    legit_email = """From: orders@amazon.com
Subject: Your Amazon order has shipped

Hello,

Your order #123-4567890 has shipped and will arrive Monday.
Track your package at amazon.com/tracking

Thank you,
Amazon Customer Service"""
    
    print("\n📧 Testing LEGITIMATE email...")
    time.sleep(2)  # Rate limiting
    result = gemini_analyzer.analyze_with_gemini(legit_email)
    print(f"AI Verdict: {'🔴 PHISHING' if result.get('is_phishing') else '🟢 LEGITIMATE'}")
    print(f"Confidence: {result.get('confidence', 0)}%")
    if result.get('reasons'):
        print("Reasons:")
        for r in result['reasons']:
            print(f"  • {r}")
    if result.get('sender_analysis'):
        print(f"Sender Analysis: {result['sender_analysis']}")
    if result.get('urgency_level'):
        print(f"Urgency Level: {result['urgency_level']}")
    
    # Test phishing email
    phishing_email = """From: security@paypal-verify.net
Subject: URGENT: Your account has been limited

Dear Valued Customer,

We have detected unusual activity on your account.
Click here to verify immediately: http://paypal-verify.com/secure

Failure to verify will result in account suspension.

PayPal Security Team"""
    
    print("\n📧 Testing PHISHING email...")
    time.sleep(2)  # Rate limiting
    result = gemini_analyzer.analyze_with_gemini(phishing_email)
    print(f"AI Verdict: {'🔴 PHISHING' if result.get('is_phishing') else '🟢 LEGITIMATE'}")
    print(f"Confidence: {result.get('confidence', 0)}%")
    if result.get('reasons'):
        print("Reasons:")
        for r in result['reasons']:
            print(f"  • {r}")
    if result.get('sender_analysis'):
        print(f"Sender Analysis: {result['sender_analysis']}")
    if result.get('suspicious_links'):
        print(f"Suspicious Links: {result['suspicious_links']}")
    
    # Test suspicious sender
    print("\n📧 Testing suspicious sender...")
    time.sleep(2)  # Rate limiting
    result = gemini_analyzer.analyze_sender("security@paypal-verify.net")
    if isinstance(result, dict):
        print(f"Sender Analysis Result:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    
    print("\n" + "="*60)
    print("\n⚠️ Note: If you see rate limit errors, wait a minute and try again.")
    print("The free tier has limits. For production, upgrade your API plan.")

if __name__ == "__main__":
    test_gemini()