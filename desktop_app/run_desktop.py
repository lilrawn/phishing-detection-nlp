#!/usr/bin/env python3
"""
Launcher for Phishing Detector Desktop App with error handling
"""
import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Main entry point with error handling"""
    try:
        # Import main app
        from desktop_app.main import main as app_main
        app_main()
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nPossible solutions:")
        print("1. Make sure you're running from the correct directory")
        print("2. Check that all dependencies are installed:")
        print("   pip install pystray Pillow plyer pyobjus")
        print("\nCurrent Python path:")
        for p in sys.path:
            print(f"  • {p}")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        traceback.print_exc()
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()