"""
Configuration package for the cryptocurrency prediction system.
"""
from .settings import *

# Feature list with importance weights
FEATURE_LIST = {
    # Price data (Primary features)
    'Open': 1.0,
    'High': 1.0,
    'Low': 1.0,
    'Close': 1.0,
    'Volume': 0.9,
    
    # Technical indicators (Secondary features)
    'SMA_20': 0.8,
    'EMA_20': 0.8,
    'RSI_14': 0.85,
    'MACD': 0.85,
    'MACD_Signal': 0.8,
    'MACD_Hist': 0.8,
    
    # Bollinger Bands
    'Bollinger_middle': 0.75,
    'Bollinger_Upper': 0.75,
    'Bollinger_Lower': 0.75,
    
    # Additional indicators
    'ATR': 0.7,
    'OBV': 0.8,
    'VWAP': 0.85,
    'Stoch_%K': 0.7,
    'Stoch_%D': 0.7,
    'ADX': 0.7,
    'MFI': 0.7
}

# Tortoise ORM Settings
TORTOISE_ORM = {
    "connections": {"default": DATABASE_URL},
    "apps": {
        "models": {
            "models": ["models.user", "aerich.models"],
            "default_connection": "default",
        },
    },
}