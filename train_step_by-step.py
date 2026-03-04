#!/usr/bin/env python3
"""
Train step by step to see where it might be hanging
"""
import sys
import os
import time
from src.data_collection import DataCollector
from src.preprocessing import DataPreprocessor
from src.feature_extraction import FeatureExtractor
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from scipy.sparse import hstack, csr_matrix
import joblib
from config import MODELS_DIR

print("="*60)
print("🚀 TRAINING PHISHING DETECTION MODEL (STEP BY STEP)")
print("="*60)

# Step 1: Data Collection
print("\n📁 Step 1/6: Loading Data...")
start = time.time()
collector = DataCollector()
df = collector.load_dataset()
print(f"   ✓ Loaded {len(df)} emails in {time.time()-start:.1f}s")

# Step 2: Preprocessing
print("\n🧹 Step 2/6: Preprocessing Data (this may take a few minutes)...")
start = time.time()
preprocessor = DataPreprocessor()
df = preprocessor.preprocess_dataset(df)
print(f"   ✓ Preprocessed {len(df)} emails in {time.time()-start:.1f}s")

# Step 3: Feature Extraction
print("\n🔧 Step 3/6: Extracting Features...")
start = time.time()
extractor = FeatureExtractor(max_features=2000)  # Reduced features for faster testing
texts = df['cleaned_text'].tolist()
tfidf_matrix = extractor.fit_transform_tfidf(texts)
numeric_features = df[['url_count', 'email_count', 'urgent_keyword_count', 
                      'text_length', 'word_count', 'avg_word_length',
                      'exclamation_count', 'all_caps_count']].values
y = df['label_encoded'].values
print(f"   ✓ Features extracted in {time.time()-start:.1f}s")
print(f"     TF-IDF shape: {tfidf_matrix.shape}")
print(f"     Numeric features shape: {numeric_features.shape}")

# Step 4: Split Data
print("\n📊 Step 4/6: Splitting Data...")
X_train_tfidf, X_test_tfidf, X_train_num, X_test_num, y_train, y_test = train_test_split(
    tfidf_matrix, numeric_features, y, test_size=0.2, random_state=42, stratify=y
)
print(f"   ✓ Training set: {X_train_tfidf.shape[0]} samples")
print(f"     Test set: {X_test_tfidf.shape[0]} samples")

# Step 5: Train Models
print("\n🤖 Step 5/6: Training Models...")

results = {}

# Naive Bayes
print("\n   Training Naive Bayes...")
start = time.time()
nb = MultinomialNB(alpha=1.0)
nb.fit(X_train_tfidf, y_train)
y_pred = nb.predict(X_test_tfidf)
results['Naive Bayes'] = {
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'f1': f1_score(y_test, y_pred)
}
print(f"     ✓ Completed in {time.time()-start:.1f}s")
print(f"       F1: {results['Naive Bayes']['f1']:.4f}")

# Prepare combined features for other models
print("\n   Preparing combined features...")
X_train_combined = hstack([X_train_tfidf, csr_matrix(X_train_num)])
X_test_combined = hstack([X_test_tfidf, csr_matrix(X_test_num)])

# Logistic Regression
print("\n   Training Logistic Regression...")
start = time.time()
lr = LogisticRegression(C=1.0, max_iter=1000, random_state=42, class_weight='balanced')
lr.fit(X_train_combined, y_train)
y_pred = lr.predict(X_test_combined)
results['Logistic Regression'] = {
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'f1': f1_score(y_test, y_pred)
}
print(f"     ✓ Completed in {time.time()-start:.1f}s")
print(f"       F1: {results['Logistic Regression']['f1']:.4f}")

# SVM
print("\n   Training SVM...")
start = time.time()
svm = SVC(C=1.0, kernel='linear', probability=True, random_state=42, class_weight='balanced')
svm.fit(X_train_combined, y_train)
y_pred = svm.predict(X_test_combined)
results['SVM'] = {
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'f1': f1_score(y_test, y_pred)
}
print(f"     ✓ Completed in {time.time()-start:.1f}s")
print(f"       F1: {results['SVM']['f1']:.4f}")

# Random Forest
print("\n   Training Random Forest...")
start = time.time()
rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight='balanced', n_jobs=-1)
rf.fit(X_train_combined, y_train)
y_pred = rf.predict(X_test_combined)
results['Random Forest'] = {
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'f1': f1_score(y_test, y_pred)
}
print(f"     ✓ Completed in {time.time()-start:.1f}s")
print(f"       F1: {results['Random Forest']['f1']:.4f}")

# Step 6: Save Models
print("\n💾 Step 6/6: Saving Models...")
os.makedirs(MODELS_DIR, exist_ok=True)

joblib.dump(nb, os.path.join(MODELS_DIR, 'naive_bayes_model.pkl'))
joblib.dump(lr, os.path.join(MODELS_DIR, 'logistic_regression_model.pkl'))
joblib.dump(svm, os.path.join(MODELS_DIR, 'svm_model.pkl'))
joblib.dump(rf, os.path.join(MODELS_DIR, 'random_forest_model.pkl'))
extractor.save_vectorizer()

# Find best model
best_model = max(results.items(), key=lambda x: x[1]['f1'])
print(f"\n{'='*60}")
print(f"🏆 BEST MODEL: {best_model[0]} (F1: {best_model[1]['f1']:.4f})")
print("="*60)

# Save best model separately
joblib.dump(svm if best_model[0] == 'SVM' else 
            lr if best_model[0] == 'Logistic Regression' else
            nb if best_model[0] == 'Naive Bayes' else rf,
            os.path.join(MODELS_DIR, 'best_model.pkl'))

print("\n✅ Training complete! Models saved to models/ directory")
print("   You can now run: python main.py --mode interactive")
