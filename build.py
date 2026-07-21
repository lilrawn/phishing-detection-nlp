#!/usr/bin/env python3
"""
Top-level build script: runs the platform-appropriate installer build, then
assembles the final distributable folder -- the built app/installer plus
browser_extensions/ and README.md side by side -- and zips it up as
PhishingDetector-<OS>.zip.

Usage: python build.py
"""
import platform
import shutil
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DESKTOP_APP_DIR = PROJECT_ROOT / 'desktop_app'
DIST_DIR = PROJECT_ROOT / 'dist'


def clean_dist():
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()


def build_macos():
    sys.path.insert(0, str(DESKTOP_APP_DIR / 'installers'))
    import setup_macos
    app_path = setup_macos.create_macos_app()
    dmg_path = setup_macos.create_dmg(app_path)
    return [p for p in (dmg_path, app_path) if p and p.exists()][:1] or [app_path]


def build_windows():
    sys.path.insert(0, str(DESKTOP_APP_DIR / 'installers'))
    import setup_windows
    dist_dir = setup_windows.create_windows_installer()
    setup_windows.write_inno_setup_script()
    # The compiled installer (if ISCC ran) lives under desktop_app/Output/;
    # otherwise ship the raw PyInstaller COLLECT output plus the .iss script
    # for the user to compile themselves on a Windows machine.
    output_exe = DESKTOP_APP_DIR / 'Output' / 'PhishingDetector-Setup.exe'
    if output_exe.exists():
        return [output_exe]
    return [dist_dir, DESKTOP_APP_DIR / 'installer_windows.iss']


def build_linux():
    sys.path.insert(0, str(DESKTOP_APP_DIR / 'installers'))
    import setup_linux
    exe_path = setup_linux.create_linux_build()
    install_script = setup_linux.write_install_script()
    return [exe_path, install_script]


BUILDERS = {
    'Darwin': ('macos', build_macos),
    'Windows': ('windows', build_windows),
    'Linux': ('linux', build_linux),
}


def assemble_distribution(os_label, built_paths):
    """Copy the built app + browser_extensions/ + README.md into dist/PhishingDetector-<os>/"""
    stage_dir = DIST_DIR / f'PhishingDetector-{os_label}'
    stage_dir.mkdir(parents=True)

    for path in built_paths:
        dest = stage_dir / path.name
        if path.is_dir():
            shutil.copytree(path, dest)
        else:
            shutil.copy2(path, dest)

    shutil.copytree(PROJECT_ROOT / 'browser_extensions', stage_dir / 'browser_extensions')

    readme_src = PROJECT_ROOT / 'README.md'
    if readme_src.exists():
        shutil.copy2(readme_src, stage_dir / 'README.md')

    return stage_dir


def zip_distribution(stage_dir, os_label):
    zip_path = DIST_DIR / f'PhishingDetector-{os_label}.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in stage_dir.rglob('*'):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(DIST_DIR))
    return zip_path


def main():
    os_name = platform.system()
    if os_name not in BUILDERS:
        print(f"❌ Unsupported OS for building: {os_name}")
        sys.exit(1)

    os_label, builder = BUILDERS[os_name]
    print(f"🚀 Building Phishing Detector for {os_label}...")

    clean_dist()
    built_paths = builder()

    print(f"\n📦 Assembling distribution folder...")
    stage_dir = assemble_distribution(os_label, built_paths)

    print(f"🗜️  Zipping...")
    zip_path = zip_distribution(stage_dir, os_label)

    print(f"\n✅ Done: {zip_path}")


if __name__ == "__main__":
    main()
