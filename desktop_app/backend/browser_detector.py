"""
Detects installed browsers and helps the user load the extension into each
one. Browsers block silently installing extensions outside their stores, so
the most we can automate is: find the browser, open its extensions page,
and put the folder path on the clipboard -- the user still clicks
"Load unpacked" themselves, once per browser.
"""
import platform
import shutil
import subprocess
import sys
from pathlib import Path

EXTENSIONS_PAGE_URLS = {
    'chrome': 'chrome://extensions/',
    'brave': 'brave://extensions/',
    'edge': 'edge://extensions/',
    'firefox': 'about:debugging#/runtime/this-firefox',
}

# macOS .app bundle names, relative to /Applications or ~/Applications
_MACOS_APPS = {
    'chrome': 'Google Chrome.app',
    'brave': 'Brave Browser.app',
    'edge': 'Microsoft Edge.app',
    'firefox': 'Firefox.app',
}

# Windows executables, checked under Program Files / Program Files (x86) / LOCALAPPDATA
_WINDOWS_PATHS = {
    'chrome': [r'Google\Chrome\Application\chrome.exe'],
    'brave': [r'BraveSoftware\Brave-Browser\Application\brave.exe'],
    'edge': [r'Microsoft\Edge\Application\msedge.exe'],
    'firefox': [r'Mozilla Firefox\firefox.exe'],
}

# Linux binary names, looked up on PATH
_LINUX_BINARIES = {
    'chrome': ['google-chrome', 'google-chrome-stable'],
    'brave': ['brave-browser', 'brave'],
    'edge': ['microsoft-edge', 'microsoft-edge-stable'],
    'firefox': ['firefox'],
}


def _find_macos_app(browser):
    app_name = _MACOS_APPS[browser]
    for base in (Path('/Applications'), Path.home() / 'Applications'):
        app_path = base / app_name
        if app_path.exists():
            exe = app_path / 'Contents' / 'MacOS'
            if exe.exists():
                candidates = list(exe.iterdir())
                if candidates:
                    return str(candidates[0])
    return None


def _find_windows_exe(browser):
    import os
    program_files = [
        os.environ.get('ProgramFiles', r'C:\Program Files'),
        os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
        os.environ.get('LOCALAPPDATA', ''),
    ]
    for rel_path in _WINDOWS_PATHS[browser]:
        for base in program_files:
            if not base:
                continue
            candidate = Path(base) / rel_path
            if candidate.exists():
                return str(candidate)
    return None


def _find_linux_binary(browser):
    for name in _LINUX_BINARIES[browser]:
        found = shutil.which(name)
        if found:
            return found
    return None


def detect_installed_browsers():
    """Return {browser_name: executable_path} for every browser found installed."""
    os_name = platform.system()
    finder = {
        'Darwin': _find_macos_app,
        'Windows': _find_windows_exe,
        'Linux': _find_linux_binary,
    }.get(os_name)

    if finder is None:
        return {}

    found = {}
    for browser in EXTENSIONS_PAGE_URLS:
        path = finder(browser)
        if path:
            found[browser] = path
    return found


def open_extensions_page(browser, executable_path):
    """Launch the given browser directly at its extensions-management page."""
    url = EXTENSIONS_PAGE_URLS[browser]
    try:
        subprocess.Popen([executable_path, url])
        return True
    except OSError as e:
        print(f"⚠️ Could not launch {browser}: {e}")
        return False


def get_extension_folder(browser):
    """
    Path to the browser_extensions/<browser> folder to load. Looks next to
    the running executable first (the shipped, packaged layout), then falls
    back to the project root (running from source in development).
    """
    if getattr(sys, 'frozen', False):
        candidate = Path(sys.executable).parent / 'browser_extensions' / browser
        if candidate.exists():
            return candidate

    project_root = Path(__file__).parent.parent.parent
    return project_root / 'browser_extensions' / browser


if __name__ == "__main__":
    browsers = detect_installed_browsers()
    if not browsers:
        print("No supported browsers detected.")
    for name, path in browsers.items():
        print(f"{name}: {path}")
        print(f"  extension folder: {get_extension_folder(name)}")
