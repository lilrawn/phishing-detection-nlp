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

# Phishing keywords for feature engineering. This list feeds
# urgent_keyword_count, one of the numeric features the trained model
# (models/best_model.pkl + tfidf_vectorizer.pkl) was fit on -- changing it
# shifts that feature's distribution away from what the model learned, so
# don't add entries here. New phishing vocabulary belongs in SCAM_PHRASES
# below instead, which is scored separately in the rule-based layer
# (src/predictor.py's _rule_score) and never touches the ML feature vector.
URGENT_KEYWORDS = [
    'urgent', 'immediately', 'verify', 'account', 'suspended',
    'limited', 'click', 'update', 'confirm', 'security',
    'unusual', 'login', 'password', 'bank', 'paypal',
    'credit card', 'ssn', 'social security', 'verify your account',
    'suspended', 'locked', 'restricted', 'unusual activity'
]

# Broader phishing/social-engineering vocabulary beyond the credential-
# phishing-focused URGENT_KEYWORDS above -- covers advance-fee/lottery
# scams, gift-card/wire-transfer requests, threat-based coercion, and
# authority impersonation, none of which URGENT_KEYWORDS catches (e.g. a
# classic 419 scam ships with none of "verify/suspended/login/password").
# Grouped by technique so predictor.py can name which pattern matched.
SCAM_PHRASES = {
    'advance_fee_or_inheritance': [
        'next of kin', 'unclaimed funds', 'unclaimed inheritance', 'beneficiary',
        'unclaimed lottery', 'lottery winner', "you have won", 'claim your prize',
        'claim your winnings', 'unclaimed prize', 'million dollars', 'million usd',
        'transfer the funds', 'transfer of funds', 'processing fee', 'clearance fee',
        'release the funds', 'release your funds', 'foreign partner', 'deceased client',
        'dear beneficiary', 'dear friend', 'dear winner', 'compensation fund',
        'diplomatic courier', 'abandoned funds',
    ],
    'payment_or_wire_request': [
        'gift card', 'gift cards', 'itunes card', 'google play card', 'steam card',
        'wire transfer', 'western union', 'moneygram', 'bitcoin payment',
        'crypto wallet', 'send payment', 'urgent payment', 'invoice attached',
        'overdue invoice', 'payment overdue', 'update your billing',
        'confirm your payment', 'wire the funds', 'routing number',
    ],
    'threat_or_coercion': [
        'legal action will be taken', 'you will be arrested', 'account will be closed',
        'account will be terminated', 'failure to comply', 'immediate action required',
        'final notice', 'final warning', 'we have your', 'i have access to your',
        'pay within 24 hours', 'pay within 48 hours', 'or else',
    ],
    'authority_impersonation': [
        'irs', 'internal revenue service', 'tax refund', 'social security administration',
        'court summons', 'law enforcement', 'fbi', 'department of justice',
        'your package could not be delivered', 'delivery failed', 'customs fee',
        'ceo request', 'wire transfer request from', 'hr department',
    ],
}

# Flattened for simple substring scanning; predictor.py also keeps the
# categorized form above to report which technique matched.
SCAM_PHRASES_FLAT = [phrase for phrases in SCAM_PHRASES.values() for phrase in phrases]

# Trusted senders: exact email addresses that should never themselves be
# flagged as a suspicious sender (still subject to link/attachment/body
# checks -- this only short-circuits the sender-domain check). Add your own
# verified addresses here.
TRUSTED_SENDERS = {
    'liron4908@gmail.com',
}

# File extensions phishing attachments commonly disguise themselves as or
# actually are. 'executable' types run code on open; 'macro_enabled' Office
# formats can run embedded macros; 'archive' formats are used to smuggle an
# executable past mail-scanner content inspection.
SUSPICIOUS_ATTACHMENT_EXTENSIONS = {
    'executable': {
        '.exe', '.scr', '.bat', '.cmd', '.com', '.pif', '.msi', '.msp',
        '.jar', '.js', '.jse', '.vbs', '.vbe', '.wsf', '.wsh', '.ps1',
        '.hta', '.app', '.gadget', '.cpl',
    },
    'macro_enabled_office': {
        '.docm', '.xlsm', '.pptm', '.dotm', '.xltm', '.potm',
    },
    'archive': {
        '.zip', '.rar', '.7z', '.iso', '.img',
    },
}
SUSPICIOUS_ATTACHMENT_EXTENSIONS_FLAT = {
    ext for exts in SUSPICIOUS_ATTACHMENT_EXTENSIONS.values() for ext in exts
}

# Add to existing config.py

# Desktop app settings
DESKTOP_CONFIG = {
    'check_interval': 30,  # seconds
    'notification_timeout': 5,  # seconds
    'max_history': 1000,  # max emails to store
    'sound_alerts': True,
    'auto_start': False
}

# Paths for desktop app
DESKTOP_DATA_DIR = os.path.join(BASE_DIR, 'desktop_app', 'data')
DESKTOP_LOGS_DIR = os.path.join(BASE_DIR, 'desktop_app', 'logs')

# Create directories
os.makedirs(DESKTOP_DATA_DIR, exist_ok=True)
os.makedirs(DESKTOP_LOGS_DIR, exist_ok=True)