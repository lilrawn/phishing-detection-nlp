"""
Initialize the src package
"""
# Use relative imports within the package
from .data_collection import DataCollector
from .preprocessing import DataPreprocessor, TextPreprocessor
from .feature_extraction import FeatureExtractor
from .model_training import ModelTrainer
from .evaluation import ModelEvaluator
# predictor.py is intentionally not imported here: it pulls in the full ML
# stack (model, vectorizer, database) at import time, which the pipeline
# modules above don't need and which would slow down every `import src`.

__all__ = [
    'DataCollector',
    'DataPreprocessor',
    'TextPreprocessor',
    'FeatureExtractor',
    'ModelTrainer',
    'ModelEvaluator'
]