"""
Module for training and comparing machine learning models
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    TRAIN_TEST_SPLIT, RANDOM_STATE, MODELS_DIR,
    NAIVE_BAYES_ALPHA, LOGISTIC_REGRESSION_C, SVM_C,
    RANDOM_FOREST_N_ESTIMATORS, RANDOM_FOREST_MAX_DEPTH
)

class ModelTrainer:
    """
    Class to handle model training and comparison
    """
    
    def __init__(self, random_state=RANDOM_STATE):
        self.random_state = random_state
        self.models = {}
        self.results = {}
        self.best_model = None
        self.best_model_name = None
        
    def define_models(self):
        """
        Define the models to be trained
        """
        self.models = {
            'Naive Bayes': MultinomialNB(alpha=NAIVE_BAYES_ALPHA),
            'Logistic Regression': LogisticRegression(
                C=LOGISTIC_REGRESSION_C, 
                max_iter=1000, 
                random_state=self.random_state,
                class_weight='balanced'
            ),
            'SVM': SVC(
                C=SVM_C, 
                kernel='linear', 
                probability=True, 
                random_state=self.random_state,
                class_weight='balanced'
            ),
            'Random Forest': RandomForestClassifier(
                n_estimators=RANDOM_FOREST_N_ESTIMATORS,
                max_depth=RANDOM_FOREST_MAX_DEPTH,
                random_state=self.random_state,
                class_weight='balanced',
                n_jobs=-1
            )
        }
        
        print(f"Defined {len(self.models)} models for training")
        return self.models
    
    def split_data(self, features, labels, test_size=TRAIN_TEST_SPLIT):
        """
        Split data into training and testing sets
        """
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=test_size, 
            random_state=self.random_state, stratify=labels
        )
        
        print(f"Training set size: {X_train.shape[0]} samples")
        print(f"Testing set size: {X_test.shape[0]} samples")
        
        return X_train, X_test, y_train, y_test
    
    def prepare_features_for_model(self, X, model_name):
        """
        Prepare features appropriately for each model type
        """
        from scipy.sparse import issparse, csr_matrix
        
        if model_name == 'Naive Bayes':
            # Naive Bayes requires non-negative features
            # Convert to dense and clip negative values to 0
            if issparse(X):
                print(f"  ℹ️  Converting sparse to dense and clipping negatives for Naive Bayes")
                X_dense = X.toarray()
                X = np.maximum(X_dense, 0)
            else:
                # For dense arrays, clip negative values to 0
                if np.min(X) < 0:
                    print(f"  ℹ️  Clipping negative values for Naive Bayes")
                    X = np.maximum(X, 0)
            return X
        else:
            # Other models can handle negative values and sparse matrices
            return X
    
    def train_model(self, model_name, model, X_train, y_train, X_test, y_test):
        """
        Train a single model and evaluate
        """
        print(f"\nTraining {model_name}...")
        
        # Prepare features for this specific model
        X_train_prepared = self.prepare_features_for_model(X_train, model_name)
        X_test_prepared = self.prepare_features_for_model(X_test, model_name)
        
        # Train the model
        model.fit(X_train_prepared, y_train)
        
        # Make predictions
        y_pred = model.predict(X_test_prepared)
        
        # Get probability predictions if available
        y_proba = None
        if hasattr(model, 'predict_proba'):
            y_proba = model.predict_proba(X_test_prepared)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        
        # Perform cross-validation
        try:
            cv_scores = cross_val_score(model, X_train_prepared, y_train, cv=5, scoring='f1')
            cv_mean = cv_scores.mean()
            cv_std = cv_scores.std()
        except Exception as e:
            print(f"  ⚠️  Cross-validation skipped: {e}")
            cv_mean = 0
            cv_std = 0
        
        results = {
            'model': model,
            'predictions': y_pred,
            'probabilities': y_proba,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'cv_mean': cv_mean,
            'cv_std': cv_std,
            'classification_report': classification_report(y_test, y_pred)
        }
        
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1-Score: {f1:.4f}")
        if cv_mean > 0:
            print(f"  CV F1-Score: {cv_mean:.4f} (+/- {cv_std:.4f})")
        
        return results
    
    def train_all_models(self, X_train, y_train, X_test, y_test):
        """
        Train all defined models
        """
        if not self.models:
            self.define_models()
        
        self.results = {}
        
        for name, model in self.models.items():
            results = self.train_model(name, model, X_train, y_train, X_test, y_test)
            self.results[name] = results
        
        # Find best model based on F1 score
        self.best_model_name = max(self.results, key=lambda x: self.results[x]['f1_score'])
        self.best_model = self.results[self.best_model_name]['model']
        
        print(f"\n{'='*50}")
        print(f"Best Model: {self.best_model_name}")
        print(f"Best F1-Score: {self.results[self.best_model_name]['f1_score']:.4f}")
        print(f"Best Accuracy: {self.results[self.best_model_name]['accuracy']:.4f}")
        print(f"{'='*50}")
        
        return self.results
    
    def hyperparameter_tuning(self, X_train, y_train, model_name='SVM'):
        """
        Perform hyperparameter tuning for a specific model
        """
        print(f"\nPerforming hyperparameter tuning for {model_name}...")
        
        # Prepare features for the model
        X_train_prepared = self.prepare_features_for_model(X_train, model_name)
        
        if model_name == 'SVM':
            model = SVC(random_state=self.random_state, class_weight='balanced')
            param_grid = {
                'C': [0.1, 1, 10, 100],
                'kernel': ['linear', 'rbf'],
                'gamma': ['scale', 'auto']
            }
        elif model_name == 'Logistic Regression':
            model = LogisticRegression(max_iter=1000, random_state=self.random_state)
            param_grid = {
                'C': [0.01, 0.1, 1, 10],
                'penalty': ['l1', 'l2'],
                'solver': ['liblinear']
            }
        elif model_name == 'Random Forest':
            model = RandomForestClassifier(random_state=self.random_state)
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, None],
                'min_samples_split': [2, 5, 10]
            }
        else:
            print(f"Tuning not implemented for {model_name}")
            return None
        
        # Grid search with cross-validation
        grid_search = GridSearchCV(
            model, param_grid, cv=5, 
            scoring='f1', n_jobs=-1, verbose=1
        )
        
        grid_search.fit(X_train_prepared, y_train)
        
        print(f"Best parameters: {grid_search.best_params_}")
        print(f"Best cross-validation F1-score: {grid_search.best_score_:.4f}")
        
        return grid_search.best_estimator_
    
    def save_models(self):
        """
        Save all trained models
        """
        for name, results in self.results.items():
            model = results['model']
            model_path = os.path.join(MODELS_DIR, f"{name.lower().replace(' ', '_')}_model.pkl")
            joblib.dump(model, model_path)
            print(f"Saved {name} model to: {model_path}")
        
        # Save best model separately
        if self.best_model:
            best_path = os.path.join(MODELS_DIR, 'best_model.pkl')
            joblib.dump(self.best_model, best_path)
            print(f"Saved best model ({self.best_model_name}) to: {best_path}")
    
    def load_model(self, model_name):
        """
        Load a specific model
        """
        model_path = os.path.join(MODELS_DIR, f"{model_name.lower().replace(' ', '_')}_model.pkl")
        
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            print(f"Loaded model from: {model_path}")
            return model
        else:
            print(f"Model not found: {model_path}")
            return None