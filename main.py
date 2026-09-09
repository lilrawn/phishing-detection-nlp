"""
Main entry point for the Phishing Email Detection System
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules - use direct imports without 'src.' prefix
from src.data_collection import DataCollector
from src.preprocessing import DataPreprocessor
from src.feature_extraction import FeatureExtractor
from src.evaluation import ModelEvaluator
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
    setup_environment()
    print("\n🚀 Starting Training Pipeline...")
    start_time = datetime.now()
    
    # Step 1: Data Collection
    print("\n📁 Step 1: Data Collection")
    collector = DataCollector()
    df = collector.load_dataset()
    print(f"   ✓ Loaded {len(df)} emails")

    # Step 1b: Fold in user-corrected feedback -- the whole point of
    # marking a prediction wrong in the dashboard is that the next
    # retrain should actually learn from it, not just log it. Only pulls
    # in emails the database has ground truth for: unlabeled scans the
    # user never corrected (label IS NULL, corrected_label IS NULL in
    # export_for_training's terms) are silently excluded, same as before.
    from src.database import db as _feedback_db
    feedback_df = _feedback_db.export_for_training(limit=10000)
    if not feedback_df.empty:
        before = len(df)
        feedback_df = feedback_df[['email_text', 'label']].rename(columns={'email_text': 'text'})
        feedback_df['source'] = 'user_feedback'
        df = pd.concat([df, feedback_df], ignore_index=True)
        df = df.drop_duplicates(subset=['text'], keep='last')  # corrections win over the original
        print(f"   ✓ Folded in {len(feedback_df)} corrected/labeled feedback email(s) from the "
              f"database ({len(df) - before} are new text not already in the static corpus; "
              f"the rest override an existing sample's label)")

    # Step 2: Preprocessing
    print("\n🧹 Step 2: Text Preprocessing")
    preprocessor = DataPreprocessor()
    df = preprocessor.preprocess_dataset(df)
    print(f"   ✓ Preprocessed {len(df)} emails")
    
    # Step 3: Data Splitting (BEFORE any feature fitting)
    print("\n📊 Step 3: Splitting data (BEFORE feature fitting to prevent leakage)...")
    from sklearn.model_selection import train_test_split
    
    # Get texts, numeric features, and labels
    texts = df['cleaned_text'].tolist()
    numeric_features = df[['url_count', 'email_count', 'urgent_keyword_count', 
                          'text_length', 'word_count', 'avg_word_length',
                          'exclamation_count', 'all_caps_count']].values
    y = df['label_encoded'].values
    
    # Split BEFORE fitting vectorizer or scaler
    texts_train, texts_test, numeric_train, numeric_test, y_train, y_test = train_test_split(
        texts, numeric_features, y,
        test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"   Training set size: {len(texts_train)} samples")
    print(f"   Testing set size: {len(texts_test)} samples")
    
    # Step 4: Feature Extraction (fit on training data ONLY)
    print("\n🔧 Step 4: Feature Extraction")
    extractor = FeatureExtractor()
    
    # Fit TF-IDF vectorizer ONLY on training texts
    print("   Fitting TF-IDF vectorizer on training data...")
    X_train_tfidf = extractor.fit_transform_tfidf(texts_train)
    
    # Transform test texts using the fitted vectorizer (no fitting)
    print("   Transforming test data with fitted vectorizer...")
    X_test_tfidf = extractor.transform_tfidf(texts_test)
    
    print(f"   TF-IDF features shape (train): {X_train_tfidf.shape}")
    print(f"   TF-IDF features shape (test): {X_test_tfidf.shape}")
    print(f"   Numeric features shape (train): {numeric_train.shape}")
    print(f"   Numeric features shape (test): {numeric_test.shape}")
     
    # Combine features: fit scaler on training data ONLY
    print("\n   Combining TF-IDF and numeric features (scaler fitted on train only)...")
    X_train_combined = extractor.combine_features(X_train_tfidf, numeric_train, fit=True)
    X_test_combined = extractor.combine_features(X_test_tfidf, numeric_test, fit=False)
    
    # Step 5: Model Training
    print("\n🤖 Step 5: Model Training")
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
    
    # Step 6: Save artifacts
    print("\n💾 Step 6: Saving Models and Vectorizers")
    
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
    
    # Step 7: Evaluation
    print("\n📊 Step 7: Model Evaluation")
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
    
    # Create confusion matrices -- saved to results/confusion_matrices/,
    # regenerated fresh on every run so they never go stale relative to
    # whatever model actually gets shipped (unlike the hand-maintained,
    # hardcoded confusion_matrix.png this replaced, which said "Logistic
    # Regression" long after SVM became the real best model).
    for name, res in results.items():
        cm = evaluator.plot_confusion_matrix(y_test, res['predictions'], name)

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


if __name__ == "__main__":
    train_pipeline()