#!/usr/bin/env python3
"""
Train calibrated models for better probability estimates
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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from scipy.sparse import hstack, csr_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.data_collection import DataCollector
from src.preprocessing import DataPreprocessor
from src.feature_extraction import FeatureExtractor
from config import MODELS_DIR

print("="*60)
print("🎯 TRAINING CALIBRATED MODELS")
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

print(f"   Training set: {X_train_tfidf.shape[0]} samples")
print(f"   Test set: {X_test_tfidf.shape[0]} samples")

# Prepare combined features
X_train_combined = hstack([X_train_tfidf, csr_matrix(X_train_num)])
X_test_combined = hstack([X_test_tfidf, csr_matrix(X_test_num)])

print("\n🤖 Training Models...")
results = {}

# 1. Naive Bayes
print("\n   Training Naive Bayes...")
start = time.time()
nb = MultinomialNB(alpha=1.0)
nb.fit(X_train_tfidf, y_train)
y_pred = nb.predict(X_test_tfidf)
y_prob = nb.predict_proba(X_test_tfidf)[:, 1]
results['Naive Bayes'] = {
    'model': nb,
    'f1': f1_score(y_test, y_pred),
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'time': time.time() - start,
    'probabilities': y_prob
}
print(f"     ✓ {results['Naive Bayes']['time']:.1f}s, F1: {results['Naive Bayes']['f1']:.4f}")

# 2. Logistic Regression
print("\n   Training Logistic Regression...")
start = time.time()
lr = LogisticRegression(C=1.0, max_iter=1000, random_state=42, class_weight='balanced')
lr.fit(X_train_combined, y_train)
y_pred = lr.predict(X_test_combined)
y_prob = lr.predict_proba(X_test_combined)[:, 1]
results['Logistic Regression'] = {
    'model': lr,
    'f1': f1_score(y_test, y_pred),
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'time': time.time() - start,
    'probabilities': y_prob
}
print(f"     ✓ {results['Logistic Regression']['time']:.1f}s, F1: {results['Logistic Regression']['f1']:.4f}")

# 3. Calibrated LinearSVC (with probability calibration)
print("\n   Training Calibrated LinearSVC...")
start = time.time()
base_svm = LinearSVC(C=1.0, random_state=42, class_weight='balanced', max_iter=2000, dual=False)
# Calibrate to get proper probabilities
svm = CalibratedClassifierCV(base_svm, cv=5, method='sigmoid')
svm.fit(X_train_combined, y_train)
y_pred = svm.predict(X_test_combined)
y_prob = svm.predict_proba(X_test_combined)[:, 1]
results['LinearSVC (calibrated)'] = {
    'model': svm,
    'f1': f1_score(y_test, y_pred),
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'time': time.time() - start,
    'probabilities': y_prob
}
print(f"     ✓ {results['LinearSVC (calibrated)']['time']:.1f}s, F1: {results['LinearSVC (calibrated)']['f1']:.4f}")

# 4. Random Forest
print("\n   Training Random Forest...")
start = time.time()
rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight='balanced', n_jobs=-1)
rf.fit(X_train_combined, y_train)
y_pred = rf.predict(X_test_combined)
y_prob = rf.predict_proba(X_test_combined)[:, 1]
results['Random Forest'] = {
    'model': rf,
    'f1': f1_score(y_test, y_pred),
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'time': time.time() - start,
    'probabilities': y_prob
}
print(f"     ✓ {results['Random Forest']['time']:.1f}s, F1: {results['Random Forest']['f1']:.4f}")

# Find best model
best_model_name = max(results, key=lambda x: results[x]['f1'])
best_model = results[best_model_name]['model']

print(f"\n{'='*60}")
print(f"🏆 BEST MODEL: {best_model_name}")
print(f"   F1-Score: {results[best_model_name]['f1']:.4f}")
print(f"   Accuracy: {results[best_model_name]['accuracy']:.4f}")
print(f"   Precision: {results[best_model_name]['precision']:.4f}")
print(f"   Recall: {results[best_model_name]['recall']:.4f}")
print(f"   Training time: {results[best_model_name]['time']:.1f}s")
print("="*60)

# Show confusion matrix for best model
from sklearn.metrics import confusion_matrix
y_pred_best = best_model.predict(X_test_combined)
cm = confusion_matrix(y_test, y_pred_best)
print(f"\n📊 Confusion Matrix for {best_model_name}:")
print(f"   True Negatives: {cm[0,0]} | False Positives: {cm[0,1]}")
print(f"   False Negatives: {cm[1,0]} | True Positives: {cm[1,1]}")
print(f"   Accuracy: {(cm[0,0] + cm[1,1]) / cm.sum() * 100:.2f}%")

# Show probability distribution
print(f"\n📈 Probability Analysis for {best_model_name}:")
print(f"   Mean probability for legitimate: {np.mean(y_prob[y_test==0]):.3f}")
print(f"   Mean probability for phishing: {np.mean(y_prob[y_test==1]):.3f}")

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
print("-" * 60)
print(f"{'Model':<25} {'F1':<8} {'Acc':<8} {'Prec':<8} {'Rec':<8} {'Time':<8}")
print("-" * 60)
for name, metrics in results.items():
    print(f"{name:<25} {metrics['f1']:.4f}  {metrics['accuracy']:.4f}  {metrics['precision']:.4f}  {metrics['recall']:.4f}  {metrics['time']:.1f}s")

print("\n" + "="*60)
print("🚀 Run: python main.py --mode interactive")
print("="*60)
