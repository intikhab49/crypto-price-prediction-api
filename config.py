from pydantic import BaseModel, SecretStr
import os
from dotenv import load_dotenv
from typing import List, Dict
from pathlib import Path
from controllers.timeframe_config import TIMEFRAME_MAP

load_dotenv()

class Settings(BaseModel):
    # Database settings
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite://./db.sqlite3')
    
    # JWT settings
    JWT_SECRET: SecretStr = SecretStr(os.getenv('JWT_SECRET') or os.urandom(32).hex())
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    
    # API settings
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "CryptoAion AI"
    BACKEND_CORS_ORIGINS: List[str] = os.getenv('BACKEND_CORS_ORIGINS', '').split(',') or ["http://localhost:5173", "http://localhost:3000"]
    
    # Data Validation Settings (Adjusted for API limitations)
    MIN_DATA_POINTS: int = int(os.getenv('MIN_DATA_POINTS', '100'))
    MIN_TRAINING_POINTS: int = int(os.getenv('MIN_TRAINING_POINTS', '500'))  # Reduced from 1500
    MAX_MISSING_PERCENTAGE: float = float(os.getenv('MAX_MISSING_PERCENTAGE', '0.10'))  # Increased from 0.05
    OUTLIER_STD_THRESHOLD: float = float(os.getenv('OUTLIER_STD_THRESHOLD', '3.5'))  # Increased from 3.0
    MIN_PRICE_POINTS: int = int(os.getenv('MIN_PRICE_POINTS', '500'))  # Reduced from 1000
    MIN_VOLUME_POINTS: int = int(os.getenv('MIN_VOLUME_POINTS', '500'))  # Reduced from 1000
    MAX_GAP_MINUTES: int = int(os.getenv('MAX_GAP_MINUTES', '120'))  # Increased from 60
    
    # Model Training Settings
    VALIDATION_SPLIT: float = float(os.getenv('VALIDATION_SPLIT', '0.2'))
    TEST_SPLIT: float = float(os.getenv('TEST_SPLIT', '0.1'))
    MIN_TRAINING_SAMPLES: int = int(os.getenv('MIN_TRAINING_SAMPLES', '500'))  # Reduced from 1500
    MODEL_PATH: str = os.getenv('MODEL_PATH', os.path.join(os.path.dirname(__file__), "models"))
    
    # Prediction settings
    DEFAULT_TIMEFRAME: str = "24h"
    TIMEFRAME_OPTIONS: List[str] = ["1m", "5m", "15m", "30m", "1h", "4h", "24h"]
    
    # WebSocket settings
    WS_UPDATE_INTERVAL: Dict[str, int] = {
        "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "4h": 14400, "24h": 86400
    }
    WS_MAX_ERRORS: int = int(os.getenv('WS_MAX_ERRORS', '5'))
    WS_RECONNECT_DELAY: int = int(os.getenv('WS_RECONNECT_DELAY', '5'))
    
    # External API settings
    COINGECKO_API_URL: str = os.getenv('COINGECKO_API_URL', 'https://api.coingecko.com/api/v3')
    COINGECKO_API_KEY: SecretStr = SecretStr(os.getenv('COINGECKO_API_KEY', ''))  # Demo API key
    COINGECKO_PRO_URL: str = os.getenv('COINGECKO_PRO_URL', 'https://api.coingecko.com/api/v3')
    
    # Cache settings
    CACHE_TIMEOUT: Dict[str, int] = {
        "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "4h": 14400, "24h": 86400
    }

    # Data Fetching Settings
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '50'))
    DEBUG_MODE: bool = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

    # New settings
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '32'))
    LOG_PATH: str = os.getenv('LOG_PATH', os.path.join(os.path.dirname(__file__), "logs"))
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_custom_rules(self):
        """Custom validation rules after Pydantic validation"""
        # Example: Check if API key is actually provided, not just an empty string from env
        if not self.COINGECKO_API_KEY.get_secret_value():
            # This could raise ValueError or log a warning
            print("Warning: COINGECKO_API_KEY is not set in environment.")
        # Add other custom checks if needed
        return True

# Define global constants first
FEATURE_LIST: Dict[str, float] = {
    # Core price data
    'Open': 1.0,
    'High': 1.0,
    'Low': 1.0,
    'Close': 1.0,
    'Volume': 0.9,
    
    # Moving averages and trends
    'SMA_20': 0.8,
    'EMA_20': 0.8,
    'RSI_14': 0.85,
    
    # MACD components
    'MACD': 0.85,
    'MACD_Signal': 0.8,
    'MACD_Hist': 0.8,
    
    # Bollinger Bands
    'Bollinger_middle': 0.75,
    'Bollinger_Upper': 0.75,
    'Bollinger_Lower': 0.75,
    
    # Volume and price action
    'ATR': 0.7,
    'OBV': 0.8,
    'VWAP': 0.85,
    
    # Momentum and volatility
    'Momentum': 0.9,
    'Volatility': 0.85,
    'Lag1': 0.7,
    'Sentiment_Up': 0.6,
    'ADX': 0.7,
    
    # Stochastic and other oscillators
    'CCI': 0.7,
    'Stoch_%K': 0.7,
    'Stoch_%D': 0.7,
    'MFI': 0.7
}

# Create necessary directories
Path(Settings.MODEL_PATH).mkdir(parents=True, exist_ok=True)
Path(Settings.LOG_PATH).mkdir(parents=True, exist_ok=True)

# Then, create the settings instance
try:
    settings = Settings()
    settings.validate_custom_rules() # Call custom validation if needed
except Exception as e:
    # Log this error properly in a real application
    print(f"CRITICAL: Configuration loading failed: {str(e)}")
    raise

# Any debug prints should ideally be conditional on settings.DEBUG_MODE
if settings.DEBUG_MODE:
    print(f"DEBUG (config.py): Loaded settings.MIN_PRICE_POINTS = {settings.MIN_PRICE_POINTS}", flush=True)
    print(f"DEBUG (config.py): TIMEFRAME_MAP['24h']['period'] = {TIMEFRAME_MAP.get('24h', {}).get('period')}", flush=True)
