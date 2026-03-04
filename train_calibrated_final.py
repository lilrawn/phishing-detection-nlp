#!/usr/bin/env python3
"""
Train a calibrated logistic regression model with proper probability scaling
"""
import sys
import os
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from scipy.sparse import hstack, csr_matrix
from sklearn.utils import class_weight

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.data_collection import DataCollector
from src.preprocessing import DataPreprocessor
from src.feature_extraction import FeatureExtractor
from config import MODELS_DIR

print("="*60)
print("🎯 TRAINING CALIBRATED LOGISTIC REGRESSION")
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

# Calculate class weights
class_weights = class_weight.compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
weight_dict = {0: class_weights[0], 1: class_weights[1]}
print(f"\n⚖️  Class weights: Legitimate={class_weights[0]:.2f}, Phishing={class_weights[1]:.2f}")

# Step 5: Train base model with best C from previous run
print("\n🤖 Training base model with C=10.0...")
base_model = LogisticRegression(
    C=10.0,
    max_iter=2000,
    random_state=42,
    class_weight='balanced',
    solver='liblinear'
)

base_model.fit(X_train_combined, y_train)

# Step 6: Calibrate the model
print("\n🔧 Calibrating probabilities...")
calibrated_model = CalibratedClassifierCV(
    base_model,
    cv=5,  # 5-fold cross-validation for calibration
    method='sigmoid'  # Platt scaling
)

calibrated_model.fit(X_train_combined, y_train)

# Step 7: Evaluate both models
print("\n📊 Evaluating models...")

# Base model predictions
y_pred_base = base_model.predict(X_test_combined)
y_prob_base = base_model.predict_proba(X_test_combined)[:, 1]

# Calibrated model predictions
y_pred_cal = calibrated_model.predict(X_test_combined)
y_prob_cal = calibrated_model.predict_proba(X_test_combined)[:, 1]

# Metrics for base model
f1_base = f1_score(y_test, y_pred_base)
acc_base = accuracy_score(y_test, y_pred_base)
prec_base = precision_score(y_test, y_pred_base)
rec_base = recall_score(y_test, y_pred_base)

# Metrics for calibrated model
f1_cal = f1_score(y_test, y_pred_cal)
acc_cal = accuracy_score(y_test, y_pred_cal)
prec_cal = precision_score(y_test, y_pred_cal)
rec_cal = recall_score(y_test, y_pred_cal)

print(f"\n{'='*60}")
print(f"Base Model (C=10.0):")
print(f"   F1-Score: {f1_base:.4f}")
print(f"   Accuracy: {acc_base:.4f}")
print(f"   Precision: {prec_base:.4f}")
print(f"   Recall: {rec_base:.4f}")
print()
print(f"Calibrated Model:")
print(f"   F1-Score: {f1_cal:.4f}")
print(f"   Accuracy: {acc_cal:.4f}")
print(f"   Precision: {prec_cal:.4f}")
print(f"   Recall: {rec_cal:.4f}")
print("="*60)

# Analyze probability distributions
print(f"\n📈 Probability Analysis:")

legit_probs_base = y_prob_base[y_test == 0]
phish_probs_base = y_prob_base[y_test == 1]

legit_probs_cal = y_prob_cal[y_test == 0]
phish_probs_cal = y_prob_cal[y_test == 1]

print(f"\nBase Model:")
print(f"   Legitimate emails - Mean: {np.mean(legit_probs_base):.3f}, Std: {np.std(legit_probs_base):.3f}")
print(f"   Phishing emails   - Mean: {np.mean(phish_probs_base):.3f}, Std: {np.std(phish_probs_base):.3f}")
print(f"   Legitimate 5th-95th percentile: {np.percentile(legit_probs_base, 5):.3f} - {np.percentile(legit_probs_base, 95):.3f}")
print(f"   Phishing 5th-95th percentile: {np.percentile(phish_probs_base, 5):.3f} - {np.percentile(phish_probs_base, 95):.3f}")

print(f"\nCalibrated Model:")
print(f"   Legitimate emails - Mean: {np.mean(legit_probs_cal):.3f}, Std: {np.std(legit_probs_cal):.3f}")
print(f"   Phishing emails   - Mean: {np.mean(phish_probs_cal):.3f}, Std: {np.std(phish_probs_cal):.3f}")
print(f"   Legitimate 5th-95th percentile: {np.percentile(legit_probs_cal, 5):.3f} - {np.percentile(legit_probs_cal, 95):.3f}")
print(f"   Phishing 5th-95th percentile: {np.percentile(phish_probs_cal, 5):.3f} - {np.percentile(phish_probs_cal, 95):.3f}")

# Calculate optimal threshold for calibrated model
from sklearn.metrics import precision_recall_curve
precision, recall, thresholds = precision_recall_curve(y_test, y_prob_cal)
f1_scores = 2 * (precision * recall) / (precision + recall + 1e-10)
optimal_idx = np.argmax(f1_scores[:-1])
optimal_threshold = thresholds[optimal_idx]

print(f"\n🎯 Optimal threshold for calibrated model: {optimal_threshold:.3f}")
print(f"   F1-score at optimal threshold: {f1_scores[optimal_idx]:.4f}")

# Save models
print("\n💾 Saving Models...")
os.makedirs(MODELS_DIR, exist_ok=True)

# Save both models
joblib.dump(base_model, os.path.join(MODELS_DIR, 'logistic_regression_base.pkl'))
joblib.dump(calibrated_model, os.path.join(MODELS_DIR, 'logistic_regression_calibrated.pkl'))
joblib.dump(calibrated_model, os.path.join(MODELS_DIR, 'best_model.pkl'))

# Save calibration info
calibration_info = {
    'base_model_f1': f1_base,
    'calibrated_model_f1': f1_cal,
    'optimal_threshold': optimal_threshold,
    'legit_mean_cal': np.mean(legit_probs_cal),
    'legit_std_cal': np.std(legit_probs_cal),
    'phish_mean_cal': np.mean(phish_probs_cal),
    'phish_std_cal': np.std(phish_probs_cal)
}
joblib.dump(calibration_info, os.path.join(MODELS_DIR, 'calibration_info.pkl'))

extractor.save_vectorizer()

print("\n✅ Training complete!")
print(f"   Calibrated model saved to: models/logistic_regression_calibrated.pkl")
print(f"   Calibration info saved to: models/calibration_info.pkl")

print("\n" + "="*60)
print(f"🚀 Recommended settings:")
print(f"   Model: Calibrated Logistic Regression")
print(f"   Threshold: {optimal_threshold:.3f}")
print(f"   Expected legitimate probability range: 0-30%")
print(f"   Expected phishing probability range: 70-100%")
print("   Run: python run_interactive.py")
print("="*60)
