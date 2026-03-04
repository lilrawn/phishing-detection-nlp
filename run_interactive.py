#!/usr/bin/env python3
"""
Simple launcher for interactive mode
"""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suppress NLTK downloads
import nltk
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Set NLTK to silent mode
nltk.data.path.append('/Users/lilrawn/nltk_data')

# Now import and run
from src.prediction_interface import run_interactive_mode

if __name__ == "__main__":
    run_interactive_mode()
