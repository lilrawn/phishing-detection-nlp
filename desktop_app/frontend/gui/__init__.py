"""
GUI package for Phishing Detector Desktop App
"""
from .main_window import PhishingDashboard
from .login_dialog import LoginDialog
from .settings_dialog import SettingsDialog
from .history_dialog import HistoryDialog
from .notification import NotificationManager

__all__ = [
    'PhishingDashboard',
    'LoginDialog', 
    'SettingsDialog',
    'HistoryDialog',
    'NotificationManager'
]