"""
GUI package for Phishing Detector Desktop App
"""
from .main_window import PhishingDashboard
from .login_dialog import LoginDialog
from .settings_dialog import SettingsDialog
from .history_dialog import HistoryDialog
from .notification import NotificationManager
from .browser_setup_dialog import BrowserSetupDialog

__all__ = [
    'PhishingDashboard',
    'LoginDialog',
    'SettingsDialog',
    'HistoryDialog',
    'NotificationManager',
    'BrowserSetupDialog'
]