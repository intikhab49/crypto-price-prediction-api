"""Configuration for model training and prediction."""

# Training constants
EPOCHS = 100
PATIENCE = 40  # Increased for slower convergence with lower learning rate
CLIP_GRAD_NORM = 0.5

# Model hyperparameters for different timeframes
TIMEFRAME_CONFIG = {
    "30m": {
        "lookback": 48,  # Reduced to 24 hours of data
        "hidden_size": 64,  # Keep current size
        "num_layers": 2,  # Keep current layers
        "dropout": 0.3,  # Keep current dropout
        "batch_size": 32,  # Increased from 16
        "learning_rate": 0.00005  # Already at 5e-5
    },
    "1h": {
        "lookback": 48,
        "hidden_size": 64,
        "num_layers": 2,
        "dropout": 0.2,
        "batch_size": 32,
        "learning_rate": 0.001
    },
    "4h": {
        "lookback": 36,
        "hidden_size": 64,
        "num_layers": 2,
        "dropout": 0.2,
        "batch_size": 32,
        "learning_rate": 0.001
    },
    "24h": {
        "lookback": 30,
        "hidden_size": 32,
        "num_layers": 2,
        "dropout": 0.2,
        "batch_size": 32,
        "learning_rate": 0.001
    }
} 