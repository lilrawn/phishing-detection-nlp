"""
History dialog for viewing scanned email history
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import sys
from pathlib import Path
import csv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.database import db

class HistoryDialog:
    """Dialog for viewing email scan history"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Scan History - Phishing Detector")
        self.dialog.geometry("1000x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Variables
        self.filter_var = tk.StringVar(value="all")
        self.search_var = tk.StringVar()
        self.current_page = 0
        self.page_size = 50
        self.total_pages = 1
        self.current_data = []
        
        self.setup_ui()
        self.load_history()
        
    def setup_ui(self):
        """Setup the history dialog UI"""
        # Top frame with filters
        top_frame = ttk.Frame(self.dialog, padding="10")
        top_frame.pack(fill=tk.X)
        
        # Search
        ttk.Label(top_frame, text="Search:").grid(row=0, column=0, padx=5)
        search_entry = ttk.Entry(top_frame, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=1, padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.load_history())
        
        # Filter by type
        ttk.Label(top_frame, text="Filter:").grid(row=0, column=2, padx=5)
        filter_combo = ttk.Combobox(top_frame, textvariable=self.filter_var, 
                                    values=['all', 'phishing', 'legitimate', 'recent'],
                                    state='readonly', width=15)
        filter_combo.grid(row=0, column=3, padx=5)
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self.load_history())
        
        # Date range
        ttk.Label(top_frame, text="From:").grid(row=0, column=4, padx=5)
        self.from_date = ttk.Entry(top_frame, width=12)
        self.from_date.grid(row=0, column=5, padx=5)
        self.from_date.insert(0, "2024-01-01")
        
        ttk.Label(top_frame, text="To:").grid(row=0, column=6, padx=5)
        self.to_date = ttk.Entry(top_frame, width=12)
        self.to_date.grid(row=0, column=7, padx=5)
        self.to_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # Refresh button
        ttk.Button(top_frame, text="🔄 Refresh", command=self.load_history).grid(row=0, column=8, padx=20)
        
        # Export button
        ttk.Button(top_frame, text="📥 Export CSV", command=self.export_csv).grid(row=0, column=9, padx=5)
        
        # Main content - Treeview for history
        content_frame = ttk.Frame(self.dialog, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview
        columns = ('ID', 'Date', 'Time', 'From/Source', 'Subject/Email', 'Prediction', 'Confidence', 'URLs', 'Urgent')
        self.tree = ttk.Treeview(content_frame, columns=columns, show='headings', height=20)
        
        # Define headings
        self.tree.heading('ID', text='ID')
        self.tree.heading('Date', text='Date')
        self.tree.heading('Time', text='Time')
        self.tree.heading('From/Source', text='From/Source')
        self.tree.heading('Subject/Email', text='Subject/Email')
        self.tree.heading('Prediction', text='Prediction')
        self.tree.heading('Confidence', text='Confidence')
        self.tree.heading('URLs', text='URLs')
        self.tree.heading('Urgent', text='Urgent')
        
        # Set column widths
        self.tree.column('ID', width=50)
        self.tree.column('Date', width=80)
        self.tree.column('Time', width=70)
        self.tree.column('From/Source', width=150)
        self.tree.column('Subject/Email', width=300)
        self.tree.column('Prediction', width=80)
        self.tree.column('Confidence', width=80)
        self.tree.column('URLs', width=50)
        self.tree.column('Urgent', width=50)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click to show details
        self.tree.bind('<Double-Button-1>', self.show_email_details)
        
        # Pagination frame
        pagination_frame = ttk.Frame(self.dialog, padding="10")
        pagination_frame.pack(fill=tk.X)
        
        ttk.Button(pagination_frame, text="◀ Previous", command=self.prev_page).pack(side=tk.LEFT, padx=5)
        
        self.page_label = ttk.Label(pagination_frame, text="Page 1 of 1")
        self.page_label.pack(side=tk.LEFT, padx=20)
        
        ttk.Button(pagination_frame, text="Next ▶", command=self.next_page).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(pagination_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.RIGHT, padx=5)
        ttk.Button(pagination_frame, text="Clear All", command=self.clear_all).pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Loading...")
        status_bar = ttk.Label(self.dialog, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def load_history(self):
        """Load history from database"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Get stats first
            stats = db.get_statistics()
            
            # In a real implementation, you would query the database with filters
            # For demo, we'll create sample data
            sample_data = self.get_sample_data()
            
            # Apply filters
            filtered_data = self.apply_filters(sample_data)
            
            # Calculate pagination
            self.total_pages = max(1, (len(filtered_data) + self.page_size - 1) // self.page_size)
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(filtered_data))
            
            # Update page label
            self.page_label.config(text=f"Page {self.current_page + 1} of {self.total_pages}")
            
            # Add data to tree
            for item in filtered_data[start_idx:end_idx]:
                # Determine tags for coloring
                tags = ()
                if item['prediction'] == 'PHISHING':
                    tags = ('phishing',)
                elif item['prediction'] == 'LEGITIMATE':
                    tags = ('legitimate',)
                
                # Format confidence
                confidence = f"{item['confidence']:.1f}%" if isinstance(item['confidence'], (int, float)) else item['confidence']
                
                # Insert item
                self.tree.insert('', tk.END, values=(
                    item['id'],
                    item['date'],
                    item['time'],
                    item['source'],
                    item['subject'][:50] + '...' if len(item['subject']) > 50 else item['subject'],
                    item['prediction'],
                    confidence,
                    item['urls'],
                    item['urgent']
                ), tags=tags)
            
            # Configure tag colors
            self.tree.tag_configure('phishing', background='#ffcccc')
            self.tree.tag_configure('legitimate', background='#ccffcc')
            
            # Update status
            self.status_var.set(f"Showing {start_idx + 1}-{end_idx} of {len(filtered_data)} records")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load history: {e}")
    
    def get_sample_data(self):
        """Get sample data for demo"""
        return [
            {
                'id': 1,
                'date': '2025-03-10',
                'time': '14:23:45',
                'source': 'gmail@example.com',
                'subject': 'URGENT: Your account has been limited',
                'prediction': 'PHISHING',
                'confidence': 98.5,
                'urls': 1,
                'urgent': 4
            },
            {
                'id': 2,
                'date': '2025-03-10',
                'time': '10:15:22',
                'source': 'manager@company.com',
                'subject': 'Team meeting tomorrow at 10 AM',
                'prediction': 'LEGITIMATE',
                'confidence': 12.3,
                'urls': 0,
                'urgent': 0
            },
            {
                'id': 3,
                'date': '2025-03-09',
                'time': '16:42:10',
                'source': 'amazon@amazon.com',
                'subject': 'Your Amazon order #123-4567890 has shipped',
                'prediction': 'LEGITIMATE',
                'confidence': 8.7,
                'urls': 1,
                'urgent': 0
            },
            {
                'id': 4,
                'date': '2025-03-09',
                'time': '09:30:05',
                'source': 'security@paypal.com',
                'subject': 'FINAL NOTICE: Your account will be suspended',
                'prediction': 'PHISHING',
                'confidence': 99.2,
                'urls': 1,
                'urgent': 3
            },
            {
                'id': 5,
                'date': '2025-03-08',
                'time': '11:20:33',
                'source': 'netflix@netflix.com',
                'subject': 'Your monthly statement is now available',
                'prediction': 'LEGITIMATE',
                'confidence': 5.6,
                'urls': 0,
                'urgent': 0
            },
            {
                'id': 6,
                'date': '2025-03-08',
                'time': '08:45:12',
                'source': 'hr@company.com',
                'subject': 'New employee benefits information',
                'prediction': 'LEGITIMATE',
                'confidence': 3.2,
                'urls': 0,
                'urgent': 1
            },
            {
                'id': 7,
                'date': '2025-03-07',
                'time': '15:50:28',
                'source': 'apple@apple.com',
                'subject': 'Your Apple ID was used to sign in',
                'prediction': 'LEGITIMATE',
                'confidence': 25.6,
                'urls': 0,
                'urgent': 0
            },
            {
                'id': 8,
                'date': '2025-03-07',
                'time': '13:10:45',
                'source': 'bank@bankofamerica.com',
                'subject': 'Verify your account information',
                'prediction': 'PHISHING',
                'confidence': 95.8,
                'urls': 1,
                'urgent': 2
            },
            {
                'id': 9,
                'date': '2025-03-06',
                'time': '09:05:17',
                'source': 'linkedin@linkedin.com',
                'subject': 'Sarah Johnson accepted your connection request',
                'prediction': 'LEGITIMATE',
                'confidence': 2.1,
                'urls': 0,
                'urgent': 0
            },
            {
                'id': 10,
                'date': '2025-03-06',
                'time': '07:30:00',
                'source': 'irs@irs.gov',
                'subject': 'URGENT: Tax refund pending',
                'prediction': 'PHISHING',
                'confidence': 97.3,
                'urls': 1,
                'urgent': 3
            }
        ]
    
    def apply_filters(self, data):
        """Apply filters to data"""
        filtered = data.copy()
        
        # Filter by type
        if self.filter_var.get() == 'phishing':
            filtered = [d for d in filtered if d['prediction'] == 'PHISHING']
        elif self.filter_var.get() == 'legitimate':
            filtered = [d for d in filtered if d['prediction'] == 'LEGITIMATE']
        elif self.filter_var.get() == 'recent':
            filtered = filtered[:20]  # Just show first 20
        
        # Filter by search
        search = self.search_var.get().lower()
        if search:
            filtered = [d for d in filtered if 
                       search in d['source'].lower() or 
                       search in d['subject'].lower()]
        
        # Filter by date range
        try:
            from_date = datetime.strptime(self.from_date.get(), "%Y-%m-%d")
            to_date = datetime.strptime(self.to_date.get(), "%Y-%m-%d")
            
            filtered = [d for d in filtered if 
                       from_date <= datetime.strptime(d['date'], "%Y-%m-%d") <= to_date]
        except:
            pass  # Invalid date format, skip date filter
        
        return filtered
    
    def show_email_details(self, event):
        """Show detailed view of selected email"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        values = item['values']
        
        # Create details dialog
        details = tk.Toplevel(self.dialog)
        details.title(f"Email Details - ID: {values[0]}")
        details.geometry("600x400")
        details.transient(self.dialog)
        
        # Email details
        frame = ttk.Frame(details, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # ID
        ttk.Label(frame, text=f"Email ID: {values[0]}", font=('Helvetica', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        # Date/Time
        ttk.Label(frame, text=f"Received: {values[1]} {values[2]}").pack(anchor=tk.W, pady=2)
        
        # From
        ttk.Label(frame, text=f"From: {values[3]}").pack(anchor=tk.W, pady=2)
        
        # Subject
        ttk.Label(frame, text=f"Subject: {values[4]}", wraplength=500, justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        
        # Prediction with color
        pred_frame = ttk.Frame(frame)
        pred_frame.pack(anchor=tk.W, pady=5)
        
        ttk.Label(pred_frame, text="Prediction: ").pack(side=tk.LEFT)
        pred_label = ttk.Label(pred_frame, text=values[5], font=('Helvetica', 10, 'bold'))
        pred_label.pack(side=tk.LEFT)
        
        if values[5] == 'PHISHING':
            pred_label.configure(foreground='red')
        else:
            pred_label.configure(foreground='green')
        
        # Confidence
        ttk.Label(frame, text=f"Confidence: {values[6]}").pack(anchor=tk.W, pady=2)
        
        # Indicators
        ttk.Label(frame, text=f"URLs detected: {values[7]}").pack(anchor=tk.W, pady=2)
        ttk.Label(frame, text=f"Urgent keywords: {values[8]}").pack(anchor=tk.W, pady=2)
        
        # Full email content (in a real app)
        ttk.Label(frame, text="\nFull Email Content:", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=(10, 2))
        
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, height=10)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Sample content
        sample_content = f"""From: {values[3]}
To: user@example.com
Date: {values[1]} {values[2]}
Subject: {values[4]}

This is a sample email content. In a real implementation, this would show the actual email body that was scanned.

The model detected {values[7]} URL(s) and {values[8]} urgent keyword(s) in this email.

Confidence: {values[6]} that this is {values[5].lower()}.
"""
        text_widget.insert('1.0', sample_content)
        text_widget.configure(state='disabled')
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Mark as False Positive", 
                  command=lambda: self.mark_false_positive(values[0])).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=details.destroy).pack(side=tk.RIGHT, padx=5)
    
    def mark_false_positive(self, email_id):
        """Mark an email as false positive"""
        result = messagebox.askyesno(
            "Confirm",
            "Mark this email as false positive?\n"
            "This will help improve the model."
        )
        if result:
            # In a real app, you would update the database
            messagebox.showinfo("Success", "Feedback recorded. Thank you!")
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_history()
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.load_history()
    
    def delete_selected(self):
        """Delete selected items"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Info", "No items selected")
            return
        
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Delete {len(selection)} selected item(s)?"
        )
        
        if result:
            for item in selection:
                self.tree.delete(item)
            self.status_var.set(f"Deleted {len(selection)} item(s)")
    
    def clear_all(self):
        """Clear all history"""
        result = messagebox.askyesno(
            "Confirm Clear All",
            "Are you sure you want to clear all history?\n"
            "This action cannot be undone."
        )
        
        if result:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.current_page = 0
            self.status_var.set("All history cleared")
    
    def export_csv(self):
        """Export history to CSV"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export History"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(['ID', 'Date', 'Time', 'From/Source', 'Subject', 
                               'Prediction', 'Confidence', 'URLs', 'Urgent Keywords'])
                
                # Write data
                for item in self.tree.get_children():
                    values = self.tree.item(item)['values']
                    writer.writerow(values)
            
            messagebox.showinfo("Success", f"History exported to {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")