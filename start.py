#!/usr/bin/env python3
"""
Simple launcher for phishing detection
"""
import sys
import os

# Fix SSL for NLTK
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download NLTK data quietly
import nltk
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

print("\n" + "="*60)
print("🔍 PHISHING EMAIL DETECTION")
print("="*60)

from src.predictor_simple import run_simple_interactive
run_simple_interactive()