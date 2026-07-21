#!/usr/bin/env python3
"""
Import existing CSV files to database
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import db
from config import RAW_DATA_DIR

print("="*60)
print("📥 IMPORTING CSV FILES TO DATABASE")
print("="*60)

# Import email_text.csv
email_text_path = os.path.join(RAW_DATA_DIR, 'email_text.csv')
if os.path.exists(email_text_path):
    db.import_csv_to_db(email_text_path, 'email_text.csv')
else:
    print(f"❌ {email_text_path} not found")

# Import Nazario_5.csv
nazario_path = os.path.join(RAW_DATA_DIR, 'Nazario_5.csv')
if os.path.exists(nazario_path):
    db.import_csv_to_db(nazario_path, 'nazario')
else:
    print(f"❌ {nazario_path} not found")

# Show final stats
stats = db.get_statistics()
print(f"\n📊 Final Database Statistics:")
print(f"   Training data: {stats['total_emails']} emails")
print(f"   By source: {stats['by_source']}")
