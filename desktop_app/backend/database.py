"""
Database module for storing emails and user data
"""
import sqlite3
import os
import json
from datetime import datetime
import hashlib

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'database', 'phishing.db')

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Emails table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_text TEXT,
                sender TEXT,
                subject TEXT,
                source TEXT,
                predicted_label TEXT,
                confidence REAL,
                has_links BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                email TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                user_feedback TEXT,
                correct BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_email(self, email_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO emails (email_text, sender, subject, source, predicted_label, confidence, has_links)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            email_data.get('email_text', '')[:5000],
            email_data.get('sender', ''),
            email_data.get('subject', '')[:200],
            email_data.get('source', 'unknown'),
            email_data.get('predicted_label', 'UNKNOWN'),
            email_data.get('confidence', 0),
            email_data.get('has_links', False)
        ))
        
        email_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return email_id
    
    def get_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM emails")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM emails WHERE predicted_label LIKE '%PHISHING%'")
        phishing = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM emails WHERE predicted_label LIKE '%LEGITIMATE%'")
        legitimate = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(confidence) FROM emails")
        avg_conf = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_emails': total,
            'phishing': phishing,
            'legitimate': legitimate,
            'avg_confidence': avg_conf
        }
    
    def get_recent_emails(self, limit=50):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, sender, subject, predicted_label, confidence, timestamp
            FROM emails
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        emails = cursor.fetchall()
        conn.close()
        return emails

db = Database()
