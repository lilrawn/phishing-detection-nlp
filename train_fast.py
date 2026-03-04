#!/usr/bin/env python3
"""
Fast training script using LinearSVC instead of full SVM
"""
import sys
import os
import time
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from scipy.sparse import hstack, csr_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.data_collection import DataCollector
from src.preprocessing import DataPreprocessor
from src.feature_extraction import FeatureExtractor
from config import MODELS_DIR

print("="*60)
print("🚀 FAST TRAINING (using LinearSVC)")
print("="*60)

# Step 1: Data Collection
print("\n📁 Loading Data...")
collector = DataCollector()
df = collector.load_dataset()

# Step 2: Preprocessing
print("\n🧹 Preprocessing...")
preprocessor = DataPreprocessor()
df = preprocessor.preprocess_dataset(df)

# Step 3: Feature Extraction
print("\n🔧 Extracting Features...")
extractor = FeatureExtractor(max_features=2000)
texts = df['cleaned_text'].tolist()
tfidf_matrix = extractor.fit_transform_tfidf(texts)
numeric_features = df[['url_count', 'email_count', 'urgent_keyword_count', 
                      'text_length', 'word_count', 'avg_word_length',
                      'exclamation_count', 'all_caps_count']].values
y = df['label_encoded'].values

# Step 4: Split Data
print("\n📊 Splitting Data...")
X_train_tfidf, X_test_tfidf, X_train_num, X_test_num, y_train, y_test = train_test_split(
    tfidf_matrix, numeric_features, y, test_size=0.2, random_state=42, stratify=y
)

# Step 5: Train Models
print("\n🤖 Training Models...")
results = {}

# 1. Naive Bayes
print("\n   Training Naive Bayes...")
start = time.time()
nb = MultinomialNB(alpha=1.0)
nb.fit(X_train_tfidf, y_train)
y_pred = nb.predict(X_test_tfidf)
results['Naive Bayes'] = {
    'f1': f1_score(y_test, y_pred),
    'time': time.time() - start
}
print(f"     ✓ {results['Naive Bayes']['time']:.1f}s, F1: {results['Naive Bayes']['f1']:.4f}")

# Prepare combined features
X_train_combined = hstack([X_train_tfidf, csr_matrix(X_train_num)])
X_test_combined = hstack([X_test_tfidf, csr_matrix(X_test_num)])

# 2. Logistic Regression
print("\n   Training Logistic Regression...")
start = time.time()
lr = LogisticRegression(C=1.0, max_iter=1000, random_state=42, class_weight='balanced')
lr.fit(X_train_combined, y_train)
y_pred = lr.predict(X_test_combined)
results['Logistic Regression'] = {
    'f1': f1_score(y_test, y_pred),
    'time': time.time() - start
}
print(f"     ✓ {results['Logistic Regression']['time']:.1f}s, F1: {results['Logistic Regression']['f1']:.4f}")

# 3. LinearSVC (FAST alternative to SVM)
print("\n   Training LinearSVC (fast SVM)...")
start = time.time()
svm = LinearSVC(C=1.0, random_state=42, class_weight='balanced', max_iter=2000, dual=False)
svm.fit(X_train_combined, y_train)
y_pred = svm.predict(X_test_combined)
results['LinearSVC'] = {
    'f1': f1_score(y_test, y_pred),
    'time': time.time() - start
}
print(f"     ✓ {results['LinearSVC']['time']:.1f}s, F1: {results['LinearSVC']['f1']:.4f}")

# 4. Random Forest
print("\n   Training Random Forest...")
start = time.time()
rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight='balanced', n_jobs=-1)
rf.fit(X_train_combined, y_train)
y_pred = rf.predict(X_test_combined)
results['Random Forest'] = {
    'f1': f1_score(y_test, y_pred),
    'time': time.time() - start
}
print(f"     ✓ {results['Random Forest']['time']:.1f}s, F1: {results['Random Forest']['f1']:.4f}")

# Find best model
best_model_name = max(results, key=lambda x: results[x]['f1'])
best_model = {
    'Naive Bayes': nb,
    'Logistic Regression': lr,
    'LinearSVC': svm,
    'Random Forest': rf
}[best_model_name]

print(f"\n{'='*60}")
print(f"🏆 BEST MODEL: {best_model_name}")
print(f"   F1-Score: {results[best_model_name]['f1']:.4f}")
print(f"   Training time: {results[best_model_name]['time']:.1f}s")
print("="*60)

# Save models
print("\n💾 Saving Models...")
os.makedirs(MODELS_DIR, exist_ok=True)

joblib.dump(nb, os.path.join(MODELS_DIR, 'naive_bayes_model.pkl'))
joblib.dump(lr, os.path.join(MODELS_DIR, 'logistic_regression_model.pkl'))
joblib.dump(svm, os.path.join(MODELS_DIR, 'svm_model.pkl'))
joblib.dump(rf, os.path.join(MODELS_DIR, 'random_forest_model.pkl'))
joblib.dump(best_model, os.path.join(MODELS_DIR, 'best_model.pkl'))
extractor.save_vectorizer()

print("\n✅ Training complete! Models saved to models/")
print("\n📊 Performance Summary:")
for name, metrics in results.items():
    print(f"   {name:20} F1: {metrics['f1']:.4f}  Time: {metrics['time']:.1f}s")

print("\nRun: python main.py --mode interactive")
