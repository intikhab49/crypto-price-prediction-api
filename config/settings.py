"""Global settings for the application."""
import os
from pathlib import Path
from typing import Dict
import secrets
from datetime import timedelta

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# JWT Settings
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))  # In production, always use environment variable
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Base paths
BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = str(BASE_DIR / "models")
CACHE_DIR = str(BASE_DIR / "cache")

# Set environment variables
os.environ['MODEL_PATH'] = MODEL_PATH
os.environ['CACHE_DIR'] = CACHE_DIR
os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
os.environ['COINGECKO_API_KEY'] = ''

# Ensure directories exist
Path(MODEL_PATH).mkdir(exist_ok=True)
Path(CACHE_DIR).mkdir(exist_ok=True)

# Model Configuration
SEQUENCE_LENGTH = 60
FEATURE_SIZE = 32
HIDDEN_SIZE = 128
NUM_LAYERS = 2
DROPOUT = 0.2
LEARNING_RATE = 0.001
EPOCHS = 100
BATCH_SIZE = 32

# Training Configuration
VALIDATION_SPLIT = 0.2
TEST_SPLIT = 0.1
EARLY_STOPPING_PATIENCE = 10
MIN_DELTA = 0.001

# Data Configuration
SYMBOLS = ["BTC", "ETH", "BNB", "XRP", "ADA", "DOGE", "SOL"]
TIMEFRAMES = ["30m", "1h", "4h", "24h"]
DEFAULT_TIMEFRAME = "1h"
TIMEFRAME_OPTIONS = TIMEFRAMES

# Technical Indicators
TECHNICAL_INDICATORS = [
    "RSI", "MACD", "BB_UPPER", "BB_MIDDLE", "BB_LOWER",
    "EMA_9", "SMA_20", "ATR", "OBV"
]

# Prediction Configuration
PREDICTION_HORIZON = 24  # hours
UNCERTAINTY_SAMPLES = 100  # Monte Carlo Dropout samples

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Performance Thresholds
MIN_ACCURACY = 0.55
MAX_LOSS = 0.1
MIN_DATA_POINTS = 1000

# API Configuration
API_V1_PREFIX = "/api/v1"

# CoinGecko API configuration
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
COINGECKO_PRO_URL = "https://api.coingecko.com/api/v3"  # Using regular API URL
COINGECKO_API_KEY = None  # Using free API

# Rate limiting settings
MAX_REQUESTS_PER_MINUTE = 10  # Reduced for free API
RATE_LIMIT_WINDOW = 60  # seconds

# Cache settings
CACHE_TTL = 300  # 5 minutes
MAX_CACHE_ITEMS = 1000

# Performance settings
MIN_MEMORY_GB = 4  # Use 4GB out of available 5GB RAM for training

# WebSocket settings
WS_UPDATE_INTERVAL = {
    "30m": 1800,    # 30 minutes
    "1h": 3600,     # 1 hour
    "4h": 14400,    # 4 hours
    "24h": 86400    # 24 hours
}
WS_MAX_ERRORS = 5  # Maximum number of consecutive errors before stopping updates
WS_MAX_CONNECTIONS_PER_USER = 3  # Maximum concurrent connections per user
WS_RECONNECT_DELAY = int(os.getenv('WS_RECONNECT_DELAY', '5'))

# WebSocket rate limits
WS_RATE_LIMITS: Dict[str, Dict[str, int]] = {
    "30m": {"requests": 30, "window": 60},  # 30 requests per minute
    "1h": {"requests": 20, "window": 60},   # 20 requests per minute
    "4h": {"requests": 10, "window": 60},   # 10 requests per minute
    "24h": {"requests": 5, "window": 60}    # 5 requests per minute
}

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')

# Timeframe specific settings
TIMEFRAME_MAP = {
    "30m": {
        "period": "7d",
        "interval": "30m",
        "lookback": 48,  # 24 hours worth of data
        "sma_window": 20,
        "ema_span": 12,
        "bb_window": 20,
        "momentum_window": 10,
        "rsi_window": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_sign": 9,
        "bb_std_dev": 2,
        "min_samples": 672,  # 7 days * 24 hours/day * 2 samples/hour
        "gap_threshold": 3600,  # 1 hour in seconds
        "model_params": {
            "hidden_size": 128,
            "num_layers": 2,
            "dropout": 0.2
        }
    },
    "1h": {
        "period": "30d",
        "interval": "1h",
        "lookback": 72,  # 3 days worth of data
        "sma_window": 20,
        "ema_span": 12,
        "bb_window": 20,
        "momentum_window": 10,
        "rsi_window": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_sign": 9,
        "bb_std_dev": 2,
        "min_samples": 720,  # 30 days * 24 hours/day
        "gap_threshold": 7200,  # 2 hours in seconds
        "model_params": {
            "hidden_size": 128,
            "num_layers": 2,
            "dropout": 0.2
        }
    },
    "4h": {
        "period": "90d",
        "interval": "4h",
        "lookback": 90,  # 15 days worth of data
        "sma_window": 20,
        "ema_span": 12,
        "bb_window": 20,
        "momentum_window": 10,
        "rsi_window": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_sign": 9,
        "bb_std_dev": 2,
        "min_samples": 540,  # 90 days * 6 samples/day
        "gap_threshold": 28800,  # 8 hours in seconds
        "model_params": {
            "hidden_size": 128,
            "num_layers": 2,
            "dropout": 0.2
        }
    },
    "24h": {
        "period": "730d",
        "interval": "1d",
        "lookback": 200,  # About 6.5 months of daily data
        "sma_window": 20,
        "ema_span": 12,
        "bb_window": 20,
        "momentum_window": 14,
        "rsi_window": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_sign": 9,
        "bb_std_dev": 2,
        "min_samples": 700,  # About 2 years of daily data
        "gap_threshold": 172800,  # 48 hours in seconds
        "model_params": {
            "hidden_size": 128,
            "num_layers": 2,
            "dropout": 0.2
        }
    }
}

# Update TIMEFRAME_OPTIONS to match TIMEFRAME_MAP
TIMEFRAME_OPTIONS = list(TIMEFRAME_MAP.keys())
DEFAULT_TIMEFRAME = "1h"

# Cache settings
CACHE_TIMEOUT: Dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "24h": 86400
}

# Data validation settings
MIN_DATA_POINTS = int(os.getenv('MIN_DATA_POINTS', '1000'))
MAX_MISSING_PERCENTAGE = float(os.getenv('MAX_MISSING_PERCENTAGE', '0.1'))
OUTLIER_STD_THRESHOLD = float(os.getenv('OUTLIER_STD_THRESHOLD', '3.0'))
MIN_DATA_QUALITY_SCORE_PREDICT = float(os.getenv('MIN_DATA_QUALITY_SCORE_PREDICT', '0.6'))

# Model training settings
MIN_TRAINING_SAMPLES = int(os.getenv('MIN_TRAINING_SAMPLES', '800'))

# API rate limiting
MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '30'))

# Debug mode
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

# Alpha Vantage API Key
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')

# List of required features for model input
REQUIRED_FEATURES = [
    "Open", "High", "Low", "Close", "Volume",
    "RSI", "MACD", "Bollinger_Upper", "Bollinger_middle", "Bollinger_Lower",
    "ATR", "OBV", "VWAP", "Momentum", "Volatility", "ADX", "CCI"
]

# Model settings
MODEL_RETRAIN_INTERVAL_DAYS = 7  # Retrain model if it's older than this many days