"""
Backend package for Phishing Detector Desktop App
"""
from .permission_manager import PermissionManager
from .gmail_watcher import GmailWatcher
from .browser_watcher import BrowserWatcher
from .monitor import EmailMonitor

__all__ = [
    'PermissionManager',
    'GmailWatcher', 
    'BrowserWatcher',
    'EmailMonitor'
]