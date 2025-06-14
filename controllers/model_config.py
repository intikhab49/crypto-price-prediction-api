"""Configuration for model training and hyperparameters."""

# Training constants
EPOCHS = 100
PATIENCE = 40  # Increased patience for thorough training
CLIP_GRAD_NORM = 1.0  # Maximum gradient norm for clipping

# Model hyperparameters for different timeframes
TIMEFRAME_CONFIG = {
    "30m": {
        "lookback": 48,  # 24 hours of 30m data
        "hidden_size": 64,  # Simpler architecture that performed better
        "num_layers": 2,  # Simpler architecture that performed better
        "dropout": 0.3,  # Moderate dropout
        "batch_size": 16,  # Smaller batch size that worked well
        "learning_rate": 0.0001  # Learning rate that gave best MAPE
    },
    "1h": {
        "lookback": 48,
        "hidden_size": 128,
        "num_layers": 2,
        "dropout": 0.2,
        "batch_size": 32,
        "learning_rate": 0.001
    },
    "4h": {
        "lookback": 36,
        "hidden_size": 128,
        "num_layers": 2,
        "dropout": 0.2,
        "batch_size": 32,
        "learning_rate": 0.001
    },
    "24h": {
        "lookback": 60,
        "hidden_size": 128,
        "num_layers": 2,
        "dropout": 0.2,
        "batch_size": 32,
        "learning_rate": 0.001
    }
} 