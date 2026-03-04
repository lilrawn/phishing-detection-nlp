#!/usr/bin/env python3
"""
Test script to verify training pipeline works
"""
import sys
import os
from src.data_collection import DataCollector
from src.preprocessing import DataPreprocessor
from src.feature_extraction import FeatureExtractor

print("="*60)
print("🔍 TESTING TRAINING PIPELINE")
print("="*60)

# Test Data Collection
print("\n📁 Testing Data Collection...")
collector = DataCollector()
df = collector.load_dataset()
print(f"   ✓ Loaded {len(df)} emails")

# Test Preprocessing
print("\n🧹 Testing Preprocessing (first 10 emails only)...")
preprocessor = DataPreprocessor()
df_sample = df.head(10).copy()  # Just test with 10 emails
df_sample = preprocessor.preprocess_dataset(df_sample)
print(f"   ✓ Preprocessed {len(df_sample)} emails")

# Test Feature Extraction
print("\n🔧 Testing Feature Extraction...")
extractor = FeatureExtractor()
texts = df_sample['cleaned_text'].tolist()
tfidf_matrix = extractor.fit_transform_tfidf(texts)
print(f"   ✓ TF-IDF shape: {tfidf_matrix.shape}")

print("\n" + "="*60)
print("✅ All tests passed! Training pipeline should work.")
print("="*60)
