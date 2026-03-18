#!/usr/bin/env python3
"""
Run hybrid phishing detector demo
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

from src.predictor_hybrid import run_hybrid_demo
run_hybrid_demo()
