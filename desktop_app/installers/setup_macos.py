"""
macOS installer for Phishing Detector.

Builds a self-contained .app bundle with PyInstaller. Run from anywhere;
it chdir's into desktop_app/ itself.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DESKTOP_APP_DIR = Path(__file__).parent.parent
PROJECT_ROOT = DESKTOP_APP_DIR.parent


def create_macos_app():
    """Create the macOS .app bundle."""
    print("🔧 Creating macOS application...")

    nltk_data_dir = Path.home() / 'nltk_data'
    if not nltk_data_dir.exists():
        print(f"⚠️  {nltk_data_dir} not found -- run download_nltk_data.py first "
              f"so the bundled app has its NLTK data.")

    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [
    ('{PROJECT_ROOT / "src"}', 'src'),
    ('{PROJECT_ROOT / "models"}', 'models'),
    ('{PROJECT_ROOT / "config.py"}', '.'),
]
if {str(nltk_data_dir.exists())}:
    datas.append(('{nltk_data_dir}', 'nltk_data'))
datas += collect_data_files('en_core_web_sm')

# scipy has internal submodules (e.g. scipy._lib.array_api_compat.numpy.fft)
# that PyInstaller's static analysis doesn't always discover from a bare
# 'scipy' hidden import -- collect_submodules pulls in the full tree so
# sklearn/scipy imports don't fail at runtime with a missing-module error.
a = Analysis(
    ['main.py'],
    pathex=['{PROJECT_ROOT}'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'sklearn', 'numpy', 'nltk', 'spacy', 'en_core_web_sm',
        'cryptography', 'dns', 'dns.resolver',
        'pystray', 'PIL', 'plyer.platforms.macosx.notification',
        'requests', 'bs4',
    ] + collect_submodules('scipy'),
    hookspath=[],
    hooksconfig={{}},
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
    info_plist={{
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
        'NSHighResolutionCapable': True,
    }}
)
'''
    # LSUIElement is deliberately omitted: this app has a real dashboard
    # window, not just a menu-bar icon, so it should show up normally in
    # the Dock and Cmd-Tab switcher. A previous version set it to True,
    # which would have hidden the Dock icon and made the window hard to
    # find after opening the app.

    spec_path = DESKTOP_APP_DIR / 'phishing_detector_macos.spec'
    spec_path.write_text(spec_content)

    subprocess.run(
        [sys.executable, '-m', 'PyInstaller', '--clean', '-y', str(spec_path)],
        cwd=str(DESKTOP_APP_DIR),
        check=True,
    )

    app_path = DESKTOP_APP_DIR / 'dist' / 'PhishingDetector.app'

    # If the project lives on a non-native filesystem (exFAT/FAT32, e.g. an
    # external drive), macOS leaves AppleDouble '._*' shadow files alongside
    # every real file, including inside the freshly-built bundle. codesign
    # chokes on these ("Operation not permitted"), so PyInstaller's own
    # signing attempt can fail even though the app itself built fine. Strip
    # them and re-sign explicitly.
    for junk in app_path.rglob('._*'):
        junk.unlink()
    subprocess.run(
        ['codesign', '-s', '-', '--force', '--all-architectures', '--timestamp', '--deep', str(app_path)],
        check=True,
    )

    print(f"✅ macOS app created at: {app_path}")
    return app_path


def create_dmg(app_path):
    """Wrap the .app in a .dmg for a drag-to-Applications install experience."""
    if shutil.which('hdiutil') is None:
        print("⚠️  hdiutil not found (not on macOS?) -- skipping .dmg creation")
        return None

    # Stage on the system temp dir (APFS/HFS+), not wherever this project
    # happens to live -- if that's on an exFAT volume (e.g. an external
    # drive), symlinks and codesign-relevant metadata don't survive it and
    # both hdiutil and codesign fail with "Operation not permitted".
    with tempfile.TemporaryDirectory() as tmp:
        dmg_staging = Path(tmp) / 'dmg_staging'
        dmg_staging.mkdir()

        shutil.copytree(app_path, dmg_staging / 'PhishingDetector.app')
        os.symlink('/Applications', dmg_staging / 'Applications')

        dmg_path = DESKTOP_APP_DIR / 'dist' / 'PhishingDetector.dmg'
        if dmg_path.exists():
            dmg_path.unlink()

        print("🔧 Creating .dmg...")
        subprocess.run([
            'hdiutil', 'create', '-volname', 'Phishing Detector',
            '-srcfolder', str(dmg_staging), '-ov', '-format', 'UDZO',
            str(dmg_path)
        ], check=True)

    print(f"✅ .dmg created at: {dmg_path}")
    return dmg_path


def create_launchd_plist():
    """Create the launchd plist used for background/autostart mode (see
    permission_manager.setup_macos_autostart, which generates this same
    content at runtime once the user opts in -- this copy is just for
    reference/manual installation)."""
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

    plist_path = DESKTOP_APP_DIR / 'com.phishingdetector.background.plist'
    plist_path.write_text(plist_content)


if __name__ == "__main__":
    app_path = create_macos_app()
    create_dmg(app_path)
    create_launchd_plist()
