#!/usr/bin/env python3
"""
Complete setup script for the Phishing Detection Project
Run this once to set up everything
"""

import os
import sys
import subprocess
import ssl

def fix_ssl():
    """Fix SSL certificate issues"""
    print("🔧 Fixing SSL certificate issues...")
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    print("✅ SSL fix applied")

def download_nltk_data():
    """Download required NLTK data"""
    print("\n📥 Downloading NLTK data...")
    import nltk
    packages = ['stopwords', 'punkt', 'wordnet']
    for package in packages:
        try:
            nltk.download(package, quiet=False)
            print(f"  ✅ Downloaded {package}")
        except Exception as e:
            print(f"  ❌ Error downloading {package}: {e}")
    print("✅ NLTK data download complete")

def download_spacy_model():
    """Download spaCy model"""
    print("\n📥 Downloading spaCy model...")
    try:
        subprocess.run([sys.executable, '-m', 'spacy', 'download', 'en_core_web_sm'], check=True)
        print("✅ spaCy model downloaded")
    except Exception as e:
        print(f"❌ Error downloading spaCy model: {e}")

def create_directory_structure():
    """Create necessary directories"""
    print("\n📁 Creating directory structure...")
    dirs = [
        'data/raw',
        'data/processed',
        'models',
        'results/confusion_matrices',
        'results/visualizations',
        'notebooks',
        'src'
    ]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"  ✅ Created/Verified: {dir_path}")

def check_raw_data():
    """Check what raw data files are available"""
    print("\n🔍 Checking raw data files...")
    raw_dir = 'data/raw'
    if os.path.exists(raw_dir):
        files = os.listdir(raw_dir)
        if files:
            print("  Found raw data files:")
            for f in files:
                file_path = os.path.join(raw_dir, f)
                size = os.path.getsize(file_path)
                print(f"    - {f} ({size} bytes)")
        else:
            print("  ⚠️  No raw data files found")
            print("  Please place your datasets in data/raw/:")
            print("    - Mail-SpamAssassin-3.4.6/ (folder)")
            print("    - email_text.csv")
            print("    - Nazario_5.csv")
    else:
        print("  ⚠️  Raw data directory not found")

def create_dataset():
    """Run the dataset creation script"""
    print("\n📊 Creating combined dataset...")
    try:
        subprocess.run([sys.executable, 'create_dataset.py'], check=True)
        print("✅ Dataset creation complete")
    except Exception as e:
        print(f"❌ Error creating dataset: {e}")

def main():
    """Main setup function"""
    print("="*60)
    print("🚀 PHISHING DETECTION PROJECT - SETUP")
    print("="*60)
    
    # Step 1: Fix SSL
    fix_ssl()
    
    # Step 2: Create directories
    create_directory_structure()
    
    # Step 3: Download NLTK data
    download_nltk_data()
    
    # Step 4: Download spaCy model
    download_spacy_model()
    
    # Step 5: Check raw data
    check_raw_data()
    
    # Step 6: Create dataset
    create_dataset()
    
    print("\n" + "="*60)
    print("✅ SETUP COMPLETE!")
    print("="*60)
    print("\nYou can now run:")
    print("  python main.py --mode train")
    print("  python main.py --mode interactive")
    print("  python main.py --mode predict --email \"Your email text here\"")

if __name__ == "__main__":
    main()
