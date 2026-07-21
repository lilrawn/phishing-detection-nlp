#!/usr/bin/env python3
"""
Fix spaCy installation and download
Run this to fix the spaCy model download error
"""

import subprocess
import sys
import os

def fix_spacy():
    print("="*60)
    print("🔧 FIXING SPACY INSTALLATION")
    print("="*60)
    
    # Step 1: Upgrade pip and setuptools
    print("\n📦 Step 1: Upgrading pip and setuptools...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'])
    
    # Step 2: Uninstall existing spacy
    print("\n📦 Step 2: Reinstalling spacy...")
    subprocess.run([sys.executable, '-m', 'pip', 'uninstall', 'spacy', '-y'])
    
    # Step 3: Install spacy with specific version
    print("\n📦 Step 3: Installing spacy 3.6.1...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'spacy==3.6.1'])
    
    # Step 4: Download model using alternative method
    print("\n📥 Step 4: Downloading en_core_web_sm model...")
    
    # Method 1: Try direct download
    try:
        subprocess.run([
            sys.executable, '-m', 'spacy', 'download', 'en_core_web_sm'
        ], check=True)
        print("✅ Model downloaded successfully!")
    except:
        print("⚠️  Direct download failed, trying alternative method...")
        
        # Method 2: Download via pip
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', 
                'https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.6.0/en_core_web_sm-3.6.0.tar.gz'
            ], check=True)
            print("✅ Model installed via pip!")
        except:
            print("⚠️  Pip install failed, trying manual method...")
            
            # Method 3: Manual download and install
            import urllib.request
            import tarfile
            
            url = "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.6.0/en_core_web_sm-3.6.0.tar.gz"
            filename = "en_core_web_sm-3.6.0.tar.gz"
            
            print(f"📥 Downloading from {url}...")
            urllib.request.urlretrieve(url, filename)
            
            print("📦 Extracting and installing...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', filename])
            
            # Clean up
            os.remove(filename)
            print("✅ Manual download and install complete!")
    
    # Step 5: Verify installation
    print("\n✅ Step 5: Verifying installation...")
    try:
        import spacy
        nlp = spacy.load('en_core_web_sm')
        print(f"✅ spaCy version: {spacy.__version__}")
        print("✅ Model loaded successfully!")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        print("\nTrying one more method...")
        
        # Final method: Use python -m directly
        subprocess.run([
            sys.executable, '-c', 
            "import spacy; spacy.cli.download('en_core_web_sm')"
        ])

if __name__ == "__main__":
    fix_spacy()
