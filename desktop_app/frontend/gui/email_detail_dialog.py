"""
Email detail dialog for viewing full email content
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class EmailDetailDialog:
    """Dialog for displaying full email details"""
    
    def __init__(self, parent, email_data, dashboard):
        self.parent = parent
        self.email_data = email_data
        self.dashboard = dashboard
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Email Details")
        self.dialog.geometry("700x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the email detail UI"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with result
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Handle both data formats
        if 'email' in self.email_data:
            email = self.email_data['email']
        else:
            # Create a default email object
            email = {
                'from': 'unknown@example.com',
                'subject': 'No subject',
                'body': 'No content available',
                'id': self.email_data.get('email_id', 'N/A'),
                'timestamp': datetime.now()
            }
        
        result = self.email_data.get('result', {})
        is_phishing = self.email_data.get('type') == 'phishing_detected'
        
        # Result badge
        if is_phishing:
            badge_text = "🔴 PHISHING DETECTED"
            badge_color = '#B0524F'  # muted red -- see PhishingDashboard.COLORS['danger']
        else:
            badge_text = "🟢 LEGITIMATE EMAIL"
            badge_color = '#4A8C5E'  # muted green -- see PhishingDashboard.COLORS['safe']
        
        badge = tk.Label(header_frame, text=badge_text, bg=badge_color, 
                        fg='white', font=('Helvetica', 14, 'bold'),
                        padx=10, pady=5)
        badge.pack(side=tk.LEFT)
        
        # Confidence
        conf_frame = ttk.Frame(header_frame)
        conf_frame.pack(side=tk.RIGHT)
        ttk.Label(conf_frame, text="Confidence:", 
                 font=('Helvetica', 10)).pack(side=tk.LEFT)
        confidence = result.get('confidence', 0)
        ttk.Label(conf_frame, text=f"{confidence:.1f}%", 
                 font=('Helvetica', 14, 'bold'),
                 foreground='#B0524F' if is_phishing else '#4A8C5E').pack(side=tk.LEFT, padx=5)
        
        # Email metadata
        meta_frame = ttk.LabelFrame(main_frame, text="Email Information", padding="10")
        meta_frame.pack(fill=tk.X, pady=10)
        
        # From
        from_frame = ttk.Frame(meta_frame)
        from_frame.pack(fill=tk.X, pady=2)
        ttk.Label(from_frame, text="From:", width=10, font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(from_frame, text=email.get('from', 'Unknown'), wraplength=500).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Subject
        subject_frame = ttk.Frame(meta_frame)
        subject_frame.pack(fill=tk.X, pady=2)
        ttk.Label(subject_frame, text="Subject:", width=10, font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(subject_frame, text=email.get('subject', 'No subject'), wraplength=500).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Time
        time_frame = ttk.Frame(meta_frame)
        time_frame.pack(fill=tk.X, pady=2)
        ttk.Label(time_frame, text="Time:", width=10, font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT)
        timestamp = email.get('timestamp', datetime.now())
        if isinstance(timestamp, datetime):
            time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            time_str = str(timestamp)
        ttk.Label(time_frame, text=time_str).pack(side=tk.LEFT)
        
        # ID
        id_frame = ttk.Frame(meta_frame)
        id_frame.pack(fill=tk.X, pady=2)
        ttk.Label(id_frame, text="Email ID:", width=10, font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(id_frame, text=email.get('id', 'N/A')).pack(side=tk.LEFT)
        
        # Analysis results
        analysis_frame = ttk.LabelFrame(main_frame, text="Analysis Results", padding="10")
        analysis_frame.pack(fill=tk.X, pady=10)
        
        # ML probability
        ml_frame = ttk.Frame(analysis_frame)
        ml_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ml_frame, text="ML Probability:", width=15).pack(side=tk.LEFT)
        ttk.Label(ml_frame, text=f"{result.get('ml_probability', 0) * 100:.1f}%").pack(side=tk.LEFT)

        # Combined probability (ML + rule-based augmentation)
        combined_frame = ttk.Frame(analysis_frame)
        combined_frame.pack(fill=tk.X, pady=2)
        ttk.Label(combined_frame, text="Combined:", width=15).pack(side=tk.LEFT)
        ttk.Label(combined_frame, text=f"{result.get('probability', 0) * 100:.1f}%").pack(side=tk.LEFT)
        
        # Reasons
        reasons = result.get('reasons', [])
        if reasons:
            reasons_frame = ttk.Frame(analysis_frame)
            reasons_frame.pack(fill=tk.X, pady=5)
            ttk.Label(reasons_frame, text="Reasons:", width=15).pack(side=tk.LEFT, anchor=tk.N)
            
            reasons_text = tk.Text(reasons_frame, height=len(reasons), width=50, 
                                   wrap=tk.WORD, font=('Helvetica', 10))
            reasons_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
            for reason in reasons:
                reasons_text.insert(tk.END, f"• {reason}\n")
            reasons_text.config(state=tk.DISABLED)
        
        # Email body
        body_frame = ttk.LabelFrame(main_frame, text="Email Content", padding="10")
        body_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(body_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        body_text = tk.Text(text_frame, wrap=tk.WORD, height=15, 
                            font=('Helvetica', 10), padx=5, pady=5)
        body_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=body_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        body_text.configure(yscrollcommand=scrollbar.set)
        
        # Insert email body
        body_text.insert(tk.END, email.get('body', 'No content available'))
        body_text.config(state=tk.DISABLED)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        email_id = self.email_data.get('email_id')
        
        if is_phishing:
            ttk.Button(button_frame, text="✅ This is Legitimate (False Positive)", 
                      command=lambda: self.mark_legitimate(email_id)).pack(side=tk.LEFT, padx=5)
        else:
            ttk.Button(button_frame, text="❌ This is Phishing (False Negative)", 
                      command=lambda: self.mark_phishing(email_id)).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="🚫 Block Sender", 
                  command=lambda: self.block_sender(email_id)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", 
                  command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def mark_legitimate(self, email_id):
        """Mark this email as legitimate"""
        if email_id:
            self.dashboard.mark_as_legitimate(email_id)
            messagebox.showinfo("Feedback Recorded", 
                              "Thank you! This will help improve future detections.")
            self.dialog.destroy()
    
    def mark_phishing(self, email_id):
        """Mark this email as phishing"""
        if email_id:
            self.dashboard.mark_as_phishing(email_id)
            messagebox.showinfo("Feedback Recorded", 
                              "Thank you for confirming!")
            self.dialog.destroy()
    
    def block_sender(self, email_id):
        """Block this sender"""
        if email_id:
            self.dashboard.block_sender(email_id)
            self.dialog.destroy()