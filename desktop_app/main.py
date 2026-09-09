#!/usr/bin/env python3
"""
Phishing Detector Desktop Application
Cross-platform desktop app for real-time phishing detection with browser integration
"""
import sys
import os
import argparse
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load a Settings-configured Gemini API key into the environment before
# anything below (starting with browser_integration next, which pulls in
# predictor.py -> ai_domain_screening.py) gets a chance to import a module
# that reads GEMINI_API_KEY at import time -- gemini_analyzer.py's
# singleton and ai_domain_screening.py's AI_SCREENING_AVAILABLE flag are
# both fixed once at import, so this has to run first. An explicit
# environment variable, if one is already set, always wins over the saved
# (encrypted) key from Settings.
if not os.environ.get('GEMINI_API_KEY'):
    try:
        from desktop_app.backend.permission_manager import PermissionManager
        _pm = PermissionManager()
        _encrypted_key = _pm.permissions.get('gemini_api_key')
        if _encrypted_key:
            os.environ['GEMINI_API_KEY'] = _pm.decrypt_password(_encrypted_key)
    except Exception as e:
        print(f"⚠️ Could not load saved Gemini API key: {e}")

# Importing the predictor below (directly, or transitively via the backend
# modules) already patches SSL and downloads NLTK data as a side effect --
# see src/preprocessing.py -- so this file doesn't need its own copy.

# Try to import browser integration (optional)
try:
    from desktop_app.backend.browser_integration import browser_server
    BROWSER_INTEGRATION_AVAILABLE = True
except ImportError as e:
    BROWSER_INTEGRATION_AVAILABLE = False
    print(f"⚠️ Browser integration not available: {e}")

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    optional_missing = []
    
    # Required for core functionality
    try:
        import PIL
    except ImportError:
        optional_missing.append("Pillow")
    
    try:
        import pystray
    except ImportError:
        optional_missing.append("pystray")
    
    try:
        import plyer
    except ImportError:
        optional_missing.append("plyer")
    
    # Check for browser integration dependencies
    try:
        import Levenshtein
    except ImportError:
        optional_missing.append("python-Levenshtein")
    
    try:
        import whois
    except ImportError:
        optional_missing.append("python-whois")
    
    try:
        import tldextract
    except ImportError:
        optional_missing.append("tldextract")
    
    if optional_missing:
        print(f"⚠️ Optional dependencies missing: {', '.join(optional_missing)}")
        print("   Some features may be limited.")
        print("   Install with: pip install " + ' '.join(optional_missing))
    
    return len(missing) == 0

def create_icon_directories():
    """Create icon directories for browser extension"""
    icon_path = Path(__file__).parent / 'backend' / 'browser_extension' / 'icons'
    icon_path.mkdir(parents=True, exist_ok=True)
    
    # Create placeholder icons if they don't exist
    create_placeholder_icons(icon_path)

def create_placeholder_icons(icon_path):
    """Create simple placeholder icons using PIL if available"""
    try:
        from PIL import Image, ImageDraw
        
        sizes = [16, 48, 128]
        for size in sizes:
            icon_file = icon_path / f'icon{size}.png'
            if not icon_file.exists():
                # Create a simple shield icon
                img = Image.new('RGB', (size, size), color='white')
                draw = ImageDraw.Draw(img)
                
                # Draw shield shape
                margin = size // 8
                draw.rectangle([margin, margin, size-margin, size-margin], 
                             fill='#4CAF50', outline='#2E7D32', width=2)
                
                # Draw "PD" text
                try:
                    from PIL import ImageFont
                    font = ImageFont.load_default()
                    draw.text((size//3, size//3), "PD", fill='white', font=font)
                except:
                    pass
                
                img.save(icon_file)
                print(f"✅ Created placeholder icon: {icon_file}")
    except ImportError:
        print("⚠️ PIL not available - skipping icon creation")
        print("   You can download icons manually from:")
        print(f"   {icon_path}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Phishing Detector Desktop App')
    parser.add_argument('--background', action='store_true', 
                       help='Run in background mode (no GUI)')
    parser.add_argument('--minimized', action='store_true',
                       help='Start minimized to system tray')
    parser.add_argument('--no-tray', action='store_true',
                       help='Disable system tray')
    parser.add_argument('--no-browser', action='store_true',
                       help='Disable browser integration')
    parser.add_argument('--install-extension', action='store_true',
                       help='Install browser extension files')
    
    args = parser.parse_args()
    
    # Create icon directories
    create_icon_directories()
    
    # Check dependencies
    check_dependencies()
    
    # Handle extension installation
    if args.install_extension:
        install_browser_extension()
        return
    
    # Start browser integration server (unless disabled)
    browser_server_started = False
    if not args.no_browser and BROWSER_INTEGRATION_AVAILABLE:
        try:
            browser_server.start()
            browser_server_started = True
            print("🌐 Browser integration enabled")
        except Exception as e:
            print(f"⚠️ Failed to start browser integration: {e}")
    
    if args.background:
        run_background(browser_server_started)
    else:
        run_gui(args.minimized, args.no_tray, browser_server_started)

def install_browser_extension():
    """Print instructions for installing browser extension"""
    extension_path = Path(__file__).parent / 'backend' / 'browser_extension'
    
    print("\n" + "="*60)
    print("📦 Browser Extension Installation Instructions")
    print("="*60)
    print(f"\nExtension files are located at:")
    print(f"  {extension_path}")
    print("\nTo install in Chrome/Edge/Brave:")
    print("  1. Open Chrome and go to chrome://extensions/")
    print("  2. Enable 'Developer mode' (toggle in top right)")
    print("  3. Click 'Load unpacked'")
    print(f"  4. Select the folder: {extension_path}")
    print("\nTo install in Firefox:")
    print("  1. Open Firefox and go to about:debugging")
    print("  2. Click 'This Firefox'")
    print("  3. Click 'Load Temporary Add-on'")
    print(f"  4. Select the manifest.json file in: {extension_path}")
    print("\n" + "="*60)

def run_background(browser_integration=False):
    """Run in background mode (no GUI)"""
    print("🔄 Running Phishing Detector in background...")
    if browser_integration:
        print("   • Browser integration active")
    print("   • Press Ctrl+C to stop")
    
    try:
        from desktop_app.backend.permission_manager import PermissionManager
        from desktop_app.backend.gmail_watcher import GmailWatcher
        from desktop_app.backend.monitor import EmailMonitor
        
        monitor = EmailMonitor()
        monitor.start()
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            monitor.stop()
            if browser_integration:
                browser_server.stop()
            
    except ImportError as e:
        print(f"❌ Failed to import backend modules: {e}")
        sys.exit(1)

def run_gui(minimized=False, no_tray=False, browser_integration=False):
    """Run GUI mode"""
    try:
        from desktop_app.frontend.gui.main_window import PhishingDashboard
        
        dashboard = PhishingDashboard()
        
        # Connect browser integration if available
        if browser_integration:
            dashboard.browser_server = browser_server
            
            # IMPORTANT: Set up callback to forward browser messages to dashboard
            def on_browser_event(data):
                print(f"📨 Browser event received in main: {data.get('type')}")
                # Forward to dashboard's on_email_detected method
                dashboard.on_email_detected(data)
            
            browser_server.callback = on_browser_event
            print("   ✅ Browser integration connected with callback")
        
        # Disable tray if requested
        if no_tray and hasattr(dashboard, 'notification_manager'):
            dashboard.notification_manager.has_tray = False
        
        if minimized:
            # Hide main window, show only tray
            dashboard.root.withdraw()
        
        print("✅ Dashboard ready!")
        dashboard.run()
        
    except ImportError as e:
        print(f"❌ Failed to import GUI modules: {e}")
        print("\nPlease ensure tkinter is installed:")
        print("  • macOS: Usually comes with Python")
        print("  • Linux: sudo apt-get install python3-tk")
        print("  • Windows: Reinstall Python with 'tcl/tk and IDLE' option")
    except Exception as e:
        print(f"❌ Error starting GUI: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if browser_integration:
            browser_server.stop()

if __name__ == "__main__":
    main()