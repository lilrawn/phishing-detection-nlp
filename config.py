"""
Configuration file for the Phishing Detection System
"""
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, 'processed')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')

# Create directories if they don't exist
for dir_path in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR, RESULTS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Data settings
TRAIN_TEST_SPLIT = 0.8
RANDOM_STATE = 42

# Feature extraction
MAX_FEATURES = 5000
NGRAM_RANGE = (1, 2)  # Use unigrams and bigrams

# Model parameters
NAIVE_BAYES_ALPHA = 1.0
LOGISTIC_REGRESSION_C = 1.0
SVM_C = 1.0
RANDOM_FOREST_N_ESTIMATORS = 100
RANDOM_FOREST_MAX_DEPTH = 10

# Evaluation metrics to use
METRICS = ['accuracy', 'precision', 'recall', 'f1_score']

# Phishing keywords for feature engineering
URGENT_KEYWORDS = [
    'urgent', 'immediately', 'verify', 'account', 'suspended', 
    'limited', 'click', 'update', 'confirm', 'security', 
    'unusual', 'login', 'password', 'bank', 'paypal', 
    'credit card', 'ssn', 'social security', 'verify your account',
    'suspended', 'locked', 'restricted', 'unusual activity'
]