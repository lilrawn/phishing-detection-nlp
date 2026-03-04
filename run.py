#!/usr/bin/env python3
"""
Simple launcher for phishing detection
"""
import os
import sys

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
print("🔍 PHISHING EMAIL DETECTION SYSTEM")
print("="*60)
print("\nOptions:")
print("1. Train new model")
print("2. Run interactive mode (Base Model - Recommended)")
print("3. Exit")

choice = input("\nChoice (1-3): ").strip()

if choice == '1':
    print("\n🚀 Training model...")
    os.system(f"{sys.executable} train_final.py")
elif choice == '2':
    print("\n🤖 Starting interactive mode...")
    from src.predictor import run_interactive
    run_interactive()
else:
    print("\n👋 Goodbye!")