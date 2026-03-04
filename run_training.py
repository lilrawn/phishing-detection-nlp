#!/usr/bin/env python3
"""
Simple script to run training with visible output
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("🚀 STARTING PHISHING DETECTION TRAINING")
print("="*60)
print("This will take 10-20 minutes depending on your computer...")
print("Output will appear below:\n")

# Import and run main
import main
main.main()
