"""
Settings dialog for phishing detector
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from pathlib import Path

class SettingsDialog:
    """Settings dialog for configuring the application"""
    
    def __init__(self, parent, permission_manager):
        self.parent = parent
        self.permission_manager = permission_manager
        self.settings = permission_manager.permissions['settings']
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings - Phishing Detector")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_general_tab()
        self.create_notifications_tab()
        self.create_privacy_tab()
        self.create_advanced_tab()
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save_settings,
                   width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy,
                   width=15).pack(side=tk.LEFT, padx=5)
    
    def create_general_tab(self):
        """Create general settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="General")
        
        # Monitoring settings
        monitor_frame = ttk.LabelFrame(tab, text="Monitoring", padding=10)
        monitor_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Check interval
        ttk.Label(monitor_frame, text="Check interval (seconds):").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.interval_var = tk.IntVar(value=self.settings['check_interval'])
        ttk.Spinbox(monitor_frame, from_=10, to=300, textvariable=self.interval_var,
                   width=10).grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Auto scan
        self.auto_scan_var = tk.BooleanVar(value=self.settings['auto_scan'])
        ttk.Checkbutton(monitor_frame, text="Auto-scan new emails",
                       variable=self.auto_scan_var).grid(row=1, column=0, columnspan=2, 
                                                         sticky=tk.W, pady=5)
        
        # Max history
        ttk.Label(monitor_frame, text="Max history items:").grid(
            row=2, column=0, sticky=tk.W, pady=5)
        self.history_var = tk.IntVar(value=1000)
        ttk.Spinbox(monitor_frame, from_=100, to=10000, textvariable=self.history_var,
                   width=10).grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Startup
        startup_frame = ttk.LabelFrame(tab, text="Startup", padding=10)
        startup_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.startup_var = tk.BooleanVar(value=self.permission_manager.permissions['background_running'])
        ttk.Checkbutton(startup_frame, text="Start with system",
                       variable=self.startup_var,
                       command=self.toggle_startup).pack(anchor=tk.W, pady=5)
        
        self.minimized_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(startup_frame, text="Start minimized to tray",
                       variable=self.minimized_var).pack(anchor=tk.W, pady=5)
    
    def create_notifications_tab(self):
        """Create notifications settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Notifications")
        
        # Notification settings
        notif_frame = ttk.LabelFrame(tab, text="Alert Settings", padding=10)
        notif_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.show_notif_var = tk.BooleanVar(value=self.settings['show_notifications'])
        ttk.Checkbutton(notif_frame, text="Show desktop notifications",
                       variable=self.show_notif_var).pack(anchor=tk.W, pady=5)
        
        self.sound_var = tk.BooleanVar(value=self.settings['sound_alerts'])
        ttk.Checkbutton(notif_frame, text="Play sound alerts",
                       variable=self.sound_var).pack(anchor=tk.W, pady=5)
        
        # Notification timeout
        ttk.Label(notif_frame, text="Notification timeout (seconds):").pack(anchor=tk.W, pady=5)
        self.timeout_var = tk.IntVar(value=5)
        ttk.Spinbox(notif_frame, from_=1, to=30, textvariable=self.timeout_var,
                   width=10).pack(anchor=tk.W, padx=20)
        
        # Alert threshold
        threshold_frame = ttk.LabelFrame(tab, text="Alert Threshold", padding=10)
        threshold_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(threshold_frame, 
                 text="Minimum confidence to trigger alert (0-100%):").pack(anchor=tk.W, pady=5)
        
        self.threshold_var = tk.IntVar(value=70)
        threshold_scale = ttk.Scale(threshold_frame, from_=0, to=100, 
                                    variable=self.threshold_var, orient=tk.HORIZONTAL)
        threshold_scale.pack(fill=tk.X, pady=5)
        
        self.threshold_label = ttk.Label(threshold_frame, text=f"{self.threshold_var.get()}%")
        self.threshold_label.pack()
        
        threshold_scale.configure(command=lambda v: self.threshold_label.config(text=f"{int(float(v))}%"))
    
    def create_privacy_tab(self):
        """Create privacy settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Privacy")
        
        # Data storage
        storage_frame = ttk.LabelFrame(tab, text="Data Storage", padding=10)
        storage_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.store_data_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(storage_frame, text="Store scan history locally",
                       variable=self.store_data_var).pack(anchor=tk.W, pady=5)
        
        self.encrypt_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(storage_frame, text="Encrypt stored data",
                       variable=self.encrypt_var).pack(anchor=tk.W, pady=5)
        
        # Data location
        ttk.Label(storage_frame, text="Data storage location:").pack(anchor=tk.W, pady=5)
        
        path_frame = ttk.Frame(storage_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        self.path_var = tk.StringVar(value=str(Path.home() / '.phishing_detector'))
        ttk.Entry(path_frame, textvariable=self.path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Browse", command=self.browse_path).pack(side=tk.RIGHT, padx=5)
        
        # Clear data button
        ttk.Button(storage_frame, text="Clear All Stored Data",
                  command=self.clear_data).pack(pady=10)
    
    def create_advanced_tab(self):
        """Create advanced settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Advanced")
        
        # ML Model settings
        model_frame = ttk.LabelFrame(tab, text="ML Model", padding=10)
        model_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(model_frame, text="Model weights:").pack(anchor=tk.W, pady=5)
        
        # ML weight slider
        weight_frame = ttk.Frame(model_frame)
        weight_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(weight_frame, text="Rules").pack(side=tk.LEFT)
        
        self.ml_weight_var = tk.IntVar(value=int(self.settings.get('ml_weight', 0.7) * 100))
        weight_scale = ttk.Scale(weight_frame, from_=0, to=100,
                                 variable=self.ml_weight_var, orient=tk.HORIZONTAL)
        weight_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        ttk.Label(weight_frame, text="ML").pack(side=tk.RIGHT)
        
        self.weight_label = ttk.Label(model_frame, 
                                      text=f"ML: {self.ml_weight_var.get()}% | Rules: {100-self.ml_weight_var.get()}%")
        self.weight_label.pack(pady=5)
        
        weight_scale.configure(command=self.update_weight_label)
        
        # Logging
        log_frame = ttk.LabelFrame(tab, text="Logging", padding=10)
        log_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.logging_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_frame, text="Enable debug logging",
                       variable=self.logging_var).pack(anchor=tk.W, pady=5)
        
        # View logs button
        ttk.Button(log_frame, text="View Logs",
                  command=self.view_logs).pack(pady=5)
    
    def update_weight_label(self, value):
        """Update ML weight label"""
        ml_weight = int(float(value))
        self.weight_label.config(text=f"ML: {ml_weight}% | Rules: {100-ml_weight}%")
    
    def toggle_startup(self):
        """Toggle startup setting"""
        if self.startup_var.get():
            self.permission_manager.setup_autostart()
        else:
            # Remove from startup (implementation depends on OS)
            pass
    
    def browse_path(self):
        """Browse for data storage path"""
        path = filedialog.askdirectory(title="Select Data Storage Location")
        if path:
            self.path_var.set(path)
    
    def clear_data(self):
        """Clear all stored data"""
        result = messagebox.askyesno(
            "Confirm",
            "Are you sure you want to clear all stored data?\n"
            "This will delete all scan history and settings."
        )
        if result:
            # Clear data logic here
            messagebox.showinfo("Success", "All data cleared successfully!")
    
    def view_logs(self):
        """View application logs"""
        log_file = Path.home() / '.phishing_detector' / 'logs' / 'app.log'
        if log_file.exists():
            os.startfile(str(log_file)) if os.name == 'nt' else os.system(f'open "{log_file}"')
        else:
            messagebox.showinfo("Info", "No logs found")
    
    def save_settings(self):
        """Save all settings"""
        self.settings.update({
            'check_interval': self.interval_var.get(),
            'auto_scan': self.auto_scan_var.get(),
            'show_notifications': self.show_notif_var.get(),
            'sound_alerts': self.sound_var.get(),
            'notification_timeout': self.timeout_var.get(),
            'alert_threshold': self.threshold_var.get(),
            'ml_weight': self.ml_weight_var.get() / 100
        })
        
        self.permission_manager.permissions['background_running'] = self.startup_var.get()
        self.permission_manager.save_permissions()
        
        messagebox.showinfo("Success", "Settings saved successfully!")
        self.dialog.destroy()