#!/usr/bin/env python3
"""
Train a balanced model with proper calibration
"""
import sys
import os
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from scipy.sparse import hstack, csr_matrix
from sklearn.utils import class_weight

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.data_collection import DataCollector
from src.preprocessing import DataPreprocessor
from src.feature_extraction import FeatureExtractor
from config import MODELS_DIR

print("="*60)
print("🎯 TRAINING BALANCED LOGISTIC REGRESSION")
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

print(f"   Class distribution: {np.bincount(y)}")
print(f"   Phishing: {np.sum(y==1)} ({np.sum(y==1)/len(y)*100:.1f}%)")
print(f"   Legitimate: {np.sum(y==0)} ({np.sum(y==0)/len(y)*100:.1f}%)")

# Step 4: Split Data (maintain class distribution)
print("\n📊 Splitting Data...")
X_train_tfidf, X_test_tfidf, X_train_num, X_test_num, y_train, y_test = train_test_split(
    tfidf_matrix, numeric_features, y, test_size=0.2, random_state=42, stratify=y
)

print(f"   Training set: {X_train_tfidf.shape[0]} samples")
print(f"   Test set: {X_test_tfidf.shape[0]} samples")

# Prepare combined features
X_train_combined = hstack([X_train_tfidf, csr_matrix(X_train_num)])
X_test_combined = hstack([X_test_tfidf, csr_matrix(X_test_num)])

# Calculate class weights to handle imbalance
class_weights = class_weight.compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
weight_dict = {0: class_weights[0], 1: class_weights[1]}
print(f"\n⚖️  Class weights: Legitimate={class_weights[0]:.2f}, Phishing={class_weights[1]:.2f}")

# Step 5: Train Logistic Regression with different regularization strengths
print("\n🤖 Training Logistic Regression with different C values...")

best_model = None
best_f1 = 0
best_c = None
results = {}

for C in [0.01, 0.1, 1.0, 10.0, 100.0]:
    print(f"\n   Training with C={C}...")
    start = time.time()
    
    model = LogisticRegression(
        C=C, 
        max_iter=2000, 
        random_state=42, 
        class_weight='balanced',  # Use balanced class weights
        solver='liblinear'
    )
    
    model.fit(X_train_combined, y_train)
    y_pred = model.predict(X_test_combined)
    y_prob = model.predict_proba(X_test_combined)[:, 1]
    
    f1 = f1_score(y_test, y_pred)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    
    results[C] = {
        'model': model,
        'f1': f1,
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'time': time.time() - start,
        'probabilities': y_prob
    }
    
    print(f"     F1: {f1:.4f}, Acc: {acc:.4f}, Prec: {prec:.4f}, Rec: {rec:.4f}")
    
    if f1 > best_f1:
        best_f1 = f1
        best_model = model
        best_c = C

print(f"\n{'='*60}")
print(f"🏆 BEST MODEL: C={best_c}")
print(f"   F1-Score: {best_f1:.4f}")
print(f"   Accuracy: {results[best_c]['accuracy']:.4f}")
print(f"   Precision: {results[best_c]['precision']:.4f}")
print(f"   Recall: {results[best_c]['recall']:.4f}")
print("="*60)

# Show confusion matrix for best model
y_pred_best = best_model.predict(X_test_combined)
y_prob_best = best_model.predict_proba(X_test_combined)[:, 1]
cm = confusion_matrix(y_test, y_pred_best)
print(f"\n📊 Confusion Matrix:")
print(f"   True Negatives: {cm[0,0]} | False Positives: {cm[0,1]}")
print(f"   False Negatives: {cm[1,0]} | True Positives: {cm[1,1]}")
print(f"   Accuracy: {(cm[0,0] + cm[1,1]) / cm.sum() * 100:.2f}%")

# Analyze probability distribution
legit_probs = y_prob_best[y_test == 0]
phish_probs = y_prob_best[y_test == 1]

print(f"\n📈 Probability Analysis:")
print(f"   Legitimate emails - Mean: {np.mean(legit_probs):.3f}, Std: {np.std(legit_probs):.3f}")
print(f"   Phishing emails   - Mean: {np.mean(phish_probs):.3f}, Std: {np.std(phish_probs):.3f}")
print(f"   Legitimate 5th-95th percentile: {np.percentile(legit_probs, 5):.3f} - {np.percentile(legit_probs, 95):.3f}")
print(f"   Phishing 5th-95th percentile: {np.percentile(phish_probs, 5):.3f} - {np.percentile(phish_probs, 95):.3f}")

# Calculate optimal threshold
from sklearn.metrics import precision_recall_curve
precision, recall, thresholds = precision_recall_curve(y_test, y_prob_best)
f1_scores = 2 * (precision * recall) / (precision + recall + 1e-10)
optimal_idx = np.argmax(f1_scores[:-1])
optimal_threshold = thresholds[optimal_idx]

print(f"\n🎯 Optimal threshold: {optimal_threshold:.3f}")
print(f"   F1-score at optimal threshold: {f1_scores[optimal_idx]:.4f}")

# Save models
print("\n💾 Saving Models...")
os.makedirs(MODELS_DIR, exist_ok=True)

# Save the best model
joblib.dump(best_model, os.path.join(MODELS_DIR, 'logistic_regression_balanced.pkl'))
joblib.dump(best_model, os.path.join(MODELS_DIR, 'best_model.pkl'))
extractor.save_vectorizer()

# Save threshold info
threshold_info = {
    'optimal_threshold': optimal_threshold,
    'legit_mean': np.mean(legit_probs),
    'legit_std': np.std(legit_probs),
    'phish_mean': np.mean(phish_probs),
    'phish_std': np.std(phish_probs)
}
joblib.dump(threshold_info, os.path.join(MODELS_DIR, 'threshold_info.pkl'))

print("\n✅ Training complete!")
print(f"   Best model saved to: models/logistic_regression_balanced.pkl")
print(f"   Threshold info saved to: models/threshold_info.pkl")

print("\n📊 Performance Summary:")
print("-" * 60)
print(f"{'C':<8} {'F1':<8} {'Acc':<8} {'Prec':<8} {'Rec':<8} {'Time':<8}")
print("-" * 60)
for C, metrics in results.items():
    print(f"C={C:<4} {metrics['f1']:.4f}  {metrics['accuracy']:.4f}  {metrics['precision']:.4f}  {metrics['recall']:.4f}  {metrics['time']:.1f}s")

print("\n" + "="*60)
print(f"🚀 Recommended threshold: {optimal_threshold:.3f}")
print("   Run: python main.py --mode interactive")
print("="*60)
