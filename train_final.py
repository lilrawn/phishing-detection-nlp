#!/usr/bin/env python3
"""
Final training script for phishing detection
"""
import sys
import os
import time
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from scipy.sparse import hstack, csr_matrix
from sklearn.utils import class_weight

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_collection import DataCollector
from src.preprocessing import DataPreprocessor
from src.feature_extraction import FeatureExtractor
from config import MODELS_DIR

print("="*60)
print("🎯 TRAINING PHISHING DETECTION MODEL")
print("="*60)

# 1. Load data
print("\n📁 Loading data...")
collector = DataCollector()
df = collector.load_dataset()

# 2. Preprocess
print("\n🧹 Preprocessing...")
preprocessor = DataPreprocessor()
df = preprocessor.preprocess_dataset(df)

# 3. Extract features
print("\n🔧 Extracting features...")
extractor = FeatureExtractor(max_features=2000)
texts = df['cleaned_text'].tolist()
tfidf = extractor.fit_transform_tfidf(texts)
numeric = df[['url_count', 'email_count', 'urgent_keyword_count',
              'text_length', 'word_count', 'avg_word_length',
              'exclamation_count', 'all_caps_count']].values
y = df['label_encoded'].values

print(f"   Classes: {np.bincount(y)}")
print(f"   Phishing: {np.sum(y==1)} ({np.sum(y==1)/len(y)*100:.1f}%)")

# 4. Split data
print("\n📊 Splitting data...")
X1_train, X1_test, X2_train, X2_test, y_train, y_test = train_test_split(
    tfidf, numeric, y, test_size=0.2, random_state=42, stratify=y
)

X_train = hstack([X1_train, csr_matrix(X2_train)])
X_test = hstack([X1_test, csr_matrix(X2_test)])

print(f"   Training: {X_train.shape[0]} samples")
print(f"   Test: {X_test.shape[0]} samples")

# 5. Train model
print("\n🤖 Training Logistic Regression...")
weights = class_weight.compute_class_weight('balanced', classes=[0,1], y=y_train)
base = LogisticRegression(C=10.0, max_iter=2000, random_state=42, 
                          class_weight='balanced', solver='liblinear')
base.fit(X_train, y_train)

# 6. Calibrate
print("🔧 Calibrating probabilities...")
model = CalibratedClassifierCV(base, cv=5, method='sigmoid')
model.fit(X_train, y_train)

# 7. Evaluate
print("\n📊 Evaluating...")
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

f1 = f1_score(y_test, y_pred)
acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred)
rec = recall_score(y_test, y_pred)

print(f"\n{'='*60}")
print(f"✅ Final Model Performance:")
print(f"   F1-Score:  {f1:.4f}")
print(f"   Accuracy:  {acc:.4f}")
print(f"   Precision: {prec:.4f}")
print(f"   Recall:    {rec:.4f}")
print("="*60)

# 8. Analyze probabilities
legit_probs = y_prob[y_test == 0]
phish_probs = y_prob[y_test == 1]

print(f"\n📈 Probability Analysis:")
print(f"   Legitimate: mean={np.mean(legit_probs):.3f}, 95% < {np.percentile(legit_probs, 95):.3f}")
print(f"   Phishing:   mean={np.mean(phish_probs):.3f}, 5% > {np.percentile(phish_probs, 5):.3f}")

# 9. Find optimal threshold
from sklearn.metrics import precision_recall_curve
precision, recall, thresholds = precision_recall_curve(y_test, y_prob)
f1_scores = 2 * (precision * recall) / (precision + recall + 1e-10)
optimal_idx = np.argmax(f1_scores[:-1])
optimal_threshold = thresholds[optimal_idx]

print(f"\n🎯 Optimal threshold: {optimal_threshold:.3f}")

# 10. Save everything
print("\n💾 Saving models...")
os.makedirs(MODELS_DIR, exist_ok=True)

joblib.dump(model, os.path.join(MODELS_DIR, 'phishing_model.pkl'))
joblib.dump(extractor.tfidf_vectorizer, os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl'))

info = {
    'threshold': optimal_threshold,
    'f1_score': f1,
    'accuracy': acc,
    'legit_mean': float(np.mean(legit_probs)),
    'phish_mean': float(np.mean(phish_probs))
}
joblib.dump(info, os.path.join(MODELS_DIR, 'model_info.pkl'))

print("\n✅ Training complete!")
print(f"   Model saved to: models/phishing_model.pkl")
print(f"   Threshold: {optimal_threshold:.3f}")
print("\n   Run: python -c 'from src.predictor import run_interactive; run_interactive()'")
