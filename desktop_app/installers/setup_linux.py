"""
Linux packaging for Phishing Detector.

Builds a single-file executable with PyInstaller and writes an install.sh
that copies it into place, registers a .desktop launcher, and (optionally)
an XDG autostart entry -- no systemd unit needed, works across
GNOME/KDE/XFCE.

NOTE: written by pattern, not executed/tested here -- this development
environment is macOS. Test on an actual Linux machine or VM before
trusting the output.
"""
import subprocess
import sys
from pathlib import Path

DESKTOP_APP_DIR = Path(__file__).parent.parent
PROJECT_ROOT = DESKTOP_APP_DIR.parent

INSTALL_SH = '''#!/bin/sh
# Installs Phishing Detector for the current user (no root required).
set -e

INSTALL_DIR="$HOME/.local/share/phishing-detector"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp -r "$SCRIPT_DIR/dist/PhishingDetector" "$INSTALL_DIR/PhishingDetector"
chmod +x "$INSTALL_DIR/PhishingDetector"
ln -sf "$INSTALL_DIR/PhishingDetector" "$BIN_DIR/phishing-detector"

cat > "$DESKTOP_DIR/phishingdetector.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Phishing Detector
Comment=Real-time phishing email detection
Exec=$INSTALL_DIR/PhishingDetector
Terminal=false
Categories=Utility;Security;
EOF
chmod +x "$DESKTOP_DIR/phishingdetector.desktop"

echo "Installed. Launch from your applications menu, or run: phishing-detector"
echo "(Make sure $BIN_DIR is on your PATH, or launch via the applications menu.)"
echo ""
echo "To start automatically at login, open the app and enable"
echo "'Background Running' from the Permissions menu."
'''


def create_linux_build():
    """PyInstaller onefile build for Linux."""
    print("🔧 Creating Linux executable...")

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
        'pystray', 'PIL', 'plyer.platforms.linux.notification',
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
    console=False,
)
'''
    spec_path = DESKTOP_APP_DIR / 'phishing_detector_linux.spec'
    spec_path.write_text(spec_content)

    subprocess.run(
        [sys.executable, '-m', 'PyInstaller', '--clean', '-y', str(spec_path)],
        cwd=str(DESKTOP_APP_DIR),
        check=True,
    )

    exe_path = DESKTOP_APP_DIR / 'dist' / 'PhishingDetector'
    print(f"✅ Linux executable created at: {exe_path}")
    return exe_path


def write_install_script():
    install_path = DESKTOP_APP_DIR / 'install.sh'
    install_path.write_text(INSTALL_SH)
    install_path.chmod(0o755)
    print(f"✅ install.sh written to: {install_path}")
    return install_path


if __name__ == "__main__":
    create_linux_build()
    write_install_script()
    print("\nNOTE: this was written by pattern on macOS and has not been "
          "executed on Linux. Test dist/PhishingDetector and install.sh on "
          "an actual Linux machine or VM before shipping.")
