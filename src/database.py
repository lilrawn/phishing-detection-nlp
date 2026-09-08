"""
Database module for storing emails and predictions
"""
import sqlite3
import os
import json
from datetime import datetime
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'phishing.db')

class EmailDatabase:
    """Store and retrieve emails with predictions"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Emails table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_text TEXT,
                cleaned_text TEXT,
                source TEXT,
                label TEXT,
                predicted_label TEXT,
                probability REAL,
                confidence REAL,
                threshold REAL,
                url_count INTEGER,
                urgent_count INTEGER,
                exclaim_count INTEGER,
                caps_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Training data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_text TEXT,
                label TEXT,
                source TEXT,
                used_in_training BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                user_feedback TEXT,
                correct_prediction BOOLEAN,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')

        # emails.corrected_label holds the human-confirmed ground truth
        # once a user marks a prediction right/wrong via the dashboard,
        # kept separate from predicted_label (the model's original,
        # immutable output) so retraining can prefer it without losing the
        # record of what the model actually said. ALTER TABLE ... ADD
        # COLUMN has no IF NOT EXISTS in sqlite, so this is guarded for
        # every run after the first against an already-migrated database.
        try:
            cursor.execute('ALTER TABLE emails ADD COLUMN corrected_label TEXT')
        except sqlite3.OperationalError:
            pass  # column already exists

        conn.commit()
        conn.close()
        print(f"✅ Database initialized: {self.db_path}")
    
    def save_email(self, email_data):
        """Save an email and its prediction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO emails 
                (email_text, cleaned_text, source, label, predicted_label, 
                 probability, confidence, threshold, url_count, urgent_count, 
                 exclaim_count, caps_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                email_data.get('email_text', ''),
                email_data.get('cleaned_text', ''),
                email_data.get('source', 'user_input'),
                email_data.get('true_label', None),
                email_data.get('predicted_label'),
                email_data.get('probability'),
                email_data.get('confidence'),
                email_data.get('threshold', 0.5),
                email_data.get('url_count', 0),
                email_data.get('urgent_count', 0),
                email_data.get('exclaim_count', 0),
                email_data.get('caps_count', 0)
            ))
            
            email_id = cursor.lastrowid
            conn.commit()
            return email_id
            
        except Exception as e:
            print(f"Error saving email: {e}")
            return None
        finally:
            conn.close()
    
    def save_feedback(self, email_id, correct, notes=""):
        """Save user feedback on prediction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO feedback (email_id, correct_prediction, notes)
            VALUES (?, ?, ?)
        ''', (email_id, correct, notes))

        conn.commit()
        conn.close()

    def correct_prediction(self, email_id, corrected_label, notes=""):
        """
        Record a user's correction of a prediction as ground truth for
        retraining, and log it in the feedback table.

        `corrected_label` is 'PHISHING' or 'LEGITIMATE' (the label the
        user says is actually correct -- not necessarily different from
        what the model predicted; confirming a correct prediction is
        itself useful signal, recorded the same way). Returns False if
        `email_id` doesn't exist, True otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT predicted_label FROM emails WHERE id = ?', (email_id,))
            row = cursor.fetchone()
            if row is None:
                return False
            predicted_label = row[0]

            cursor.execute('UPDATE emails SET corrected_label = ? WHERE id = ?',
                            (corrected_label, email_id))
            cursor.execute('''
                INSERT INTO feedback (email_id, user_feedback, correct_prediction, notes)
                VALUES (?, ?, ?, ?)
            ''', (email_id, corrected_label, predicted_label == corrected_label, notes))
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_statistics(self):
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Total emails
            total = pd.read_sql("SELECT COUNT(*) as count FROM emails", conn).iloc[0]['count']

            # By label
            by_label = pd.read_sql("""
                SELECT
                    SUM(CASE WHEN predicted_label = 'PHISHING' THEN 1 ELSE 0 END) as phishing,
                    SUM(CASE WHEN predicted_label = 'LEGITIMATE' THEN 1 ELSE 0 END) as legitimate
                FROM emails
            """, conn).iloc[0]

            # By source
            by_source = pd.read_sql("""
                SELECT source, COUNT(*) as count
                FROM emails
                GROUP BY source
                ORDER BY count DESC
            """, conn)

            # Average confidence
            avg_conf = pd.read_sql("SELECT AVG(confidence) as avg_confidence FROM emails", conn).iloc[0]['avg_confidence']

            return {
                'total_emails': total,
                'phishing': int(by_label['phishing'] or 0),
                'legitimate': int(by_label['legitimate'] or 0),
                'by_source': by_source.to_dict('records'),
                'avg_confidence': float(avg_conf or 0)
            }
        finally:
            conn.close()

    def export_for_training(self, limit=1000):
        """
        Export emails for retraining, preferring the user-corrected label
        (emails.corrected_label, set via correct_prediction()) over the
        model's own predicted_label wherever a correction exists -- the
        whole point of the feedback loop is that a corrected mistake
        shouldn't be re-taught to the next model as if it were right.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql("""
                SELECT email_text,
                       CASE
                           WHEN COALESCE(corrected_label, predicted_label) = 'PHISHING' THEN 'phishing'
                           ELSE 'legitimate'
                       END as label,
                       corrected_label IS NOT NULL as is_user_corrected
                FROM emails
                WHERE label IS NULL           -- not one of the original statically-labeled samples
                   OR corrected_label IS NOT NULL  -- unless a user has since corrected it
                ORDER BY created_at DESC
                LIMIT ?
            """, conn, params=(limit,))
        finally:
            conn.close()

    def import_csv_to_db(self, csv_path, source_name):
        """Import existing CSV data to database"""
        df = pd.read_csv(csv_path)
        conn = sqlite3.connect(self.db_path)
        imported = 0
        failed = 0
        try:
            for _, row in df.iterrows():
                try:
                    conn.execute('''
                        INSERT OR IGNORE INTO training_data (email_text, label, source)
                        VALUES (?, ?, ?)
                    ''', (row.get('text', ''), row.get('label', ''), source_name))
                    imported += 1
                except Exception as e:
                    failed += 1
                    if failed <= 5:
                        print(f"  ⚠️  Row skipped: {e}")
            conn.commit()
        finally:
            conn.close()
        print(f"✅ Imported {imported} emails from {source_name}" + (f" ({failed} skipped)" if failed else ""))

# Initialize database on import
db = EmailDatabase()