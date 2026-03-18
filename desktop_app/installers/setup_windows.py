"""
Windows installer for Phishing Detector
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def create_windows_installer():
    """Create Windows executable"""
    print("🔧 Creating Windows installer...")
    
    # Install PyInstaller
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
    
    # Create spec file
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../src/*', 'src'),
        ('../models/*', 'models'),
        ('frontend/resources/icon.ico', 'resources'),
    ],
    hiddenimports=['sklearn', 'numpy', 'scipy', 'nltk'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PhishingDetector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='frontend/resources/icon.ico'
)
'''
    
    with open('phishing_detector.spec', 'w') as f:
        f.write(spec_content)
    
    # Build executable
    subprocess.run(['pyinstaller', 'phishing_detector.spec'])
    
    print("✅ Windows installer created in dist/PhishingDetector.exe")

def create_windows_registry_entries():
    """Create Windows registry entries for startup"""
    import winreg
    
    