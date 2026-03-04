"""
Module for feature extraction using TF-IDF and other techniques
"""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
import joblib
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MAX_FEATURES, NGRAM_RANGE, MODELS_DIR

class FeatureExtractor:
    """
    Class to handle feature extraction from text
    """
    
    def __init__(self, max_features=MAX_FEATURES, ngram_range=NGRAM_RANGE):
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words='english',
            lowercase=True,
            strip_accents='unicode',
            analyzer='word',
            min_df=2,  # Ignore terms that appear in less than 2 documents
            max_df=0.95  # Ignore terms that appear in more than 95% of documents
        )
        self.scaler = StandardScaler()
        self.feature_names = None
        
    def fit_transform_tfidf(self, texts):
        """
        Fit TF-IDF vectorizer and transform texts
        """
        print(f"Fitting TF-IDF vectorizer with max_features={self.max_features}...")
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
        self.feature_names = self.tfidf_vectorizer.get_feature_names_out()
        
        print(f"TF-IDF matrix shape: {tfidf_matrix.shape}")
        return tfidf_matrix
    
    def transform_tfidf(self, texts):
        """
        Transform texts using fitted TF-IDF vectorizer
        """
        return self.tfidf_vectorizer.transform(texts)
    
    def combine_features(self, tfidf_matrix, numeric_features):
        """
        Combine TF-IDF features with numeric engineered features
        """
        # Convert numeric features to numpy array if it's a DataFrame
        if isinstance(numeric_features, pd.DataFrame):
            numeric_features = numeric_features.values
        
        # Scale numeric features
        if not hasattr(self, 'scaler_fitted'):
            numeric_scaled = self.scaler.fit_transform(numeric_features)
            self.scaler_fitted = True
        else:
            numeric_scaled = self.scaler.transform(numeric_features)
        
        # Convert sparse TF-IDF matrix to dense for concatenation
        # (only if the combined size is manageable)
        if tfidf_matrix.shape[0] * (tfidf_matrix.shape[1] + numeric_scaled.shape[1]) < 10**7:  # Less than 10 million elements
            tfidf_dense = tfidf_matrix.toarray()
            combined = np.hstack([tfidf_dense, numeric_scaled])
        else:
            # Keep as sparse for large datasets
            from scipy.sparse import hstack, csr_matrix
            numeric_sparse = csr_matrix(numeric_scaled)
            combined = hstack([tfidf_matrix, numeric_sparse])
        
        print(f"Combined features shape: {combined.shape}")
        return combined
    
    def get_top_tfidf_features(self, texts, n=20):
        """
        Get top TF-IDF features for visualization
        """
        if self.tfidf_vectorizer is None:
            return []
        
        tfidf_matrix = self.transform_tfidf(texts)
        mean_tfidf = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
        
        top_indices = mean_tfidf.argsort()[-n:][::-1]
        top_features = [self.feature_names[i] for i in top_indices]
        top_scores = [mean_tfidf[i] for i in top_indices]
        
        return list(zip(top_features, top_scores))
    
    def save_vectorizer(self, filepath=None):
        """
        Save the fitted TF-IDF vectorizer
        """
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')
        
        joblib.dump(self.tfidf_vectorizer, filepath)
        print(f"Vectorizer saved to: {filepath}")
        
        if hasattr(self, 'scaler_fitted'):
            scaler_path = os.path.join(MODELS_DIR, 'feature_scaler.pkl')
            joblib.dump(self.scaler, scaler_path)
            print(f"Scaler saved to: {scaler_path}")
    
    def load_vectorizer(self, filepath=None):
        """
        Load a fitted TF-IDF vectorizer
        """
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')
        
        self.tfidf_vectorizer = joblib.load(filepath)
        self.feature_names = self.tfidf_vectorizer.get_feature_names_out()
        print(f"Vectorizer loaded from: {filepath}")
        
        # Try to load scaler
        scaler_path = os.path.join(MODELS_DIR, 'feature_scaler.pkl')
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            self.scaler_fitted = True
            print(f"Scaler loaded from: {scaler_path}")

# For testing
if __name__ == "__main__":
    from data_collection import DataCollector
    from preprocessing import DataPreprocessor
    
    # Load and preprocess data
    collector = DataCollector()
    df = collector.load_dataset()
    
    preprocessor = DataPreprocessor()
    df = preprocessor.preprocess_dataset(df)
    
    # Extract features
    extractor = FeatureExtractor()
    
    # Get cleaned texts
    texts = df['cleaned_text'].tolist()
    
    # Fit and transform TF-IDF
    tfidf_matrix = extractor.fit_transform_tfidf(texts)
    
    # Get numeric features
    numeric_features = df[['url_count', 'email_count', 'urgent_keyword_count', 
                          'text_length', 'word_count', 'avg_word_length',
                          'exclamation_count', 'all_caps_count']]
    
    # Combine features
    combined_features = extractor.combine_features(tfidf_matrix, numeric_features)
    
    # Get top features
    top_features = extractor.get_top_tfidf_features(texts, n=10)
    print("\nTop TF-IDF features:")
    for feature, score in top_features:
        print(f"  {feature}: {score:.4f}")
    
    print(f"\nFinal feature matrix shape: {combined_features.shape}")