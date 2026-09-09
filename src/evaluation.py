"""
Module for evaluating and visualizing model performance
"""
import pandas as pd
import numpy as np
import matplotlib
# Every plot method here calls plt.show() after saving -- fine
# interactively, but this module now runs unattended from
# main.py's training pipeline, where the default GUI backend would open a
# window and block indefinitely waiting for someone to close it. Agg is
# save-only and makes plt.show() a harmless no-op; must be set before
# pyplot's first import.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, roc_curve, auc, precision_recall_curve
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RESULTS_DIR

class ModelEvaluator:
    """
    Class to evaluate and visualize model performance
    """
    
    def __init__(self, results_dir=RESULTS_DIR):
        self.results_dir = results_dir
        self.cm_dir = os.path.join(results_dir, 'confusion_matrices')
        self.viz_dir = os.path.join(results_dir, 'visualizations')
        
        # Create directories
        os.makedirs(self.cm_dir, exist_ok=True)
        os.makedirs(self.viz_dir, exist_ok=True)
        
    def plot_confusion_matrix(self, y_true, y_pred, model_name):
        """
        Plot confusion matrix for a model
        """
        cm = confusion_matrix(y_true, y_pred)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=['Legitimate', 'Phishing'],
                    yticklabels=['Legitimate', 'Phishing'])
        plt.title(f'Confusion Matrix - {model_name}')
        plt.ylabel('Actual')
        plt.xlabel('Predicted')
        
        # Save the plot
        filename = os.path.join(self.cm_dir, f'confusion_matrix_{model_name.lower().replace(" ", "_")}.png')
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        plt.show()
        plt.close()
        
        return cm
    
    def plot_roc_curve(self, y_true, y_proba, model_name):
        """
        Plot ROC curve for a model
        """
        if y_proba is None:
            print(f"No probability predictions for {model_name}")
            return None
        
        # For binary classification, use positive class probabilities
        if y_proba.ndim > 1 and y_proba.shape[1] > 1:
            y_score = y_proba[:, 1]
        else:
            y_score = y_proba
        
        fpr, tpr, _ = roc_curve(y_true, y_score)
        roc_auc = auc(fpr, tpr)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.2f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random Classifier')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title(f'ROC Curve - {model_name}')
        plt.legend(loc="lower right")
        plt.grid(True, alpha=0.3)
        
        # Save the plot
        filename = os.path.join(self.viz_dir, f'roc_curve_{model_name.lower().replace(" ", "_")}.png')
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        plt.show()
        plt.close()
        
        return roc_auc
    
    def plot_precision_recall_curve(self, y_true, y_proba, model_name):
        """
        Plot Precision-Recall curve
        """
        if y_proba is None:
            print(f"No probability predictions for {model_name}")
            return None
        
        # For binary classification, use positive class probabilities
        if y_proba.ndim > 1 and y_proba.shape[1] > 1:
            y_score = y_proba[:, 1]
        else:
            y_score = y_proba
        
        precision, recall, _ = precision_recall_curve(y_true, y_score)
        
        plt.figure(figsize=(8, 6))
        plt.plot(recall, precision, color='green', lw=2, label='Precision-Recall curve')
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title(f'Precision-Recall Curve - {model_name}')
        plt.legend(loc="lower left")
        plt.grid(True, alpha=0.3)
        
        # Save the plot
        filename = os.path.join(self.viz_dir, f'pr_curve_{model_name.lower().replace(" ", "_")}.png')
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        plt.show()
        plt.close()
    
    def create_comparison_table(self, results_dict):
        """
        Create a comparison table of all models
        """
        comparison_data = []
        
        for name, results in results_dict.items():
            comparison_data.append({
                'Model': name,
                'Accuracy': f"{results['accuracy']:.4f}",
                'Precision': f"{results['precision']:.4f}",
                'Recall': f"{results['recall']:.4f}",
                'F1-Score': f"{results['f1_score']:.4f}",
                'CV F1 (mean)': f"{results.get('cv_mean', 0):.4f}",
                'CV F1 (std)': f"{results.get('cv_std', 0):.4f}"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        # Save to CSV
        csv_path = os.path.join(self.results_dir, 'model_comparison.csv')
        comparison_df.to_csv(csv_path, index=False)
        print(f"Comparison table saved to: {csv_path}")
        
        return comparison_df
    
    def plot_model_comparison(self, results_dict):
        """
        Create bar chart comparing model performance
        """
        models = list(results_dict.keys())
        metrics = ['accuracy', 'precision', 'recall', 'f1_score']
        
        # Prepare data
        data = {}
        for metric in metrics:
            data[metric] = [results_dict[m][metric] for m in models]
        
        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(models))
        width = 0.2
        multiplier = 0
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        
        for metric, color in zip(metrics, colors):
            offset = width * multiplier
            bars = ax.bar(x + offset, data[metric], width, label=metric.capitalize(), color=color)
            multiplier += 1
        
        ax.set_xlabel('Models')
        ax.set_ylabel('Score')
        ax.set_title('Model Performance Comparison')
        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels(models, rotation=45, ha='right')
        ax.legend(loc='lower right')
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bars in ax.containers:
            ax.bar_label(bars, fmt='%.2f', fontsize=8)
        
        plt.tight_layout()
        
        # Save the plot
        filename = os.path.join(self.viz_dir, 'model_comparison.png')
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        plt.show()
        plt.close()
    
    def plot_feature_importance(self, model, feature_names, model_name, top_n=20):
        """
        Plot feature importance for tree-based models
        """
        if not hasattr(model, 'feature_importances_'):
            print(f"Model {model_name} does not have feature_importances_ attribute")
            return
        
        importances = model.feature_importances_
        
        # Get top N features
        indices = np.argsort(importances)[::-1][:top_n]
        top_features = [feature_names[i] if i < len(feature_names) else f"Feature_{i}" for i in indices]
        top_importances = importances[indices]
        
        plt.figure(figsize=(10, 8))
        plt.barh(range(top_n), top_importances[::-1], align='center')
        plt.yticks(range(top_n), top_features[::-1])
        plt.xlabel('Feature Importance')
        plt.title(f'Top {top_n} Feature Importances - {model_name}')
        plt.tight_layout()
        
        # Save the plot
        filename = os.path.join(self.viz_dir, f'feature_importance_{model_name.lower().replace(" ", "_")}.png')
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        plt.show()
        plt.close()
    
    def generate_evaluation_report(self, results_dict, y_test_dict=None):
        """
        Generate comprehensive evaluation report
        """
        print("\n" + "="*60)
        print("MODEL EVALUATION REPORT")
        print("="*60)
        
        # Create comparison table
        comparison_df = self.create_comparison_table(results_dict)
        print("\nModel Performance Summary:")
        print(comparison_df.to_string(index=False))
        
        # Find best model for each metric
        best_accuracy = max(results_dict.items(), key=lambda x: x[1]['accuracy'])
        best_precision = max(results_dict.items(), key=lambda x: x[1]['precision'])
        best_recall = max(results_dict.items(), key=lambda x: x[1]['recall'])
        best_f1 = max(results_dict.items(), key=lambda x: x[1]['f1_score'])
        
        print("\n" + "-"*40)
        print("BEST PERFORMERS:")
        print(f"Best Accuracy: {best_accuracy[0]} ({best_accuracy[1]['accuracy']:.4f})")
        print(f"Best Precision: {best_precision[0]} ({best_precision[1]['precision']:.4f})")
        print(f"Best Recall: {best_recall[0]} ({best_recall[1]['recall']:.4f})")
        print(f"Best F1-Score: {best_f1[0]} ({best_f1[1]['f1_score']:.4f})")
        print("-"*40)
        
        # Recommendations based on results
        print("\nRECOMMENDATIONS:")
        if best_f1[1]['f1_score'] > 0.95:
            print("✓ Excellent model performance - suitable for deployment")
        elif best_f1[1]['f1_score'] > 0.90:
            print("✓ Good performance - consider deployment with monitoring")
        elif best_f1[1]['f1_score'] > 0.85:
            print("⚠ Acceptable performance - may need improvement for production")
        else:
            print("✗ Model needs improvement - consider feature engineering or more data")
        
        # Check for class imbalance issues
        avg_recall = np.mean([r['recall'] for r in results_dict.values()])
        avg_precision = np.mean([r['precision'] for r in results_dict.values()])
        
        if avg_recall < 0.85:
            print("⚠ Low recall - model missing many phishing emails (high false negatives)")
        if avg_precision < 0.85:
            print("⚠ Low precision - many false alarms (high false positives)")
        
        print("="*60)
        
        return comparison_df

# For testing
if __name__ == "__main__":
    # This would be used after training models
    pass