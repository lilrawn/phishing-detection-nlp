"""
Main entry point for the Phishing Email Detection System
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules - use direct imports without 'src.' prefix
from src.data_collection import DataCollector
from src.preprocessing import DataPreprocessor
from src.feature_extraction import FeatureExtractor
from src.model_training import ModelTrainer
from src.evaluation import ModelEvaluator
from src.prediction_interface import PhishingPredictor, run_interactive_mode
from config import RESULTS_DIR, MODELS_DIR


def setup_environment():
    """
    Setup the environment and print configuration
    """
    print("\n" + "="*70)
    print("AI-POWERED PHISHING EMAIL DETECTION SYSTEM")
    print("Using Natural Language Processing (NLP)")
    print("="*70)
    
    print(f"\nSystem Configuration:")
    print(f"  - Data Directory: data/")
    print(f"  - Models Directory: {MODELS_DIR}")
    print(f"  - Results Directory: {RESULTS_DIR}")
    print(f"  - Python Version: {sys.version.split()[0]}")
    
    # Check for required packages
    try:
        import sklearn
        print(f"  - scikit-learn version: {sklearn.__version__}")
    except:
        print("  - scikit-learn: Not installed!")
    
    print("-"*70)

def train_pipeline():
    """
    Run the complete training pipeline
    """
    print("\n🚀 Starting Training Pipeline...")
    start_time = datetime.now()
    
    # Step 1: Data Collection
    print("\n📁 Step 1: Data Collection")
    collector = DataCollector()
    df = collector.load_dataset()
    print(f"   ✓ Loaded {len(df)} emails")
    
    # Step 2: Preprocessing
    print("\n🧹 Step 2: Text Preprocessing")
    preprocessor = DataPreprocessor()
    df = preprocessor.preprocess_dataset(df)
    print(f"   ✓ Preprocessed {len(df)} emails")
    
    # Step 3: Feature Extraction
    print("\n🔧 Step 3: Feature Extraction")
    extractor = FeatureExtractor()
    texts = df['cleaned_text'].tolist()
    
    # Get TF-IDF features only (these are non-negative)
    print("   Extracting TF-IDF features...")
    tfidf_matrix = extractor.fit_transform_tfidf(texts)
    
    # Get numeric features
    numeric_features = df[['url_count', 'email_count', 'urgent_keyword_count', 
                          'text_length', 'word_count', 'avg_word_length',
                          'exclamation_count', 'all_caps_count']].values
    
    print(f"   TF-IDF features shape: {tfidf_matrix.shape}")
    print(f"   Numeric features shape: {numeric_features.shape}")
    
    # Get labels
    y = df['label_encoded'].values
    
    # Split data first
    print("\n📊 Splitting data...")
    from sklearn.model_selection import train_test_split
    
    # Split indices to ensure same split across feature sets
    X_train_tfidf, X_test_tfidf, X_train_num, X_test_num, y_train, y_test = train_test_split(
        tfidf_matrix, numeric_features, y, 
        test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"   Training set size: {X_train_tfidf.shape[0]} samples")
    print(f"   Testing set size: {X_test_tfidf.shape[0]} samples")
    
    # Step 4: Model Training
    print("\n🤖 Step 4: Model Training")
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.ensemble import RandomForestClassifier
    from scipy.sparse import hstack, csr_matrix
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    
    results = {}
    models = {}
    
    # 1. Naive Bayes - ONLY uses TF-IDF (non-negative)
    print("\n📊 Training Naive Bayes...")
    nb_model = MultinomialNB(alpha=1.0)
    nb_model.fit(X_train_tfidf, y_train)
    y_pred_nb = nb_model.predict(X_test_tfidf)
    
    results['Naive Bayes'] = {
        'model': nb_model,
        'predictions': y_pred_nb,
        'accuracy': accuracy_score(y_test, y_pred_nb),
        'precision': precision_score(y_test, y_pred_nb),
        'recall': recall_score(y_test, y_pred_nb),
        'f1_score': f1_score(y_test, y_pred_nb)
    }
    print(f"   Accuracy: {results['Naive Bayes']['accuracy']:.4f}")
    print(f"   Precision: {results['Naive Bayes']['precision']:.4f}")
    print(f"   Recall: {results['Naive Bayes']['recall']:.4f}")
    print(f"   F1-Score: {results['Naive Bayes']['f1_score']:.4f}")
    
    # 2. Logistic Regression - uses combined features
    print("\n📊 Training Logistic Regression...")
    # Combine features for training
    X_train_combined = hstack([X_train_tfidf, csr_matrix(X_train_num)])
    X_test_combined = hstack([X_test_tfidf, csr_matrix(X_test_num)])
    
    lr_model = LogisticRegression(C=1.0, max_iter=1000, random_state=42, class_weight='balanced')
    lr_model.fit(X_train_combined, y_train)
    y_pred_lr = lr_model.predict(X_test_combined)
    
    results['Logistic Regression'] = {
        'model': lr_model,
        'predictions': y_pred_lr,
        'accuracy': accuracy_score(y_test, y_pred_lr),
        'precision': precision_score(y_test, y_pred_lr),
        'recall': recall_score(y_test, y_pred_lr),
        'f1_score': f1_score(y_test, y_pred_lr)
    }
    print(f"   Accuracy: {results['Logistic Regression']['accuracy']:.4f}")
    print(f"   Precision: {results['Logistic Regression']['precision']:.4f}")
    print(f"   Recall: {results['Logistic Regression']['recall']:.4f}")
    print(f"   F1-Score: {results['Logistic Regression']['f1_score']:.4f}")
    
    # 3. SVM - uses combined features
    print("\n📊 Training SVM...")
    svm_model = SVC(C=1.0, kernel='linear', probability=True, random_state=42, class_weight='balanced')
    svm_model.fit(X_train_combined, y_train)
    y_pred_svm = svm_model.predict(X_test_combined)
    
    results['SVM'] = {
        'model': svm_model,
        'predictions': y_pred_svm,
        'accuracy': accuracy_score(y_test, y_pred_svm),
        'precision': precision_score(y_test, y_pred_svm),
        'recall': recall_score(y_test, y_pred_svm),
        'f1_score': f1_score(y_test, y_pred_svm)
    }
    print(f"   Accuracy: {results['SVM']['accuracy']:.4f}")
    print(f"   Precision: {results['SVM']['precision']:.4f}")
    print(f"   Recall: {results['SVM']['recall']:.4f}")
    print(f"   F1-Score: {results['SVM']['f1_score']:.4f}")
    
    # 4. Random Forest - uses combined features
    print("\n📊 Training Random Forest...")
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight='balanced', n_jobs=-1)
    rf_model.fit(X_train_combined, y_train)
    y_pred_rf = rf_model.predict(X_test_combined)
    
    results['Random Forest'] = {
        'model': rf_model,
        'predictions': y_pred_rf,
        'accuracy': accuracy_score(y_test, y_pred_rf),
        'precision': precision_score(y_test, y_pred_rf),
        'recall': recall_score(y_test, y_pred_rf),
        'f1_score': f1_score(y_test, y_pred_rf)
    }
    print(f"   Accuracy: {results['Random Forest']['accuracy']:.4f}")
    print(f"   Precision: {results['Random Forest']['precision']:.4f}")
    print(f"   Recall: {results['Random Forest']['recall']:.4f}")
    print(f"   F1-Score: {results['Random Forest']['f1_score']:.4f}")
    
    # Find best model
    best_model_name = max(results, key=lambda x: results[x]['f1_score'])
    best_model = results[best_model_name]['model']
    
    print(f"\n{'='*50}")
    print(f"🏆 Best Model: {best_model_name}")
    print(f"   F1-Score: {results[best_model_name]['f1_score']:.4f}")
    print(f"   Accuracy: {results[best_model_name]['accuracy']:.4f}")
    print(f"{'='*50}")
    
    # Step 5: Save artifacts
    print("\n💾 Step 5: Saving Models and Vectorizers")
    
    # Save all models
    import joblib
    for name, res in results.items():
        filename = name.lower().replace(' ', '_')
        model_path = os.path.join(MODELS_DIR, f'{filename}_model.pkl')
        joblib.dump(res['model'], model_path)
        print(f"   Saved {name} to: {model_path}")
    
    # Save best model separately
    best_path = os.path.join(MODELS_DIR, 'best_model.pkl')
    joblib.dump(best_model, best_path)
    print(f"   Saved best model ({best_model_name}) to: {best_path}")
    
    # Save vectorizer
    extractor.save_vectorizer()
    
    # Step 6: Evaluation
    print("\n📊 Step 6: Model Evaluation")
    evaluator = ModelEvaluator()
    
    # Generate comparison table
    comparison_data = []
    for name, res in results.items():
        comparison_data.append({
            'Model': name,
            'Accuracy': f"{res['accuracy']:.4f}",
            'Precision': f"{res['precision']:.4f}",
            'Recall': f"{res['recall']:.4f}",
            'F1-Score': f"{res['f1_score']:.4f}"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    print("\n" + comparison_df.to_string(index=False))
    
    # Save comparison
    comparison_df.to_csv(os.path.join(RESULTS_DIR, 'model_comparison.csv'), index=False)
    
    # Create confusion matrices
    for name, res in results.items():
        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(y_test, res['predictions'])
        
        # Simple text output
        print(f"\n{name} Confusion Matrix:")
        print(cm)
    
    # Calculate training time
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "="*70)
    print(f"✅ TRAINING PIPELINE COMPLETE!")
    print(f"   Total time: {duration}")
    print(f"   Best model: {best_model_name} (F1: {results[best_model_name]['f1_score']:.4f})")
    print("="*70)
    
    return results