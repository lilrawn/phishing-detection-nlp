"""
Initialize the src package
"""
# Use relative imports within the package
from .data_collection import DataCollector
from .preprocessing import DataPreprocessor, TextPreprocessor
from .feature_extraction import FeatureExtractor
from .model_training import ModelTrainer
from .evaluation import ModelEvaluator
# Don't import from prediction_interface here to avoid circular imports

__all__ = [
    'DataCollector',
    'DataPreprocessor',
    'TextPreprocessor',
    'FeatureExtractor',
    'ModelTrainer',
    'ModelEvaluator'
]