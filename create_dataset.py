#!/usr/bin/env python3
"""
Script to create the combined dataset from raw data files
Run this BEFORE main.py to ensure your datasets are properly loaded
"""

import os
import sys
import pandas as pd
import glob
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("📊 PHISHING DATASET CREATION TOOL")
print("="*60)

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, 'data', 'processed')

# Create directories if they don't exist
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

print(f"\n📁 Raw data directory: {RAW_DATA_DIR}")
print(f"📁 Processed data directory: {PROCESSED_DATA_DIR}")

# List all files in raw directory
print("\n📋 Files found in raw directory:")
raw_files = os.listdir(RAW_DATA_DIR) if os.path.exists(RAW_DATA_DIR) else []
for f in raw_files:
    file_path = os.path.join(RAW_DATA_DIR, f)
    size = os.path.getsize(file_path)
    print(f"  - {f} ({size} bytes)")

def read_spamassassin_files():
    """Read emails from Mail-SpamAssassin directory"""
    print("\n📧 Reading Mail-SpamAssassin dataset...")
    emails = []
    labels = []
    
    spamassassin_path = os.path.join(RAW_DATA_DIR, 'Mail-SpamAssassin-3.4.6')
    
    if not os.path.exists(spamassassin_path):
        print(f"  ⚠️  SpamAssassin directory not found at: {spamassassin_path}")
        return pd.DataFrame()
    
    # Common subdirectory names in SpamAssassin corpus
    spam_dirs = ['spam', 'spam_2', 'spam_20030228', 'spam_20050301']
    ham_dirs = ['ham', 'ham_2', 'easy_ham', 'easy_ham_2', 'hard_ham']
    
    # Read spam emails
    for spam_dir in spam_dirs:
        full_path = os.path.join(spamassassin_path, spam_dir)
        if os.path.isdir(full_path):
            files = glob.glob(os.path.join(full_path, '*'))
            print(f"  Found {len(files)} files in {spam_dir}")
            
            for file_path in files[:100]:  # Limit to first 100 files per directory
                try:
                    if os.path.isfile(file_path):
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if len(content.strip()) > 50:  # Skip very short files
                                emails.append(content)
                                labels.append('phishing')
                except Exception as e:
                    continue
    
    # Read ham (legitimate) emails
    for ham_dir in ham_dirs:
        full_path = os.path.join(spamassassin_path, ham_dir)
        if os.path.isdir(full_path):
            files = glob.glob(os.path.join(full_path, '*'))
            print(f"  Found {len(files)} files in {ham_dir}")
            
            for file_path in files[:100]:  # Limit to first 100 files per directory
                try:
                    if os.path.isfile(file_path):
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if len(content.strip()) > 50:
                                emails.append(content)
                                labels.append('legitimate')
                except Exception as e:
                    continue
    
    df = pd.DataFrame({'text': emails, 'label': labels, 'source': 'spamassassin'})
    print(f"  ✅ Loaded {len(df)} emails from SpamAssassin")
    return df

def read_email_text_csv():
    """Read from email_text.csv"""
    print("\n📧 Reading email_text.csv...")
    csv_path = os.path.join(RAW_DATA_DIR, 'email_text.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  email_text.csv not found")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(csv_path)
        print(f"  CSV columns: {list(df.columns)}")
        print(f"  CSV shape: {df.shape}")
        
        # Try to identify text and label columns
        text_col = None
        for col in ['text', 'email', 'body', 'content', 'message']:
            if col in df.columns:
                text_col = col
                break
        
        label_col = None
        for col in ['label', 'class', 'type', 'category', 'spam']:
            if col in df.columns:
                label_col = col
                break
        
        if text_col is None:
            # If no obvious text column, use the first column
            text_col = df.columns[0]
            print(f"  Using first column as text: {text_col}")
        
        if label_col is None:
            # If no label column, check if there's a column with binary values
            for col in df.columns:
                if col != text_col and df[col].nunique() <= 3:
                    label_col = col
                    print(f"  Using {col} as label column (unique values: {df[col].unique()})")
                    break
        
        if label_col is None:
            # Create dummy labels (all legitimate for now)
            print("  ⚠️  No label column found, creating default labels")
            df['label'] = 'legitimate'
        else:
            df['label'] = df[label_col].astype(str).str.lower()
            # Convert to standard labels
            df['label'] = df['label'].apply(lambda x: 'phishing' if x in ['1', 'true', 'yes', 'spam', 'phishing'] else 'legitimate')
        
        df['text'] = df[text_col].astype(str)
        df['source'] = 'email_text_csv'
        
        result_df = df[['text', 'label', 'source']].copy()
        print(f"  ✅ Loaded {len(result_df)} emails from email_text.csv")
        print(f"     Phishing: {len(result_df[result_df['label']=='phishing'])}")
        print(f"     Legitimate: {len(result_df[result_df['label']=='legitimate'])}")
        
        return result_df
        
    except Exception as e:
        print(f"  ❌ Error reading email_text.csv: {e}")
        return pd.DataFrame()

def read_nazario_csv():
    """Read from Nazario_5.csv"""
    print("\n📧 Reading Nazario_5.csv...")
    csv_path = os.path.join(RAW_DATA_DIR, 'Nazario_5.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  Nazario_5.csv not found")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(csv_path)
        print(f"  CSV columns: {list(df.columns)}")
        print(f"  CSV shape: {df.shape}")
        
        # Nazario dataset is typically all phishing
        # Usually has columns like 'email', 'body', etc.
        text_col = None
        for col in ['email', 'text', 'body', 'content', 'message']:
            if col in df.columns:
                text_col = col
                break
        
        if text_col is None:
            text_col = df.columns[0]
        
        df['text'] = df[text_col].astype(str)
        df['label'] = 'phishing'  # Nazario is phishing dataset
        df['source'] = 'nazario'
        
        result_df = df[['text', 'label', 'source']].copy()
        print(f"  ✅ Loaded {len(result_df)} emails from Nazario_5.csv (all phishing)")
        
        return result_df
        
    except Exception as e:
        print(f"  ❌ Error reading Nazario_5.csv: {e}")
        return pd.DataFrame()

def create_sample_dataset():
    """Create a sample dataset if no real data is found"""
    print("\n📧 Creating sample dataset...")
    
    # Sample phishing emails
    phishing_samples = [
        "URGENT: Your account has been limited. Click here to verify: http://fake-bank.com/verify",
        "PayPal: Your account has been suspended. Update now: http://paypal-security.net",
        "IRS Notice: Your tax refund is pending. Update information: http://irs-gov-refund.com",
        "Apple ID: Your account has been locked. Verify: http://apple-id-verify.net",
        "FedEx: Your package delivery failed. Reschedule: http://fedex-delivery.info"
    ]
    
    # Sample legitimate emails
    legitimate_samples = [
        "Weekly team meeting on Friday at 10 AM in Conference Room B.",
        "Your Amazon order #123-4567890 has been shipped and will arrive Monday.",
        "LinkedIn: Sarah Johnson would like to connect with you.",
        "Netflix: Your monthly statement is now available.",
        "University: Spring semester registration opens November 15th."
    ]
    
    # Create DataFrame
    phishing_df = pd.DataFrame({'text': phishing_samples, 'label': 'phishing', 'source': 'sample'})
    legitimate_df = pd.DataFrame({'text': legitimate_samples, 'label': 'legitimate', 'source': 'sample'})
    
    df = pd.concat([phishing_df, legitimate_df], ignore_index=True)
    print(f"  ✅ Created {len(df)} sample emails")
    
    return df

def main():
    """Main function to create combined dataset"""
    
    print("\n" + "="*60)
    print("🔄 COMBINING DATASETS")
    print("="*60)
    
    datasets = []
    
    # Try each dataset
    df1 = read_spamassassin_files()
    if not df1.empty:
        datasets.append(df1)
    
    df2 = read_email_text_csv()
    if not df2.empty:
        datasets.append(df2)
    
    df3 = read_nazario_csv()
    if not df3.empty:
        datasets.append(df3)
    
    # If no real datasets, use samples
    if not datasets:
        print("\n⚠️  No real datasets found. Using sample data...")
        df_sample = create_sample_dataset()
        datasets.append(df_sample)
    
    # Combine all datasets
    combined_df = pd.concat(datasets, ignore_index=True)
    
    # Remove duplicates based on text
    combined_df = combined_df.drop_duplicates(subset=['text'], keep='first')
    
    # Remove rows with empty text
    combined_df = combined_df[combined_df['text'].str.len() > 10].reset_index(drop=True)
    
    # Shuffle the dataset
    combined_df = combined_df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    print("\n" + "="*60)
    print("📊 FINAL COMBINED DATASET STATISTICS")
    print("="*60)
    print(f"Total emails: {len(combined_df)}")
    print(f"Phishing emails: {len(combined_df[combined_df['label']=='phishing'])}")
    print(f"Legitimate emails: {len(combined_df[combined_df['label']=='legitimate'])}")
    
    if 'source' in combined_df.columns:
        print("\n📁 Source distribution:")
        print(combined_df['source'].value_counts())
    
    # Save combined dataset
    output_path = os.path.join(PROCESSED_DATA_DIR, 'combined_dataset.csv')
    combined_df.to_csv(output_path, index=False)
    print(f"\n💾 Dataset saved to: {output_path}")
    
    # Verify the file was saved correctly
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"   File size: {file_size} bytes")
        
        # Try to read it back to verify
        test_df = pd.read_csv(output_path)
        print(f"   Verified: {len(test_df)} rows can be read back")
    
    return combined_df

if __name__ == "__main__":
    main()
