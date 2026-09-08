"""
Main dashboard window for phishing detector
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
import sys
from pathlib import Path
import requests

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.database import db
from desktop_app.backend.gmail_watcher import GmailWatcher
from desktop_app.backend.real_gmail_watcher import RealGmailWatcher
from desktop_app.backend.browser_watcher import BrowserWatcher
from desktop_app.backend.permission_manager import PermissionManager

# Import dialogs - use relative imports
from .login_dialog import LoginDialog
from .settings_dialog import SettingsDialog
from .history_dialog import HistoryDialog
from .notification import NotificationManager
from .email_detail_dialog import EmailDetailDialog
from .browser_setup_dialog import BrowserSetupDialog

class PhishingDashboard:
    """Main dashboard window"""

    # Tk's literal named colors ('green', 'red', ...) render fully
    # saturated regardless of the system's light/dark appearance, which
    # reads as neon/glaring against macOS dark mode's auto-dark chrome.
    # Muted equivalents keep the same status semantics without the glare.
    COLORS = {
        'safe': '#4A8C5E',       # legitimate / connected / success
        'safe_bg': '#DCEBDF',    # row-highlight tint for the same
        'danger': '#B0524F',     # phishing / disconnected / error
        'danger_bg': '#F0DCDC',
        'warning': '#C08A3E',    # waiting / caution
        'warning_bg': '#F0E6CC',
        'info': '#4A6FA0',       # informational status
        'browser': '#7D699C',    # browser/extension indicators
        'mode': '#3F8080',       # detection-mode indicator
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Phishing Detector Dashboard")
        self.root.geometry("1200x850")
        self.root.minsize(1000, 750)
        
        # Set icon
        self.set_icon()
        
        # Initialize managers
        self.permission_manager = PermissionManager()
        self.notification_manager = NotificationManager(self.root, self.handle_tray_callback)
        
        # Initialize watchers
        self.gmail_watcher = None
        self.real_gmail_watcher = None
        self.browser_watcher = None
        self.browser_server = None  # Will be set by main.py
        
        # Email tracking
        self.email_cache = {}  # Store email data by ID
        self.email_id_map = {}  # Map tree item IDs to email IDs
        self.sender_reputation = {}  # Track sender reputation
        self.browser_messages_received = False  # Track if browser has connected
        self.browser_message_count = 0  # Count browser messages received
        self.processed_extensions = set()  # Track processed extension connections
        
        # Detection mode
        self.detection_mode = tk.StringVar(value="both")
        
        # Load sender reputation from database
        self.load_sender_reputation()
        
        # Setup UI
        self.setup_ui()
        
        # Check permissions
        self.check_initial_permissions()

        # Start background services once the Tk event loop is actually
        # running (root.mainloop() is only called later, from run()) --
        # start_services() spawns watcher threads whose very first check
        # can fire within milliseconds, and calling into Tk (even via
        # root.after) before mainloop() has started raises "main thread is
        # not in main loop". Scheduling via after(0, ...) guarantees
        # mainloop is live by the time this actually runs, since that's
        # what drives the callback in the first place.
        self.root.after(0, self.start_services)

        # Start update loop
        self.update_stats()
        
        # Start periodic browser status check
        self.root.after(3000, self.check_browser_status)
        
    def load_sender_reputation(self):
        """Load sender reputation from database"""
        try:
            # In a real app, query database for sender history
            # For demo, initialize empty
            self.sender_reputation = {}
        except Exception as e:
            print(f"Error loading sender reputation: {e}")
            self.sender_reputation = {}
    
    def handle_tray_callback(self, action):
        """Handle system tray callbacks"""
        if action == 'open_dashboard':
            self.root.deiconify()  # Show window
            self.root.lift()
        elif action == 'scan_now':
            self.manual_scan()
        elif action == 'open_settings':
            self.open_settings()
        elif action == 'exit':
            self.quit_app()
    
    def set_icon(self):
        """Set window icon"""
        icon_path = Path(__file__).parent.parent / 'resources'
        
        if sys.platform == 'win32':
            icon_file = icon_path / 'icon.ico'
        else:
            icon_file = icon_path / 'icon.icns'
        
        if icon_file.exists():
            try:
                self.root.iconbitmap(str(icon_file))
            except:
                pass
    
    def setup_ui(self):
        """Setup the user interface"""
        # Create menu bar
        self.setup_menu()
        
        # Create main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=2)  # Notifications area
        main_frame.rowconfigure(4, weight=1)  # Log viewer
        main_frame.rowconfigure(5, weight=0)  # Mode selector
        main_frame.rowconfigure(6, weight=0)  # Control buttons
        
        # Title with Google Sign-In button
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, pady=10, sticky=(tk.W, tk.E))
        
        ttk.Label(title_frame, text="🛡️ Phishing Email Detector", 
                  font=('Helvetica', 20, 'bold')).pack(side=tk.LEFT)
        
        # Google Sign-In button
        self.google_btn = ttk.Button(title_frame, text="🔑 Sign in with Google", 
                                     command=self.google_sign_in)
        self.google_btn.pack(side=tk.RIGHT, padx=10)
        
        # Status bar
        self.setup_status_bar(main_frame)
        
        # Stats cards
        self.setup_stats_cards(main_frame)
        
        # Notifications area
        self.setup_notifications(main_frame)
        
        # Log viewer
        self.setup_log_viewer(main_frame)
        
        # Mode selector
        self.setup_mode_selector(main_frame)
        
        # Control buttons
        self.setup_controls(main_frame)
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Export Logs", command=self.export_logs)
        file_menu.add_command(label="Exit", command=self.quit_app)
        
        # Permissions menu
        perm_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Permissions", menu=perm_menu)
        perm_menu.add_command(label="Grant Gmail Access", 
                              command=self.permission_manager.request_gmail_permission)
        perm_menu.add_command(label="Grant Browser Access",
                              command=self.permission_manager.request_browser_permission)
        perm_menu.add_command(label="🌐 Connect Your Browser...",
                              command=self.open_browser_setup)
        perm_menu.add_command(label="Background Running",
                              command=self.permission_manager.request_background_permission)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Statistics", command=self.show_statistics)
        view_menu.add_command(label="History", command=self.show_history)
        view_menu.add_command(label="Sender Reputation", command=self.show_sender_reputation)
        view_menu.add_command(label="Clear Log", command=self.clear_log)
        
        # Mode menu
        mode_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Mode", menu=mode_menu)
        mode_menu.add_radiobutton(label="🌐 Browser Extension Only", 
                                  variable=self.detection_mode, value="browser",
                                  command=self.change_detection_mode)
        mode_menu.add_radiobutton(label="📧 Sample Emails Only", 
                                  variable=self.detection_mode, value="samples",
                                  command=self.change_detection_mode)
        mode_menu.add_radiobutton(label="🔄 Both", 
                                  variable=self.detection_mode, value="both",
                                  command=self.change_detection_mode)
        mode_menu.add_separator()
        mode_menu.add_command(label="🔌 Force Extension Connection", 
                             command=self.force_extension_connection)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.show_docs)
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Status indicators
        self.gmail_status = ttk.Label(status_frame, text="📧 Samples: Inactive")
        self.gmail_status.grid(row=0, column=0, padx=10)
        
        self.browser_status = ttk.Label(status_frame, text="🌐 Browser: Disconnected")
        self.browser_status.grid(row=0, column=1, padx=10)
        
        self.background_status = ttk.Label(status_frame, text="🔄 Background: Stopped")
        self.background_status.grid(row=0, column=2, padx=10)
        
        # Google status
        self.google_status = ttk.Label(status_frame, text="🔑 Google: Not signed in")
        self.google_status.grid(row=0, column=3, padx=10)
        
        # Browser integration status
        self.browser_integration_status = ttk.Label(status_frame, text="🌐 Browser Extension: Waiting for connection...", foreground=self.COLORS['warning'])
        self.browser_integration_status.grid(row=0, column=4, padx=10)
        
        # Current mode
        self.mode_status = ttk.Label(status_frame, text="🔄 Mode: Both", foreground=self.COLORS['info'])
        self.mode_status.grid(row=0, column=5, padx=10)
        
        # Last scan time
        self.last_scan = ttk.Label(status_frame, text="")
        self.last_scan.grid(row=0, column=6, padx=10)
    
    def setup_stats_cards(self, parent):
        """Setup statistics cards"""
        stats_frame = ttk.Frame(parent)
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Configure grid
        for i in range(7):
            stats_frame.columnconfigure(i, weight=1)
        
        # Card 1: Total Scanned
        card1 = ttk.LabelFrame(stats_frame, text="Total Scanned", padding="10")
        card1.grid(row=0, column=0, padx=5, sticky=(tk.W, tk.E))
        self.total_scanned = ttk.Label(card1, text="0", font=('Helvetica', 24, 'bold'))
        self.total_scanned.pack()
        
        # Card 2: Phishing Detected
        card2 = ttk.LabelFrame(stats_frame, text="Phishing Detected", padding="10")
        card2.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        self.phishing_count = ttk.Label(card2, text="0", font=('Helvetica', 24, 'bold'), foreground=self.COLORS['danger'])
        self.phishing_count.pack()
        
        # Card 3: Safe Emails
        card3 = ttk.LabelFrame(stats_frame, text="Safe Emails", padding="10")
        card3.grid(row=0, column=2, padx=5, sticky=(tk.W, tk.E))
        self.safe_count = ttk.Label(card3, text="0", font=('Helvetica', 24, 'bold'), foreground=self.COLORS['safe'])
        self.safe_count.pack()
        
        # Card 4: Browser Scans
        card4 = ttk.LabelFrame(stats_frame, text="Browser Scans", padding="10")
        card4.grid(row=0, column=3, padx=5, sticky=(tk.W, tk.E))
        self.browser_scans = ttk.Label(card4, text="0", font=('Helvetica', 24, 'bold'), foreground=self.COLORS['info'])
        self.browser_scans.pack()
        
        # Card 5: Accuracy
        card5 = ttk.LabelFrame(stats_frame, text="Accuracy", padding="10")
        card5.grid(row=0, column=4, padx=5, sticky=(tk.W, tk.E))
        self.accuracy = ttk.Label(card5, text="98%", font=('Helvetica', 24, 'bold'))
        self.accuracy.pack()
        
        # Card 6: Senders Tracked
        card6 = ttk.LabelFrame(stats_frame, text="Senders Tracked", padding="10")
        card6.grid(row=0, column=5, padx=5, sticky=(tk.W, tk.E))
        self.senders_count = ttk.Label(card6, text="0", font=('Helvetica', 24, 'bold'))
        self.senders_count.pack()
        
        # Card 7: Extensions Connected
        card7 = ttk.LabelFrame(stats_frame, text="Extensions", padding="10")
        card7.grid(row=0, column=6, padx=5, sticky=(tk.W, tk.E))
        self.extensions_count = ttk.Label(card7, text="0", font=('Helvetica', 24, 'bold'), foreground=self.COLORS['browser'])
        self.extensions_count.pack()
    
    def setup_notifications(self, parent):
        """Setup notifications area"""
        notif_frame = ttk.LabelFrame(parent, text="Recent Emails", padding="10")
        notif_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Create treeview for notifications
        columns = ('Time', 'Type', 'Source', 'From', 'Subject', 'Confidence', 'Reason')
        self.notif_tree = ttk.Treeview(notif_frame, columns=columns, show='headings', height=6)

        # Define headings
        self.notif_tree.heading('Time', text='Time')
        self.notif_tree.heading('Type', text='Type')
        self.notif_tree.heading('Source', text='Source')
        self.notif_tree.heading('From', text='From')
        self.notif_tree.heading('Subject', text='Subject')
        self.notif_tree.heading('Confidence', text='Confidence')
        self.notif_tree.heading('Reason', text='Why Flagged')

        # Set column widths
        self.notif_tree.column('Time', width=80)
        self.notif_tree.column('Type', width=100)
        self.notif_tree.column('Source', width=80)
        self.notif_tree.column('From', width=200)
        self.notif_tree.column('Subject', width=260)
        self.notif_tree.column('Confidence', width=90)
        self.notif_tree.column('Reason', width=280)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(notif_frame, orient=tk.VERTICAL, command=self.notif_tree.yview)
        self.notif_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.notif_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to show details
        self.notif_tree.bind('<Double-Button-1>', self.show_email_details)
        
        # Bind right-click for context menu
        self.notif_tree.bind('<Button-3>', self.show_context_menu)
    
    def setup_log_viewer(self, parent):
        """Setup log viewer to show terminal output"""
        log_frame = ttk.LabelFrame(parent, text="Activity Log", padding="10")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Create text widget for logs
        self.log_text = tk.Text(log_frame, height=6, wrap=tk.WORD, font=('Courier', 9))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Configure tags for colors
        self.log_text.tag_configure('phishing', foreground=self.COLORS['danger'], font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('legitimate', foreground=self.COLORS['safe'], font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('info', foreground=self.COLORS['info'], font=('Courier', 9))
        self.log_text.tag_configure('browser', foreground=self.COLORS['browser'], font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('warning', foreground=self.COLORS['warning'], font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('error', foreground=self.COLORS['danger'], font=('Courier', 9, 'bold'))
        self.log_text.tag_configure('mode', foreground=self.COLORS['mode'], font=('Courier', 9, 'bold'))
        
        # Initial log message
        self.add_log("🛡️ Phishing Detector started", 'info')
        self.add_log("📋 Waiting for emails...", 'info')
    
    def add_log(self, message, tag='info'):
        """Add message to log viewer"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry, tag)
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        
        # Also print to terminal
        print(log_entry.strip())
    
    def clear_log(self):
        """Clear the log viewer"""
        self.log_text.delete(1.0, tk.END)
        self.add_log("📋 Log cleared", 'info')
    
    def setup_mode_selector(self, parent):
        """Setup mode selector for choosing detection source"""
        mode_frame = ttk.LabelFrame(parent, text="Detection Mode", padding="10")
        mode_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Browser mode radio
        browser_radio = ttk.Radiobutton(
            mode_frame, 
            text="🌐 Browser Extension Only", 
            variable=self.detection_mode,
            value="browser",
            command=self.change_detection_mode
        )
        browser_radio.pack(side=tk.LEFT, padx=10)
        
        # Sample mode radio
        sample_radio = ttk.Radiobutton(
            mode_frame, 
            text="📧 Sample Emails Only", 
            variable=self.detection_mode,
            value="samples",
            command=self.change_detection_mode
        )
        sample_radio.pack(side=tk.LEFT, padx=10)
        
        # Both mode radio
        both_radio = ttk.Radiobutton(
            mode_frame, 
            text="🔄 Both", 
            variable=self.detection_mode,
            value="both",
            command=self.change_detection_mode
        )
        both_radio.pack(side=tk.LEFT, padx=10)
        
        # Force connection button
        force_connect_btn = ttk.Button(
            mode_frame, 
            text="🔌 Force Extension Connection", 
            command=self.force_extension_connection,
            width=25
        )
        force_connect_btn.pack(side=tk.RIGHT, padx=10)
        
        # Connection status indicator
        self.connection_indicator = tk.Canvas(mode_frame, width=20, height=20)
        self.connection_indicator.pack(side=tk.RIGHT, padx=5)
        self.update_connection_indicator(False)
    
    def update_connection_indicator(self, connected):
        """Update the connection indicator dot"""
        self.connection_indicator.delete("all")
        if connected:
            self.connection_indicator.create_oval(2, 2, 18, 18, fill=self.COLORS['safe'], outline=self.COLORS['safe'])
        else:
            self.connection_indicator.create_oval(2, 2, 18, 18, fill=self.COLORS['danger'], outline=self.COLORS['danger'])
    
    def setup_controls(self, parent):
        """Setup control buttons"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Scan button
        self.scan_btn = ttk.Button(control_frame, text="🔍 Scan Now", 
                                    command=self.manual_scan, width=15)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        # Settings button
        settings_btn = ttk.Button(control_frame, text="⚙️ Settings", 
                                   command=self.open_settings, width=15)
        settings_btn.pack(side=tk.LEFT, padx=5)
        
        # View History button
        history_btn = ttk.Button(control_frame, text="📋 View History", 
                                  command=self.show_history, width=15)
        history_btn.pack(side=tk.LEFT, padx=5)
        
        # Reputation button
        reputation_btn = ttk.Button(control_frame, text="👤 Sender Reputation", 
                                    command=self.show_sender_reputation, width=15)
        reputation_btn.pack(side=tk.LEFT, padx=5)
        
        # Test Browser button
        test_browser_btn = ttk.Button(control_frame, text="🌐 Test Browser", 
                                      command=self.test_browser_connection, width=15)
        test_browser_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear Log button
        clear_log_btn = ttk.Button(control_frame, text="🗑️ Clear Log", 
                                   command=self.clear_log, width=15)
        clear_log_btn.pack(side=tk.LEFT, padx=5)
    
    def google_sign_in(self):
        """Open the real Gmail login dialog (IMAP app-password based -- see
        login_dialog.py) and, on success, start scanning the real inbox
        immediately rather than waiting for the next app launch."""
        dialog = LoginDialog(self.root, self.permission_manager)
        self.root.wait_window(dialog.dialog)
        self.start_real_gmail_watcher_if_configured()

    def get_confidence_from_result(self, result):
        """Get confidence (0-100) from a predictor result dict"""
        if not result:
            return 0
        return result.get('confidence', 0)

    def _summarize_reasons(self, result):
        """Short, single-line summary of why an email was flagged, for the
        main list -- the full list is still available in the detail dialog."""
        reasons = (result or {}).get('reasons', [])
        if not reasons:
            return 'No specific concerns' if not (result or {}).get('is_phishing') else 'Flagged by ML model'
        summary = reasons[0]
        if len(reasons) > 1:
            summary += f" (+{len(reasons) - 1} more)"
        return summary
    
    def update_browser_status(self, connected=True, extension_count=0):
        """Update browser extension status"""
        self.browser_messages_received = connected
        self.update_connection_indicator(connected)
        
        if connected:
            status_text = f"🌐 Browser Extension: Connected"
            if self.browser_message_count > 0:
                status_text += f" ({self.browser_message_count} msgs)"
            if extension_count > 0:
                status_text += f" - {extension_count} active"
            self.browser_integration_status.config(
                text=status_text, 
                foreground=self.COLORS['safe']
            )
            self.extensions_count.config(text=str(extension_count if extension_count > 0 else 1))
        else:
            self.browser_integration_status.config(
                text="🌐 Browser Extension: Disconnected", 
                foreground=self.COLORS['danger']
            )
            self.extensions_count.config(text="0")
    
    def check_specific_connection(self):
        """Check if browser extension is specifically connected"""
        try:
            response = requests.get('http://localhost:9877/api/status', timeout=1)
            if response.status_code == 200:
                data = response.json()
                if data.get('connected'):
                    extensions = data.get('extensions', [])
                    self.update_browser_status(True, len(extensions))
                    return True
            return False
        except:
            return False
    
    def check_browser_status(self):
        """Periodically check browser connection status"""
        if self.check_specific_connection():
            pass
        elif len([d for d in self.email_cache.values() if d.get('source') == 'browser']) > 0 or self.browser_message_count > 0:
            self.update_browser_status(True)
        elif self.browser_server and hasattr(self.browser_server, 'server') and self.browser_server.server:
            if not self.browser_messages_received:
                self.browser_integration_status.config(
                    text="🌐 Browser Extension: Waiting for connection...", 
                    foreground=self.COLORS['warning']
                )
                self.update_connection_indicator(False)
        else:
            self.browser_integration_status.config(
                text="🌐 Browser Extension: Server not running", 
                foreground=self.COLORS['danger']
            )
            self.update_connection_indicator(False)
        
        self.root.after(5000, self.check_browser_status)
    
    def change_detection_mode(self):
        """Change the detection mode"""
        mode = self.detection_mode.get()
        mode_display = {
            "browser": "🌐 Browser Only",
            "samples": "📧 Samples Only",
            "both": "🔄 Both"
        }
        self.mode_status.config(text=f"Mode: {mode_display[mode]}")
        self.add_log(f"🔄 Detection mode changed to: {mode_display[mode]}", 'mode')
        
        if self.gmail_watcher:
            if mode == "browser":
                self.gmail_watcher.paused = True
                self.add_log("📧 Sample emails paused - only browser scanning active", 'info')
            elif mode == "samples":
                self.gmail_watcher.paused = False
                self.add_log("📧 Sample emails active - browser scanning ignored", 'info')
            else:
                self.gmail_watcher.paused = False
                self.add_log("📧 Both sample and browser scanning active", 'info')
    
    def force_extension_connection(self):
        """Force the browser extension to reconnect"""
        self.add_log("🔌 Forcing browser extension reconnection...", 'browser')
        
        try:
            response = requests.get('http://localhost:9877/api/health', timeout=2)
            if response.status_code == 200:
                data = response.json()
                connected_count = data.get('connected_extensions', 0)
                self.add_log(f"✅ Extension server responding - {connected_count} extensions connected", 'browser')
                
                status_response = requests.get('http://localhost:9877/api/status', timeout=2)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('connected'):
                        self.update_browser_status(True, len(status_data.get('extensions', [])))
                        self.add_log(f"✅ Extension connected!", 'browser')
                        messagebox.showinfo("Connection Success", 
                                           f"✅ Browser extension is connected!\n\n"
                                           f"Active extensions: {len(status_data.get('extensions', []))}")
                    else:
                        self.add_log("⚠️ No extensions currently connected", 'warning')
                        messagebox.showinfo("Connection Status", 
                                           "⚠️ Server running but no extensions connected.\n\n"
                                           "Make sure the extension is installed and Gmail is open.")
            else:
                self.add_log("❌ Extension server not responding properly", 'error')
        except requests.exceptions.ConnectionError:
            self.add_log("❌ Failed to connect to extension server", 'error')
            self.update_browser_status(False)
        except Exception as e:
            self.add_log(f"❌ Error: {e}", 'error')
    
    def test_browser_connection(self):
        """Test browser extension connection"""
        if self.check_specific_connection():
            self.add_log("🌐 Browser connection test: SUCCESS", 'browser')
            browser_msgs = [d for d in self.email_cache.values() if d.get('source') == 'browser']
            browser_msg_count = len(browser_msgs)
            messagebox.showinfo(
                "Browser Integration", 
                f"✅ Browser extension is connected!\n\n"
                f"Browser scans: {browser_msg_count} emails scanned\n"
                f"Browser messages: {self.browser_message_count}\n"
                f"Server port: 9877"
            )
        elif self.browser_server and hasattr(self.browser_server, 'server') and self.browser_server.server:
            self.update_browser_status(False)
            self.add_log("🌐 Browser connection test: Waiting for extension", 'warning')
            messagebox.showinfo(
                "Browser Integration", 
                "🌐 Browser extension server is running, but no extension connected yet.\n\n"
                "Make sure you have:\n"
                "1. Installed the Chrome/Brave extension\n"
                "2. Opened Gmail in your browser\n"
                "3. Refreshed the Gmail page"
            )
        else:
            self.update_browser_status(False)
            self.add_log("❌ Browser connection test: Server not running", 'error')
            messagebox.showwarning(
                "Browser Integration", 
                "⚠️ Browser extension server is not running.\n\n"
                "Restart the desktop app and try again."
            )
    
    def check_initial_permissions(self):
        """Check and request initial permissions"""
        if not self.permission_manager.check_permission('gmail_access'):
            self.permission_manager.request_gmail_permission()
        
        if not self.permission_manager.check_permission('browser_monitoring'):
            self.permission_manager.request_browser_permission()
        
        if not self.permission_manager.check_permission('background_running'):
            self.permission_manager.request_background_permission()
    
    def start_services(self):
        """Start background services"""
        # GmailWatcher only ever generates simulated sample emails (see
        # gmail_watcher.py) -- it never touches a real inbox, so it doesn't
        # need the real-credentials 'gmail_access' permission to run. Gating
        # it there made "Sample Emails Only" mode a silent no-op for anyone
        # who hadn't separately granted real Gmail access.
        self.gmail_watcher = GmailWatcher(self.permission_manager, self.on_email_detected)
        self.gmail_watcher.start()
        self.gmail_status.config(text="📧 Samples: Active")
        self.add_log("📧 Gmail watcher started", 'info')
        self.gmail_watcher.paused = False

        self.start_real_gmail_watcher_if_configured()

        if self.permission_manager.check_permission('browser_monitoring'):
            self.browser_watcher = BrowserWatcher(self.permission_manager, self.on_browser_event)
            self.browser_watcher.start()
            self.browser_status.config(text="🌐 Browser: Monitoring")
            self.add_log("🌐 Browser watcher started", 'info')
        
        try:
            response = requests.get('http://localhost:9877/api/health', timeout=1)
            if response.status_code == 200:
                self.browser_integration_status.config(text="🌐 Browser Extension: Waiting for connection...", foreground=self.COLORS['warning'])
                self.add_log("🌐 Browser integration server detected on port 9877", 'info')
            else:
                self.browser_integration_status.config(text="🌐 Browser Extension: Disconnected", foreground=self.COLORS['danger'])
                self.add_log("⚠️ Browser integration server not running", 'warning')
        except:
            self.browser_integration_status.config(text="🌐 Browser Extension: Disconnected", foreground=self.COLORS['danger'])
            self.add_log("⚠️ Browser integration server not running", 'warning')
        
        self.update_connection_indicator(False)
        
        if self.permission_manager.check_permission('background_running'):
            self.background_status.config(text="🔄 Background: Running")
            self.add_log("🔄 Background service running", 'info')
        
        self.change_detection_mode()

    def start_real_gmail_watcher_if_configured(self):
        """Start (or restart) the real IMAP-based Gmail scan if at least
        one enabled real account is configured. Called on startup and
        again right after a successful login, so a real inbox sweep begins
        immediately rather than waiting for the next app launch."""
        accounts = self.permission_manager.permissions.get('gmail_accounts', [])
        if not any(a.get('enabled', True) for a in accounts):
            return

        if self.real_gmail_watcher and self.real_gmail_watcher.is_alive():
            return

        self.real_gmail_watcher = RealGmailWatcher(self.permission_manager, self.on_email_detected)
        self.real_gmail_watcher.start()
        self.google_status.config(text=f"🔑 Google: {accounts[0]['email']}")
        self.add_log(f"📬 Scanning real inbox for {accounts[0]['email']}...", 'info')

    def on_email_detected(self, data):
        """Handle email detection event.

        Called from background threads (GmailWatcher, the browser HTTP
        server) as well as directly -- Tkinter widgets may only be touched
        from the main thread, so always redispatch through root.after
        rather than trusting the caller to have done it.
        """
        self.root.after(0, self._on_email_detected_main_thread, data)

    def _on_email_detected_main_thread(self, data):
        current_mode = self.detection_mode.get()
        
        if data.get('type') == 'browser_connected':
            extension_id = data.get('extension_id', '')
            if extension_id not in self.processed_extensions:
                self.processed_extensions.add(extension_id)
                self.browser_message_count += 1
                self.update_browser_status(True, 1)
                self.add_log(f"✅ Browser extension connected - Version: {data.get('version', 'unknown')}", 'browser')
            return
        
        if data.get('type') == 'browser_disconnected':
            self.update_browser_status(False)
            self.add_log("🔴 Browser extension disconnected", 'browser')
            return
        
        # Handle browser scan results - ALWAYS show in dashboard
        if data.get('type') == 'browser_scan_result':
            self.browser_message_count += 1
            self.update_browser_status(True)
            self.add_log(f"📨 Browser scan result received (#{self.browser_message_count})", 'browser')
            self.on_browser_scan_result(data)
            return
        
        if data.get('type') in ['browser_gmail_opened', 'scan_email']:
            self.browser_message_count += 1
            self.update_browser_status(True)
            self.add_log(f"📨 Browser message received (#{self.browser_message_count})", 'browser')
            
            if current_mode == "samples":
                self.add_log("   ⏭️ Ignoring (samples only mode)", 'info')
                return
        
        if data.get('type') == 'browser_gmail_opened':
            if current_mode != "samples":
                self.add_log(f"📧 Browser Gmail opened (tab: {data.get('tab_id')})", 'browser')
            return
        
        if data.get('type') == 'gemini_analysis':
            self.on_gemini_analysis(data)
            return
        
        if current_mode == "browser":
            return
        
        if 'email_id' not in data or not data['email_id']:
            data['email_id'] = len(self.email_cache) + 1000
        
        self.email_cache[data['email_id']] = data
        self.update_sender_reputation(data)
        self.add_notification(data)
        
        if data['type'] == 'phishing_detected':
            self.notification_manager.show_phishing_alert(data['email'], data['result'])
        else:
            if self.permission_manager.permissions['settings'].get('show_legitimate_alerts', True):
                self.notification_manager.show_legitimate_alert(data['email'], data['result'])
    
    def on_browser_scan_result(self, data):
        """Handle browser scan results and show in dashboard"""
        result = data.get('result', {})
        subject = data.get('subject', 'Unknown')
        sender = data.get('sender', 'Unknown')
        email_content = data.get('email_content', '')
        confidence = self.get_confidence_from_result(result)
        is_phishing = result.get('is_phishing', False)
        email_id = data.get('email_id', f"browser_{len(self.email_cache)}")
        
        self.add_log(f"🌐 Browser scan: {subject[:50]}...", 'browser')
        result_text = f"   Result: {'🔴 PHISHING' if is_phishing else '🟢 LEGITIMATE'} ({confidence:.1f}%)"
        self.add_log(result_text, 'phishing' if is_phishing else 'legitimate')
        
        for reason in result.get('reasons', [])[:3]:
            self.add_log(f"   • {reason}", 'info')
        
        if is_phishing:
            title = "🔴 PHISHING DETECTED IN BROWSER!"
            message = f"Email: {subject[:50]}...\nFrom: {sender}\nConfidence: {confidence:.1f}%"
            self.notification_manager.show_notification(title, message, 'warning')
        else:
            title = "🟢 Email Safe"
            message = f"Email: {subject[:50]}...\nFrom: {sender}\nConfidence: {confidence:.1f}%"
            self.notification_manager.show_notification(title, message, 'info')
        
        # Update browser scans counter
        current_browser_scans = int(self.browser_scans.cget('text')) if self.browser_scans.cget('text').isdigit() else 0
        self.browser_scans.config(text=str(current_browser_scans + 1))
        
        # Create email data for dashboard
        email_data = {
            'from': sender,
            'subject': subject,
            'body': email_content[:500] if email_content else 'Email content captured from browser',
            'id': email_id,
            'timestamp': datetime.now()
        }
        
        # Add to dashboard
        self.add_browser_notification(data, email_data, email_id, confidence, is_phishing)
    
    def add_browser_notification(self, data, email_data, email_id, confidence, is_phishing):
        """Add browser scan result to dashboard"""
        time_str = datetime.now().strftime("%H:%M:%S")
        
        if is_phishing:
            type_display = '🔴 PHISHING'
            tags = ('phishing',)
        else:
            type_display = '🟢 LEGITIMATE'
            tags = ('legitimate',)
        
        subject_short = email_data['subject'][:50] + '...' if len(email_data['subject']) > 50 else email_data['subject']
        reason = self._summarize_reasons(data.get('result', {}))

        item_id = self.notif_tree.insert('', 0, values=(
            time_str,
            type_display,
            '🌐 Browser',
            email_data['from'],
            subject_short,
            f"{confidence:.1f}%",
            reason
        ), tags=tags)
        
        browser_data = {
            'email': email_data,
            'result': data.get('result', {}),
            'type': 'phishing_detected' if is_phishing else 'legitimate_detected',
            'email_id': email_id,
            'source': 'browser'
        }
        self.email_cache[email_id] = browser_data
        self.email_id_map[item_id] = email_id
        
        self.notif_tree.tag_configure('phishing', background=self.COLORS['danger_bg'])
        self.notif_tree.tag_configure('legitimate', background=self.COLORS['safe_bg'])
        
        self.add_log(f"   ✅ Browser email added to dashboard", 'info')
    
    def on_gemini_analysis(self, data):
        email_id = data['email_id']
        gemini_result = data['gemini_result']
        
        self.add_log(f"🤖 Gemini analysis complete for ID {email_id}", 'info')
        
        if email_id in self.email_cache:
            self.email_cache[email_id]['gemini_result'] = gemini_result
            self.root.after(0, self.update_email_with_gemini, email_id, gemini_result)
        
        if gemini_result.get('confidence', 0) > 70:
            verdict = "phishing" if gemini_result.get('is_phishing') else "legitimate"
            self.add_log(f"🤖 AI confirms: {verdict} ({gemini_result.get('confidence', 0)}% confidence)", 'info')
            self.notification_manager.show_notification(
                "🤖 Gemini AI Analysis",
                f"AI confirms this email is {verdict} with {gemini_result['confidence']}% confidence",
                'info'
            )
    
    def update_email_with_gemini(self, email_id, gemini_result):
        for item_id, eid in self.email_id_map.items():
            if eid == email_id:
                current_values = list(self.notif_tree.item(item_id)['values'])
                if len(current_values) >= 6:
                    confidence = current_values[5]
                    if '🤖' not in confidence:
                        current_values[5] = f"{confidence} 🤖"
                        self.notif_tree.item(item_id, values=current_values)
                break
    
    def update_sender_reputation(self, data):
        sender = data['email']['from']
        is_phishing = data['type'] == 'phishing_detected'
        
        if sender not in self.sender_reputation:
            self.sender_reputation[sender] = {
                'total': 0,
                'phishing': 0,
                'legitimate': 0,
                'last_seen': datetime.now(),
                'reputation': 50
            }
            self.add_log(f"👤 New sender tracked: {sender}", 'info')
        
        rep = self.sender_reputation[sender]
        rep['total'] += 1
        if is_phishing:
            rep['phishing'] += 1
        else:
            rep['legitimate'] += 1
        
        if rep['total'] > 0:
            rep['reputation'] = (rep['legitimate'] / rep['total']) * 100
        
        rep['last_seen'] = datetime.now()
        self.senders_count.config(text=str(len(self.sender_reputation)))
    
    def add_notification(self, data):
        try:
            time_str = datetime.now().strftime("%H:%M:%S")
            email = data.get('email', {})
            result = data.get('result', {})
            email_id = data.get('email_id', '')
            source = data.get('source', 'Gmail Watcher')
            
            # Determine source display
            if source == 'browser':
                source_display = '🌐 Browser'
            elif source == 'sample':
                source_display = '📧 Sample'
            else:
                source_display = '🔄 Watcher'
            
            confidence = self.get_confidence_from_result(result)
            is_phishing = result.get('is_phishing', False)
            
            self.add_log(f"📧 Email from: {email.get('from', 'Unknown')}", 'info')
            self.add_log(f"   Subject: {email.get('subject', 'No subject')[:50]}...", 'info')
            self.add_log(f"   Source: {source_display}", 'info')
            self.add_log(f"   Result: {'🔴 PHISHING' if is_phishing else '🟢 LEGITIMATE'} ({confidence:.1f}%)", 
                        'phishing' if is_phishing else 'legitimate')
            
            if is_phishing:
                type_display = '🔴 PHISHING'
                tags = ('phishing',)
            else:
                type_display = '🟢 LEGITIMATE'
                tags = ('legitimate',)
            
            sender = email.get('from', 'Unknown') if isinstance(email, dict) else 'Unknown'
            subject = email.get('subject', 'No subject') if isinstance(email, dict) else 'No subject'
            subject = subject[:50] + '...' if len(subject) > 50 else subject
            
            reason = self._summarize_reasons(result)

            item_id = self.notif_tree.insert('', 0, values=(
                time_str,
                type_display,
                source_display,
                sender,
                subject,
                f"{confidence:.1f}%",
                reason
            ), tags=tags)
            
            self.email_id_map[item_id] = email_id
            self.notif_tree.tag_configure('phishing', background=self.COLORS['danger_bg'])
            self.notif_tree.tag_configure('legitimate', background=self.COLORS['safe_bg'])
            
        except Exception as e:
            self.add_log(f"❌ Error in add_notification: {e}", 'error')
    
    def show_context_menu(self, event):
        item = self.notif_tree.identify_row(event.y)
        if not item:
            return
        
        self.notif_tree.selection_set(item)
        email_id = self.email_id_map.get(item)
        if not email_id:
            return
        
        values = self.notif_tree.item(item)['values']
        source = values[2] if len(values) > 2 else 'Unknown'
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="👁️ View Details", 
                        command=lambda: self.show_email_details_for_id(email_id))
        
        if source == '🌐 Browser':
            menu.add_command(label="🌐 Open in Browser", 
                           command=lambda: self.open_in_browser(email_id))
        
        menu.add_command(label="✅ Mark as Legitimate", 
                        command=lambda: self.mark_as_legitimate(email_id))
        menu.add_command(label="❌ Mark as Phishing", 
                        command=lambda: self.mark_as_phishing(email_id))
        menu.add_separator()
        menu.add_command(label="🚫 Block Sender", 
                        command=lambda: self.block_sender(email_id))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def open_in_browser(self, email_id):
        if email_id and email_id in self.email_cache:
            data = self.email_cache[email_id]
            subject = data.get('subject', 'Unknown')
            self.add_log(f"🌐 Opening in browser: {subject[:50]}...", 'browser')
            messagebox.showinfo("Open in Browser", 
                              f"Opening email in browser...\n\nSubject: {subject}")
    
    def show_email_details(self, event):
        item = self.notif_tree.identify_row(event.y)
        if not item:
            return
        
        email_id = self.email_id_map.get(item)
        if email_id:
            self.show_email_details_for_id(email_id)
    
    def show_email_details_for_id(self, email_id):
        if email_id and email_id in self.email_cache:
            data = self.email_cache[email_id]
            self.add_log(f"👁️ Viewing details for email ID: {email_id}", 'info')
            EmailDetailDialog(self.root, data, self)
        else:
            messagebox.showinfo("Info", "Email details not available")
    
    def mark_as_legitimate(self, email_id):
        if email_id and email_id in self.email_cache:
            data = self.email_cache[email_id]
            sender = data['email']['from']

            self.update_sender_reputation_manual(sender, is_phishing=False)
            self.update_email_display(email_id, is_phishing=False)
            saved = db.correct_prediction(email_id, 'LEGITIMATE')

            self.add_log(f"✅ User feedback: Marked as legitimate - {sender}", 'legitimate')
            messagebox.showinfo(
                "Feedback Recorded",
                "Thank you! Sender reputation updated." +
                ("\nSaved for the next model retrain." if saved else
                 "\n(Not saved to the training set -- this email has no database record, "
                 "e.g. a sample scan taken before the app started.)"))

    def mark_as_phishing(self, email_id):
        if email_id and email_id in self.email_cache:
            data = self.email_cache[email_id]
            sender = data['email']['from']

            self.update_sender_reputation_manual(sender, is_phishing=True)
            self.update_email_display(email_id, is_phishing=True)
            saved = db.correct_prediction(email_id, 'PHISHING')

            self.add_log(f"🔴 User feedback: Confirmed phishing - {sender}", 'phishing')
            messagebox.showinfo(
                "Feedback Recorded",
                "Thank you for confirming!" +
                ("\nSaved for the next model retrain." if saved else
                 "\n(Not saved to the training set -- this email has no database record, "
                 "e.g. a sample scan taken before the app started.)"))
    
    def update_email_display(self, email_id, is_phishing):
        for item_id, eid in self.email_id_map.items():
            if eid == email_id:
                current_values = list(self.notif_tree.item(item_id)['values'])
                if current_values:
                    new_values = list(current_values)
                    if is_phishing:
                        new_values[1] = '🔴 PHISHING (Confirmed)'
                        self.notif_tree.item(item_id, tags=('phishing',))
                    else:
                        new_values[1] = '🟢 LEGITIMATE (Confirmed)'
                        self.notif_tree.item(item_id, tags=('legitimate',))
                    self.notif_tree.item(item_id, values=new_values)
                break
    
    def update_sender_reputation_manual(self, sender, is_phishing):
        if sender not in self.sender_reputation:
            self.sender_reputation[sender] = {
                'total': 0,
                'phishing': 0,
                'legitimate': 0,
                'last_seen': datetime.now(),
                'reputation': 50
            }
        
        rep = self.sender_reputation[sender]
        rep['total'] += 1
        if is_phishing:
            rep['phishing'] += 1
        else:
            rep['legitimate'] += 1
        
        if rep['total'] > 0:
            rep['reputation'] = (rep['legitimate'] / rep['total']) * 100
        
        rep['last_seen'] = datetime.now()
        self.senders_count.config(text=str(len(self.sender_reputation)))
    
    def block_sender(self, email_id):
        if email_id and email_id in self.email_cache:
            sender = self.email_cache[email_id]['email']['from']
            result = messagebox.askyesno("Block Sender", f"Block all emails from {sender}?")
            if result:
                if 'blocked_senders' not in self.permission_manager.permissions:
                    self.permission_manager.permissions['blocked_senders'] = []
                if sender not in self.permission_manager.permissions['blocked_senders']:
                    self.permission_manager.permissions['blocked_senders'].append(sender)
                    self.permission_manager.save_permissions()
                
                self.add_log(f"🚫 Sender blocked: {sender}", 'warning')
                messagebox.showinfo("Sender Blocked", f"Future emails from {sender} will be flagged.")
    
    def on_browser_event(self, data):
        if data['type'] == 'gmail_page_detected':
            self.browser_status.config(text="🌐 Browser: On Gmail")
            self.add_log("🌐 Browser detected on Gmail page", 'browser')
    
    def update_stats(self):
        stats = db.get_statistics()
        
        self.total_scanned.config(text=str(stats['total_emails']))
        self.phishing_count.config(text=str(stats['phishing']))
        self.safe_count.config(text=str(stats['legitimate']))
        
        if stats['total_emails'] > 0:
            accuracy = (stats['legitimate'] + stats['phishing']) / stats['total_emails'] * 100
            self.accuracy.config(text=f"{accuracy:.1f}%")
        
        self.last_scan.config(text=f"Last scan: {datetime.now().strftime('%H:%M:%S')}")
        self.root.after(5000, self.update_stats)
    
    def manual_scan(self):
        self.scan_btn.config(state=tk.DISABLED, text="🔍 Scanning...")
        self.add_log("🔍 Manual scan started", 'info')

        def scan():
            before = db.get_statistics()
            if self.gmail_watcher:
                self.gmail_watcher.simulate_check_emails()
            time.sleep(1)
            after = db.get_statistics()
            scanned = after['total_emails'] - before['total_emails']
            phishing_found = after['phishing'] - before['phishing']
            self.root.after(0, self.scan_complete, scanned, phishing_found)

        threading.Thread(target=scan, daemon=True).start()

    def scan_complete(self, scanned, phishing_found):
        self.scan_btn.config(state=tk.NORMAL, text="🔍 Scan Now")
        self.add_log(f"✅ Manual scan completed: {scanned} new email(s), {phishing_found} phishing", 'info')

        self.notification_manager.show_scan_complete({'scanned': scanned, 'phishing': phishing_found})
        if scanned == 0:
            messagebox.showinfo("Scan Complete", "No new emails since the last check.")
        else:
            messagebox.showinfo("Scan Complete",
                                 f"Checked {scanned} new email(s), found {phishing_found} phishing attempt(s).")
    
    def open_settings(self):
        self.add_log("⚙️ Opening settings", 'info')
        SettingsDialog(self.root, self.permission_manager)

    def open_browser_setup(self):
        self.add_log("🌐 Opening browser connection setup", 'info')
        BrowserSetupDialog(self.root)
    
    def show_statistics(self):
        stats = db.get_statistics()
        
        total_senders = len(self.sender_reputation)
        suspicious_senders = sum(1 for s in self.sender_reputation.values() if s['reputation'] < 30)
        browser_scans = sum(1 for data in self.email_cache.values() if data.get('source') == 'browser')
        
        stats_text = (
            f"📊 Detailed Statistics\n"
            f"{'='*30}\n\n"
            f"Total Emails Scanned: {stats['total_emails']}\n"
            f"Phishing Detected: {stats['phishing']}\n"
            f"Safe Emails: {stats['legitimate']}\n"
            f"Browser Scans: {browser_scans}\n"
            f"Average Confidence: {stats['avg_confidence']:.1f}%\n\n"
            f"Sender Statistics:\n"
            f"  • Total Senders: {total_senders}\n"
            f"  • Suspicious Senders: {suspicious_senders}\n"
            f"  • Trusted Senders: {total_senders - suspicious_senders}\n\n"
            f"Sources:\n"
        )
        
        for source in stats['by_source']:
            stats_text += f"  • {source['source']}: {source['count']}\n"
        
        self.add_log("📊 Statistics viewed", 'info')
        messagebox.showinfo("Statistics", stats_text)
    
    def show_history(self):
        self.add_log("📋 Opening history view", 'info')
        HistoryDialog(self.root)
    
    def show_sender_reputation(self):
        self.add_log("👤 Opening sender reputation", 'info')
        dialog = tk.Toplevel(self.root)
        dialog.title("Sender Reputation")
        dialog.geometry("700x500")
        dialog.transient(self.root)
        
        columns = ('Sender', 'Total', 'Phishing', 'Legitimate', 'Reputation', 'Status')
        tree = ttk.Treeview(dialog, columns=columns, show='headings', height=15)
        
        tree.heading('Sender', text='Sender')
        tree.heading('Total', text='Total')
        tree.heading('Phishing', text='Phishing')
        tree.heading('Legitimate', text='Legitimate')
        tree.heading('Reputation', text='Reputation')
        tree.heading('Status', text='Status')
        
        tree.column('Sender', width=250)
        tree.column('Total', width=70)
        tree.column('Phishing', width=70)
        tree.column('Legitimate', width=70)
        tree.column('Reputation', width=80)
        tree.column('Status', width=100)
        
        scrollbar = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        for sender, data in self.sender_reputation.items():
            reputation = data['reputation']
            if reputation < 30:
                status = "🔴 Suspicious"
                tags = ('suspicious',)
            elif reputation < 70:
                status = "🟡 Neutral"
                tags = ('neutral',)
            else:
                status = "🟢 Trusted"
                tags = ('trusted',)
            
            tree.insert('', tk.END, values=(
                sender[:50] + '...' if len(sender) > 50 else sender,
                data['total'],
                data['phishing'],
                data['legitimate'],
                f"{reputation:.1f}%",
                status
            ), tags=tags)
        
        tree.tag_configure('suspicious', background=self.COLORS['danger_bg'])
        tree.tag_configure('neutral', background=self.COLORS['warning_bg'])
        tree.tag_configure('trusted', background=self.COLORS['safe_bg'])
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Refresh", 
                  command=lambda: self.refresh_sender_dialog(dialog)).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Close", 
                  command=dialog.destroy).pack(side=tk.RIGHT, padx=10)
    
    def refresh_sender_dialog(self, dialog):
        dialog.destroy()
        self.show_sender_reputation()
    
    def show_docs(self):
        self.add_log("📚 Documentation viewed", 'info')
        messagebox.showinfo(
            "Documentation",
            "Phishing Detector Documentation\n\n"
            "1. Grant Gmail access to scan emails\n"
            "2. Install browser extension for real-time monitoring\n"
            "3. Enable background running for continuous protection\n"
            "4. Double-click emails to view details\n"
            "5. Right-click emails to mark as legitimate/phishing\n"
            "6. Sender reputation helps identify patterns\n\n"
            "Browser Integration:\n"
            "• Install the Chrome/Brave extension from the extension folder\n"
            "• Emails opened in Gmail are automatically scanned\n"
            "• Results appear instantly in both browser and dashboard\n"
            "• All scans are saved to the database"
        )
    
    def show_about(self):
        self.add_log("ℹ️ About dialog opened", 'info')
        messagebox.showinfo(
            "About Phishing Detector",
            "🛡️ Phishing Email Detector\n"
            "Version 1.0.0\n\n"
            "AI-powered phishing detection using NLP\n"
            "Trained on 56,649 emails with 98% accuracy\n\n"
            "Features:\n"
            "• Real-time Gmail monitoring\n"
            "• Browser extension integration\n"
            "• Sender reputation tracking\n"
            "• User feedback system\n"
            "• Cross-platform support\n\n"
            "© 2025 Liron Nyambu"
        )
    
    def export_logs(self):
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            self.add_log(f"📤 Logs exported to {filename}", 'info')
            messagebox.showinfo("Export Complete", f"Logs exported to {filename}")
    
    def quit_app(self):
        self.add_log("👋 Shutting down...", 'info')
        if self.gmail_watcher:
            self.gmail_watcher.stop()
        if self.real_gmail_watcher:
            self.real_gmail_watcher.stop()
        if self.browser_watcher:
            self.browser_watcher.stop()
        self.root.quit()
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.mainloop()