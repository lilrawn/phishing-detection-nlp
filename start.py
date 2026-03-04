#!/usr/bin/env python3
"""
Launcher for phishing detection system
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

print("="*60)
print("🔧 PHISHING DETECTION SYSTEM")
print("="*60)
print("\nChoose an option:")
print("1. Train new model")
print("2. Run interactive mode")
print("3. Test model")
print("4. Exit")

choice = input("\nEnter choice (1-4): ").strip()

if choice == '1':
    print("\n🚀 Training calibrated model...")
    os.system(f"{sys.executable} train_calibrated_final.py")
elif choice == '2':
    print("\n🤖 Starting interactive mode...")
    from src.prediction_interface_final import run_interactive
    run_interactive()
elif choice == '3':
    print("\n🧪 Running tests...")
    os.system(f"{sys.executable} test_predictor_calibrated.py")
else:
    print("\n👋 Goodbye!")
