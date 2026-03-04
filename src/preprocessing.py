"""
Module for text preprocessing and cleaning
"""
import re
import pandas as pd
import numpy as np
import nltk
import spacy
from bs4 import BeautifulSoup
import sys
import os
import ssl

# Add this import to get URGENT_KEYWORDS from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import URGENT_KEYWORDS

# Fix SSL certificate issue for NLTK downloads
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download required NLTK data with error handling
def download_nltk_data():
    """Download NLTK data with error handling"""
    required_packages = ['stopwords', 'punkt', 'wordnet']
    for package in required_packages:
        try:
            nltk.data.find(f'tokenizers/{package}')
        except LookupError:
            print(f"Downloading {package}...")
            nltk.download(package, quiet=True)

# Call the download function
download_nltk_data()

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

# Load spaCy model (small model for efficiency)
try:
    nlp = spacy.load('en_core_web_sm')
except:
    print("Downloading spaCy model...")
    os.system('python -m spacy download en_core_web_sm --quiet')
    nlp = spacy.load('en_core_web_sm')

class TextPreprocessor:
    """
    Class for preprocessing email text
    """
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        self.urgent_keywords = URGENT_KEYWORDS  # Now this will work
        
        
    def clean_html(self, text):
        """
        Remove HTML tags from text
        """
        if pd.isna(text):
            return ""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text()
    
    def replace_urls(self, text):
        """
        Replace URLs with a token
        """
        url_pattern = r'https?://\S+|www\.\S+'
        return re.sub(url_pattern, ' <URL> ', text)
    
    def replace_emails(self, text):
        """
        Replace email addresses with a token
        """
        email_pattern = r'\S+@\S+'
        return re.sub(email_pattern, ' <EMAIL> ', text)
    
    def remove_special_chars(self, text):
        """
        Remove special characters and digits, keep letters and spaces
        """
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        return text
    
    def normalize_whitespace(self, text):
        """
        Remove extra whitespace and newlines
        """
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def tokenize(self, text):
        """
        Tokenize text into words
        """
        return word_tokenize(text.lower())
    
    def remove_stopwords(self, tokens):
        """
        Remove stopwords from tokens
        """
        return [token for token in tokens if token not in self.stop_words and len(token) > 2]
    
    def lemmatize_tokens(self, tokens):
        """
        Lemmatize tokens using WordNet
        """
        return [self.lemmatizer.lemmatize(token) for token in tokens]
    
    def extract_features(self, text):
        """
        Extract handcrafted features from text
        """
        features = {}
        text_lower = text.lower()
        
        # Count URLs
        features['url_count'] = len(re.findall(r'https?://\S+|www\.\S+', text))
        
        # Count email addresses
        features['email_count'] = len(re.findall(r'\S+@\S+', text))
        
        # Count urgent keywords
        urgent_count = 0
        for keyword in self.urgent_keywords:
            urgent_count += text_lower.count(keyword)
        features['urgent_keyword_count'] = urgent_count
        
        # Text length
        features['text_length'] = len(text)
        
        # Word count
        features['word_count'] = len(text.split())
        
        # Average word length
        words = text.split()
        if words:
            features['avg_word_length'] = sum(len(word) for word in words) / len(words)
        else:
            features['avg_word_length'] = 0
        
        # Count exclamation marks (often used in phishing)
        features['exclamation_count'] = text.count('!')
        
        # Count ALL CAPS words
        all_caps_count = sum(1 for word in text.split() if word.isupper() and len(word) > 1)
        features['all_caps_count'] = all_caps_count
        
        return features
    
    def preprocess_pipeline(self, text, extract_features=True):
        """
        Complete preprocessing pipeline
        """
        if pd.isna(text):
            text = ""
        
        # Convert to string if not already
        text = str(text)
        
        # Step 1: Clean HTML
        text = self.clean_html(text)
        
        # Step 2: Replace URLs and emails with tokens
        text = self.replace_urls(text)
        text = self.replace_emails(text)
        
        # Step 3: Remove special characters
        text = self.remove_special_chars(text)
        
        # Step 4: Normalize whitespace
        text = self.normalize_whitespace(text)
        
        # Step 5: Tokenize
        tokens = self.tokenize(text)
        
        # Step 6: Remove stopwords
        tokens = self.remove_stopwords(tokens)
        
        # Step 7: Lemmatize
        tokens = self.lemmatize_tokens(tokens)
        
        # Step 8: Reconstruct cleaned text
        cleaned_text = ' '.join(tokens)
        
        result = {'cleaned_text': cleaned_text}
        
        # Step 9: Extract features if requested
        if extract_features:
            features = self.extract_features(text)
            result.update(features)
        
        return result

class DataPreprocessor:
    """
    Class to handle dataset preprocessing
    """
    
    def __init__(self):
        self.text_preprocessor = TextPreprocessor()
        
    def preprocess_dataset(self, df, text_column='text', label_column='label'):
        """
        Preprocess entire dataset
        """
        print("Starting dataset preprocessing...")
        
        # Initialize columns for features
        feature_columns = ['url_count', 'email_count', 'urgent_keyword_count', 
                          'text_length', 'word_count', 'avg_word_length',
                          'exclamation_count', 'all_caps_count']
        
        for col in feature_columns:
            if col not in df.columns:
                df[col] = 0
        
        # Process each email
        cleaned_texts = []
        
        for idx, row in df.iterrows():
            if idx % 5 == 0:
                print(f"Processing email {idx+1}/{len(df)}")
            
            result = self.text_preprocessor.preprocess_pipeline(row[text_column])
            cleaned_texts.append(result['cleaned_text'])
            
            # Update feature columns
            for col in feature_columns:
                if col in result:
                    df.at[idx, col] = result[col]
        
        # Add cleaned text column
        df['cleaned_text'] = cleaned_texts
        
        # Remove rows with empty cleaned text
        df = df[df['cleaned_text'].str.len() > 0].reset_index(drop=True)
        
        # Encode labels
        df['label_encoded'] = (df[label_column] == 'phishing').astype(int)
        
        print(f"Preprocessing complete. {len(df)} emails processed.")
        print(f"Class distribution after preprocessing:\n{df[label_column].value_counts()}")
        
        return df

# For testing
if __name__ == "__main__":
    from data_collection import DataCollector
    
    # Load data
    collector = DataCollector()
    df = collector.load_dataset()
    
    # Preprocess
    preprocessor = DataPreprocessor()
    processed_df = preprocessor.preprocess_dataset(df)
    
    print("\nSample of processed data:")
    print(processed_df[['cleaned_text', 'label', 'url_count', 'urgent_keyword_count']].head())