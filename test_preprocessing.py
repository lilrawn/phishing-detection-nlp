#!/usr/bin/env python3
"""
Test preprocessing with fallback
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.preprocessing import TextPreprocessor

print("="*60)
print("🧪 Testing Text Preprocessor")
print("="*60)

preprocessor = TextPreprocessor()

test_text = """From: security@paypal.com
Subject: URGENT: Your account has been limited

Click here to verify: http://fake-paypal.com/verify"""

print(f"\n📧 Original text:\n{test_text[:100]}...")

result = preprocessor.preprocess_pipeline(test_text, extract_features=True)

print(f"\n📊 Processed result:")
print(f"   Cleaned text: {result['cleaned_text'][:100]}...")
print(f"   URL count: {result['url_count']}")
print(f"   Urgent keywords: {result['urgent_keyword_count']}")
print(f"   Text length: {result['text_length']}")

print("\n✅ Preprocessing test complete!")
