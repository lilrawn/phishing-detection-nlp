#!/usr/bin/env python3
"""
Fix NLTK data download issues by bypassing SSL verification
"""
import ssl
import nltk
import os

def fix_ssl_and_download():
    """Fix SSL and download NLTK data"""
    # Disable SSL verification for downloads
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    
    # Create nltk_data directory if it doesn't exist
    nltk_data_dir = os.path.expanduser('~/nltk_data')
    os.makedirs(nltk_data_dir, exist_ok=True)
    
    # Add to nltk path
    nltk.data.path.append(nltk_data_dir)
    
    # Download required packages
    packages = ['punkt', 'punkt_tab', 'stopwords', 'wordnet']
    
    for package in packages:
        try:
            print(f"Downloading {package}...")
            nltk.download(package, quiet=False, download_dir=nltk_data_dir)
            print(f"✅ {package} downloaded successfully")
        except Exception as e:
            print(f"❌ Error downloading {package}: {e}")
    
    print("\n" + "="*60)
    print("📦 NLTK Data Installation Complete")
    print("="*60)
    print(f"Data installed at: {nltk_data_dir}")
    
    # Test tokenization
    try:
        from nltk.tokenize import word_tokenize
        test_text = "This is a test sentence."
        tokens = word_tokenize(test_text)
        print(f"✅ Tokenization test passed: {tokens}")
    except Exception as e:
        print(f"❌ Tokenization test failed: {e}")

if __name__ == "__main__":
    fix_ssl_and_download()