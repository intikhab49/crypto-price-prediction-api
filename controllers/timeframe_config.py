"""Timeframe configuration for the application"""

TIMEFRAME_MAP = {
    "30m": {
        "period": "7d",
        "interval": "30m",
        "lookback": 48,  # 24 hours of 30m data
        "hidden_size": 64,  # Simpler architecture that performed better
        "num_layers": 2,  # Simpler architecture that performed better
        "dropout": 0.2,
        "batch_size": 64,
        "learning_rate": 1e-4,  # Initial LR for AdamW
        "max_lr": 1e-3,  # Max LR for OneCycleLR
        "early_stopping_patience": 20,
        "sma_window": 5,
        "ema_span": 6,
        "bb_window": 10,
        "momentum_window": 5,
        "rsi_window": 14,
        "min_samples": 672  # 7 days * 24 hours/day * 2 samples/hour (for 30m interval)
    },
    "1h": {
        "period": "30d",
        "interval": "1h",
        "lookback": 72,  # 3 days of hourly data, proven successful
        "hidden_size": 128,  # Successful architecture
        "num_layers": 2,  # Keep successful architecture
        "dropout": 0.3,  # Keep successful dropout
        "batch_size": 32,  # Proven successful batch size
        "learning_rate": 1e-4,  # Initial LR for AdamW
        "max_lr": 5e-5,  # Increased from 2e-5 for potentially faster convergence while maintaining stability
        "early_stopping_patience": 30,  # Reduced from 40 since best epoch was 7
        "sma_window": 12,  # Keep successful technical indicator settings
        "ema_span": 9,
        "bb_window": 20,
        "momentum_window": 10,
        "rsi_window": 14,
        "min_samples": 720  # 30 days * 24 hours/day
    },
    "4h": {
        "period": "90d",
        "interval": "4h",
        "lookback": 60,
        "hidden_size": 128,
        "num_layers": 2,
        "dropout": 0.3,
        "batch_size": 32,
        "learning_rate": 2e-5,
        "max_lr": 8e-5,
        "early_stopping_patience": 30,
        "sma_window": 5,
        "ema_span": 6,
        "bb_window": 10,
        "momentum_window": 5,
        "rsi_window": 14,
        "min_samples": 270  # 45 days * 6 samples/day (for 4h interval)
    },
    "24h": {
        "period": "365d",
        "interval": "1d",
        "lookback": 30,
        "hidden_size": 256,
        "num_layers": 3,
        "dropout": 0.4,
        "batch_size": 16,
        "learning_rate": 1e-5,
        "max_lr": 5e-5,
        "early_stopping_patience": 50,
        "sma_window": 20,
        "ema_span": 12,
        "bb_window": 20,
        "momentum_window": 14,
        "rsi_window": 14,
        "min_samples": 365  # 365 days
    }
} 