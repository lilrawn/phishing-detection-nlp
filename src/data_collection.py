"""
Enhanced module for collecting and loading phishing email datasets
Supports Mail-SpamAssassin, email_text.csv, and Nazario_5.csv
"""
import pandas as pd
import numpy as np
import os
import sys
import glob
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, RANDOM_STATE

class DataCollector:
    """
    Class to handle data collection from various sources
    """
    
    def __init__(self):
        self.raw_data_dir = RAW_DATA_DIR
        self.processed_dir = PROCESSED_DATA_DIR
        self.spamassassin_dir = os.path.join(RAW_DATA_DIR, 'Mail-SpamAssassin-3.4.6')
        
    def read_spamassassin_files(self):
        """
            Read emails from SpamAssassin corpus
        """
        print("\n📧 Reading SpamAssassin corpus...")
        emails = []
        labels = []
    
        # Look for the corpus directory
        corpus_paths = [
            os.path.join(RAW_DATA_DIR, 'spamassassin_corpus'),
            os.path.join(RAW_DATA_DIR, 'Mail-SpamAssassin-3.4.6', 'corpus'),
            os.path.join(RAW_DATA_DIR, 'spamassassin')
        ]
    
        corpus_dir = None
        for path in corpus_paths:
            if os.path.exists(path):
                corpus_dir = path
                print(f"  Found corpus at: {path}")
                break
    
        if not corpus_dir:
            print("  ⚠️  SpamAssassin corpus not found")
            return pd.DataFrame()
    
        # Look for spam and ham directories
        spam_dirs = ['spam', 'spam_2', 'spam_20030228', 'spam_20050311']
        ham_dirs = ['ham', 'ham_2', 'easy_ham', 'easy_ham_2', 'hard_ham']
    
        # Count emails
        spam_count = 0
        ham_count = 0
    
        # Process spam
        for spam_dir in spam_dirs:
            full_path = os.path.join(corpus_dir, spam_dir)
            if os.path.isdir(full_path):
                files = [f for f in os.listdir(full_path) 
                        if os.path.isfile(os.path.join(full_path, f)) and not f.startswith('.')]
                print(f"  Found {len(files)} files in {spam_dir}")
            
                for filename in files[:200]:  # Limit to 200 per directory to avoid overload
                    file_path = os.path.join(full_path, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if len(content.strip()) > 100:  # Skip very short files
                                emails.append(content)
                                labels.append('phishing')
                                spam_count += 1
                    except Exception as e:
                        continue
    
        # Process ham
        for ham_dir in ham_dirs:
            full_path = os.path.join(corpus_dir, ham_dir)
            if os.path.isdir(full_path):
                files = [f for f in os.listdir(full_path) 
                        if os.path.isfile(os.path.join(full_path, f)) and not f.startswith('.')]
                print(f"  Found {len(files)} files in {ham_dir}")
            
                for filename in files[:200]:  # Limit to 200 per directory
                    file_path = os.path.join(full_path, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if len(content.strip()) > 100:
                                emails.append(content)
                                labels.append('legitimate')
                                ham_count += 1
                    except Exception as e:
                        continue
    
        df = pd.DataFrame({
            'text': emails,
            'label': labels,
            'source': 'spamassassin'
        })
    
        print(f"  ✅ Loaded {len(df)} emails from SpamAssassin corpus")
        print(f"     - Phishing: {spam_count}")
        print(f"     - Legitimate: {ham_count}")
    
        return df
    
    def read_email_text_csv(self):
        """
        Read from email_text.csv file
        Assumes columns: 'text'/'email' and 'label'/'class'/'type'
        """
        print("\n📧 Reading email_text.csv...")
        csv_path = os.path.join(RAW_DATA_DIR, 'email_text.csv')
        
        if not os.path.exists(csv_path):
            print(f"⚠️  email_text.csv not found at: {csv_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(csv_path)
            print(f"  CSV columns: {list(df.columns)}")
            
            # Try to identify text and label columns
            text_col = None
            label_col = None
            
            # Common column names for email content
            text_candidates = ['text', 'email', 'body', 'content', 'message', 'email_text']
            for col in text_candidates:
                if col in df.columns:
                    text_col = col
                    break
            
            # Common column names for labels
            label_candidates = ['label', 'class', 'type', 'category', 'spam', 'is_phishing']
            for col in label_candidates:
                if col in df.columns:
                    label_col = col
                    break
            
            if text_col is None or label_col is None:
                print(f"  ⚠️  Could not identify required columns")
                print(f"     Please ensure CSV has a text column and a label column")
                return pd.DataFrame()
            
            # Standardize labels
            df['text'] = df[text_col].astype(str)
            df['label'] = df[label_col].astype(str).str.lower()
            
            # Convert various label formats to 'phishing'/'legitimate'
            df['label'] = df['label'].apply(self._standardize_label)
            
            # Keep only relevant rows
            df = df[df['label'].isin(['phishing', 'legitimate'])].copy()
            df['source'] = 'email_text_csv'
            
            # Keep only needed columns
            df = df[['text', 'label', 'source']]
            
            print(f"  ✓ Loaded {len(df)} emails from email_text.csv")
            print(f"    - Phishing: {len(df[df['label']=='phishing'])}")
            print(f"    - Legitimate: {len(df[df['label']=='legitimate'])}")
            
            return df
            
        except Exception as e:
            print(f"  ❌ Error reading email_text.csv: {e}")
            return pd.DataFrame()
    
    def read_nazario_csv(self):
        """
        Read from Nazario_5.csv (Nazario phishing dataset)
        """
        print("\n📧 Reading Nazario_5.csv...")
        csv_path = os.path.join(RAW_DATA_DIR, 'Nazario_5.csv')
        
        if not os.path.exists(csv_path):
            print(f"⚠️  Nazario_5.csv not found at: {csv_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(csv_path)
            print(f"  CSV columns: {list(df.columns)}")
            
            # Nazario dataset typically has columns like 'email' and 'phishing'
            # but we need to check actual structure
            
            # Try to identify text and label columns
            text_col = None
            possible_text_cols = ['email', 'text', 'content', 'body', 'message']
            for col in possible_text_cols:
                if col in df.columns:
                    text_col = col
                    break
            
            if text_col is None:
                # If no obvious text column, use the first string column
                for col in df.columns:
                    if df[col].dtype == 'object':
                        # Check if it contains email-like content
                        sample = df[col].iloc[0] if len(df) > 0 else ''
                        if len(str(sample)) > 100:  # Likely email content
                            text_col = col
                            break
            
            # Look for label column
            label_col = None
            possible_label_cols = ['label', 'class', 'type', 'phishing', 'is_phishing', 'spam']
            for col in possible_label_cols:
                if col in df.columns:
                    label_col = col
                    break
            
            if text_col is None:
                print(f"  ⚠️  Could not identify text column in Nazario_5.csv")
                print(f"     Available columns: {list(df.columns)}")
                return pd.DataFrame()
            
            # Extract text and create labels
            df['text'] = df[text_col].astype(str)
            
            if label_col:
                df['label'] = df[label_col].astype(str).str.lower()
                df['label'] = df['label'].apply(self._standardize_label)
            else:
                # If no label column, assume all are phishing (Nazario is phishing dataset)
                print("  ℹ️  No label column found, assuming all are phishing")
                df['label'] = 'phishing'
            
            df['source'] = 'nazario'
            df = df[['text', 'label', 'source']]
            
            print(f"  ✓ Loaded {len(df)} emails from Nazario_5.csv")
            print(f"    - Phishing: {len(df[df['label']=='phishing'])}")
            print(f"    - Legitimate: {len(df[df['label']=='legitimate'])}")
            
            return df
            
        except Exception as e:
            print(f"  ❌ Error reading Nazario_5.csv: {e}")
            return pd.DataFrame()
    
    def _standardize_label(self, label_str):
        """
        Convert various label formats to 'phishing' or 'legitimate'
        """
        label = str(label_str).lower().strip()
        
        # Phishing indicators
        if any(x in label for x in ['phish', 'spam', '1', 'true', 'yes', 'bad', 'malicious']):
            return 'phishing'
        
        # Legitimate indicators
        if any(x in label for x in ['legit', 'ham', '0', 'false', 'no', 'good', 'benign', 'safe']):
            return 'legitimate'
        
        # If can't determine, return as is (will be filtered later)
        return label
    
    def load_and_combine_datasets(self):
        """
        Load all available datasets and combine them
        """
        print("\n" + "="*60)
        print("📊 LOADING ALL DATASETS")
        print("="*60)
        
        datasets = []
        
        # 1. Load SpamAssassin
        df_spam = self.read_spamassassin_files()
        if not df_spam.empty:
            datasets.append(df_spam)
        
        # 2. Load email_text.csv
        df_email = self.read_email_text_csv()
        if not df_email.empty:
            datasets.append(df_email)
        
        # 3. Load Nazario_5.csv
        df_nazario = self.read_nazario_csv()
        if not df_nazario.empty:
            datasets.append(df_nazario)
        
        if not datasets:
            print("\n❌ No datasets found. Creating sample dataset instead...")
            return self.create_sample_dataset()
        
        # Combine all datasets
        combined_df = pd.concat(datasets, ignore_index=True)
        
        # Remove duplicates based on text content
        combined_df = combined_df.drop_duplicates(subset=['text'], keep='first')
        
        # Remove any rows with empty text
        combined_df = combined_df[combined_df['text'].str.len() > 10].reset_index(drop=True)
        
        # Shuffle the dataset
        combined_df = combined_df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
        
        print("\n" + "="*60)
        print(f"✅ FINAL COMBINED DATASET")
        print("="*60)
        print(f"Total emails: {len(combined_df)}")
        print(f"Phishing emails: {len(combined_df[combined_df['label']=='phishing'])}")
        print(f"Legitimate emails: {len(combined_df[combined_df['label']=='legitimate'])}")
        print(f"\nSources:")
        print(combined_df['source'].value_counts())
        
        # Save combined dataset
        combined_path = os.path.join(self.processed_dir, 'combined_dataset.csv')
        combined_df.to_csv(combined_path, index=False)
        print(f"\n💾 Combined dataset saved to: {combined_path}")
        
        return combined_df
    
    def create_sample_dataset(self):
        """
        Fallback: Create a sample dataset if no real data is found
        """
        print("Creating sample phishing and legitimate email dataset...")
        
        # [Your existing sample creation code here]
        # (Keep the sample creation code from your original file)
        
        
    
    def load_dataset(self):
        """
        Main method to load dataset - tries real data first, falls back to samples
        """
        combined_path = os.path.join(self.processed_dir, 'combined_dataset.csv')
    
        if os.path.exists(combined_path):
            # Check if file is not empty
            if os.path.getsize(combined_path) > 0:
                print(f"Loading existing combined dataset from: {combined_path}")
                try:
                    df = pd.read_csv(combined_path)
                    print(f"✅ Loaded {len(df)} emails from existing dataset")
                    return df
                except Exception as e:
                    print(f"⚠️  Error reading existing dataset: {e}")
                    print("Creating new dataset...")
                    return self.load_and_combine_datasets()
            else:
                print(f"⚠️  Existing dataset file is empty. Creating new one...")
                os.remove(combined_path)  # Remove empty file
                return self.load_and_combine_datasets()
        else:
        # Load and combine all datasets
            return self.load_and_combine_datasets()

