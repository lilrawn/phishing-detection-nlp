"""
Windows packaging for Phishing Detector.

Builds a PyInstaller .exe, then (if Inno Setup's ISCC is available) wraps
it into a real "Next, Next, Finish" installer via installer_windows.iss.

NOTE: written by pattern, not executed/tested here -- this development
environment is macOS. Test on an actual Windows machine before trusting
the output; ISCC.exe specifically cannot run outside Windows.
"""
import shutil
import subprocess
import sys
from pathlib import Path

DESKTOP_APP_DIR = Path(__file__).parent.parent
PROJECT_ROOT = DESKTOP_APP_DIR.parent

INNO_SETUP_SCRIPT = '''; Inno Setup script for Phishing Detector.
; Compile with ISCC.exe (Inno Setup Compiler) on Windows:
;   ISCC installer_windows.iss

#define MyAppName "Phishing Detector"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Liron Nyambu"
#define MyAppExeName "PhishingDetector.exe"

[Setup]
AppId={{B6C9E4F0-6C1A-4E9C-9F1A-PHISHDETECT01}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=PhishingDetector-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start automatically when Windows starts"; GroupDescription: "Startup"

[Files]
Source: "dist\\PhishingDetector\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\\Microsoft\\Windows\\CurrentVersion\\Run"; \\
    ValueType: string; ValueName: "PhishingDetector"; \\
    ValueData: """{app}\\{#MyAppExeName}"" --background"; Tasks: autostart

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
'''


def create_windows_installer():
    """PyInstaller build -- produces dist/PhishingDetector/PhishingDetector.exe."""
    print("🔧 Creating Windows executable...")

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
        'pystray', 'PIL', 'plyer.platforms.win.notification',
        'requests', 'bs4', 'win32api', 'win32con',
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
    [],
    exclude_binaries=True,
    name='PhishingDetector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='frontend/resources/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='PhishingDetector',
)
'''

    spec_path = DESKTOP_APP_DIR / 'phishing_detector_windows.spec'
    spec_path.write_text(spec_content)

    subprocess.run(
        [sys.executable, '-m', 'PyInstaller', '--clean', '-y', str(spec_path)],
        cwd=str(DESKTOP_APP_DIR),
        check=True,
    )

    dist_dir = DESKTOP_APP_DIR / 'dist' / 'PhishingDetector'
    print(f"✅ Windows build created at: {dist_dir}")
    return dist_dir


def write_inno_setup_script():
    iss_path = DESKTOP_APP_DIR / 'installer_windows.iss'
    iss_path.write_text(INNO_SETUP_SCRIPT)
    print(f"✅ Inno Setup script written to: {iss_path}")

    iscc = shutil.which('ISCC')
    if iscc:
        print("🔧 Compiling installer with ISCC...")
        subprocess.run([iscc, str(iss_path)], cwd=str(DESKTOP_APP_DIR), check=True)
        print(f"✅ Installer created at: {DESKTOP_APP_DIR / 'Output' / 'PhishingDetector-Setup.exe'}")
    else:
        print("ℹ️  ISCC (Inno Setup Compiler) not found on PATH -- that's expected "
              "unless this is running on Windows with Inno Setup installed. "
              f"Compile {iss_path.name} manually with Inno Setup to produce the final installer.")

    return iss_path


if __name__ == "__main__":
    create_windows_installer()
    write_inno_setup_script()
    print("\nNOTE: this was written by pattern on macOS and has not been "
          "executed on Windows. Test dist/PhishingDetector/PhishingDetector.exe "
          "and the compiled installer on an actual Windows machine before shipping.")
