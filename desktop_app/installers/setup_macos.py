"""
macOS installer for Phishing Detector
"""
import os
import sys
import subprocess
from pathlib import Path

def create_macos_app():
    """Create macOS .app bundle"""
    print("🔧 Creating macOS application...")
    
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
        ('frontend/resources/icon.icns', 'resources'),
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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='frontend/resources/icon.icns'
)

app = BUNDLE(
    exe,
    name='PhishingDetector.app',
    icon='frontend/resources/icon.icns',
    bundle_identifier='com.phishingdetector.app',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,
    }
)
'''
    
    with open('phishing_detector_macos.spec', 'w') as f:
        f.write(spec_content)
    
    # Build .app bundle
    subprocess.run(['pyinstaller', 'phishing_detector_macos.spec'])
    
    print("✅ macOS app created in dist/PhishingDetector.app")

def create_launchd_plist():
    """Create launchd plist for background running"""
    plist_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.phishingdetector.background</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/PhishingDetector.app/Contents/MacOS/PhishingDetector</string>
        <string>--background</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>'''
    
    with open('com.phishingdetector.background.plist', 'w') as f:
        f.write(plist_content)

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    create_macos_app()
    create_launchd_plist()