"""
Gmail login dialog for phishing detector
"""
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

class LoginDialog:
    """Dialog for Gmail login"""
    
    def __init__(self, parent, permission_manager):
        self.parent = parent
        self.permission_manager = permission_manager
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Gmail Login - Phishing Detector")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the login dialog UI"""
        # Title
        title = ttk.Label(self.dialog, text="🔐 Connect to Gmail", 
                          font=('Helvetica', 16, 'bold'))
        title.pack(pady=20)
        
        # Info text
        info_text = (
            "To scan your emails for phishing attempts,\n"
            "Phishing Detector needs access to your Gmail account.\n\n"
            "Your credentials are stored locally and encrypted.\n"
            "No data is ever sent to external servers."
        )
        info = ttk.Label(self.dialog, text=info_text, justify=tk.CENTER)
        info.pack(pady=10)
        
        # Security note
        security_frame = ttk.LabelFrame(self.dialog, text="🔒 Security", padding=10)
        security_frame.pack(pady=10, padx=20, fill=tk.X)
        
        security_text = (
            "• Use an App Password, not your regular password\n"
            "• Generate App Password in Google Account settings\n"
            "• Revoke access anytime from Google Account"
        )
        security = ttk.Label(security_frame, text=security_text, justify=tk.LEFT)
        security.pack()
        
        # Link to create app password
        link = ttk.Label(security_frame, text="How to create App Password", 
                         foreground="blue", cursor="hand2")
        link.pack(pady=5)
        link.bind("<Button-1>", lambda e: webbrowser.open(
            "https://support.google.com/accounts/answer/185833"
        ))
        
        # Login form
        form_frame = ttk.Frame(self.dialog)
        form_frame.pack(pady=20, padx=20, fill=tk.X)
        
        # Email
        ttk.Label(form_frame, text="Gmail Address:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.email_var = tk.StringVar()
        email_entry = ttk.Entry(form_frame, textvariable=self.email_var, width=40)
        email_entry.grid(row=0, column=1, pady=5, padx=10)
        
        # App Password
        ttk.Label(form_frame, text="App Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(form_frame, textvariable=self.password_var, 
                                   show="*", width=40)
        password_entry.grid(row=1, column=1, pady=5, padx=10)
        
        # Remember me
        self.remember_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form_frame, text="Remember me", 
                        variable=self.remember_var).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Connect", command=self.connect, 
                   width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy, 
                   width=15).pack(side=tk.LEFT, padx=5)
        
        # Focus email entry
        email_entry.focus()
        
    def connect(self):
        """Handle connect button click"""
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()
        
        if not email or not password:
            messagebox.showerror("Error", "Please enter both email and password")
            return
        
        if '@' not in email:
            messagebox.showerror("Error", "Please enter a valid email address")
            return
        
        # Save credentials
        self.permission_manager.permissions['gmail_access'] = True
        self.permission_manager.permissions['gmail_accounts'].append({
            'email': email,
            'password': self.permission_manager.encrypt_password(password),
            'enabled': True,
            'last_check': None
        })
        self.permission_manager.save_permissions()
        
        messagebox.showinfo("Success", "✅ Gmail connected successfully!")
        self.dialog.destroy()