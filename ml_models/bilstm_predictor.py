import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import joblib
from config import settings
from sklearn.preprocessing import RobustScaler
import logging
import os
from datetime import datetime
import pytz
import torch.serialization
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import math
import torch.nn.functional as F

# Allowlist datetime.datetime and numpy scalar types for safe model loading
torch.serialization.add_safe_globals([
    datetime,
    np._core.multiarray.scalar,  # Add numpy scalar type
    np.dtype,  # Add numpy dtype
    np.ndarray,  # Add numpy array type
    np.bool_,  # Add numpy bool type
    np.float64,  # Add numpy float types
    np.float32,
    np.int64,  # Add numpy int types
    np.int32
])

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Updated feature list
FEATURE_LIST = [
    # Core price data
    'Open', 'High', 'Low', 'Close', 'Volume',
    
    # Moving averages and trends
    'SMA_20', 'EMA_20', 'RSI_14',
    
    # MACD components
    'MACD', 'MACD_Signal', 'MACD_Hist',
    
    # Bollinger Bands
    'Bollinger_middle', 'Bollinger_Upper', 'Bollinger_Lower',
    
    # Volume and price action
    'ATR', 'OBV', 'VWAP',
    
    # Momentum and volatility
    'Momentum', 'Volatility', 'Lag1', 'Sentiment_Up', 'ADX',
    
    # Stochastic and other oscillators
    'CCI', 'Stoch_%K', 'Stoch_%D', 'MFI'
]

def load_model(symbol, timeframe, input_size=16, hidden_size=32, num_layers=2):
    """Load pre-trained model and scaler"""
    model_path = f"models/{symbol}_{timeframe}_model.pth"
    scaler_path = f"models/{symbol}_{timeframe}_scaler.pkl"
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Model or scaler not found at {model_path}")
    
    # Get hyperparameters from config
    from controllers.timeframe_config import TIMEFRAME_MAP
    config = TIMEFRAME_MAP[timeframe]
    effective_hidden_size = config['hidden_size']
    effective_dropout = config['dropout']
    effective_num_layers = config['num_layers']
    
    model = BiLSTMWithAttention(
        input_size=input_size,
        hidden_size=effective_hidden_size,
        num_layers=effective_num_layers,
        dropout=effective_dropout
    )
    checkpoint = torch.load(model_path, map_location=torch.device('cpu'), weights_only=False)
    state_dict = checkpoint['model_state_dict'] if 'model_state_dict' in checkpoint else checkpoint
    model.load_state_dict(state_dict)
    scaler = joblib.load(scaler_path)
    model.eval()
    return model, scaler

class BiLSTMWithAttention(nn.Module):
    """Bidirectional LSTM with Attention mechanism"""
    def __init__(self, input_size, hidden_size=128, num_layers=2, dropout=0.3):
        super(BiLSTMWithAttention, self).__init__()
        
        # Store configuration
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout_rate = dropout
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Layer normalization for LSTM outputs
        self.layer_norm_lstm = nn.LayerNorm(hidden_size * 2)
        
        # Attention mechanism
        attention_hidden_size = hidden_size * 2  # Use full bidirectional hidden size
        self.attention_key = nn.Linear(attention_hidden_size, attention_hidden_size)
        self.attention_query = nn.Linear(attention_hidden_size, attention_hidden_size)
        self.attention_value = nn.Linear(attention_hidden_size, attention_hidden_size)
        
        # Layer normalization for attention outputs
        self.layer_norm_attn = nn.LayerNorm(attention_hidden_size)
        
        # Output layers with residual connections
        self.fc1 = nn.Linear(attention_hidden_size, attention_hidden_size)
        self.layer_norm_fc1 = nn.LayerNorm(attention_hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(attention_hidden_size, 1)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights with Xavier/Glorot initialization"""
        for name, param in self.named_parameters():
            if 'bias' in name:
                nn.init.zeros_(param)  # Initialize all biases to zero
            elif 'weight' in name: # Check if it's a weight parameter
                if 'layer_norm' in name: # Is it a LayerNorm weight?
                    nn.init.ones_(param)  # LayerNorm weights are typically init to 1
                elif param.dim() >= 2:     # Is it a 2D+ weight (Linear, LSTM)?
                    if 'lstm' in name:
                        nn.init.orthogonal_(param)
                    else: # Assume Linear weights for attention and fc layers
                        nn.init.xavier_uniform_(param)
                # Implicitly, 1D weights not part of LayerNorm or other 2D+ weights are left to default if any exist
            # Other parameters (if any) are left to default initialization
    
    def forward(self, x):
        """Forward pass with enhanced attention and residual connections"""
        # Ensure input has correct shape (batch_size, seq_len, input_size)
        if x.dim() == 2:
            x = x.unsqueeze(0)  # Add batch dimension if missing
        elif x.dim() == 1:
            x = x.unsqueeze(0).unsqueeze(0)  # Add batch and sequence dimensions
            
        # Log input shape for debugging
        logger.debug(f"Input shape at start of forward pass: {x.shape}")
        
        # LSTM layer
        lstm_out, _ = self.lstm(x)  # Shape: (batch_size, seq_len, 2*hidden_size)
        lstm_out = self.layer_norm_lstm(lstm_out)
        
        # Log LSTM output shape
        logger.debug(f"LSTM output shape: {lstm_out.shape}")
        
        # Self-attention mechanism
        batch_size, seq_len, hidden_dim = lstm_out.shape
        
        # Compute attention scores
        key = self.attention_key(lstm_out)    # Shape: (batch_size, seq_len, 2*hidden_size)
        query = self.attention_query(lstm_out) # Shape: (batch_size, seq_len, 2*hidden_size)
        value = self.attention_value(lstm_out) # Shape: (batch_size, seq_len, 2*hidden_size)
        
        # Log attention component shapes
        logger.debug(f"Attention shapes - key: {key.shape}, query: {query.shape}, value: {value.shape}")
        
        # Scaled dot-product attention
        scores = torch.bmm(query, key.transpose(1, 2)) / math.sqrt(hidden_dim)
        attention_weights = F.softmax(scores, dim=-1)
        
        # Apply attention
        context = torch.bmm(attention_weights, value)  # Shape: (batch_size, seq_len, 2*hidden_size)
        
        # Layer normalization and residual connection for attention
        context = self.layer_norm_attn(context)
        
        # Take the last timestep
        out = context[:, -1, :]  # Shape: (batch_size, 2*hidden_size)
        
        # First dense layer with residual connection
        residual = out
        out = self.fc1(out)
        out = F.relu(out)
        out = self.layer_norm_fc1(out + residual)
        out = self.dropout(out)
        
        # Final output layer
        out = self.fc2(out)  # Shape: (batch_size, 1)
        
        # Log final output shape
        logger.debug(f"Final output shape: {out.shape}")
        
        return out
    
    @staticmethod
    def load_from_checkpoint(checkpoint_path):
        """Load model from checkpoint with enhanced error handling and numpy type support"""
        try:
            # Load checkpoint with numpy scalar support
            checkpoint = torch.load(checkpoint_path, map_location=torch.device('cpu'), weights_only=False)
            
            # Extract model configuration, ensuring defaults if not found
            config = checkpoint.get('config', {}) # Prioritize 'config'
            if not config:
                # Try alternate key if 'config' is empty or not present
                config = checkpoint.get('model_config', {})
            
            # Ensure we have all required parameters with defaults
            input_size = config.get('input_size', 26)  # Default to 26 features
            hidden_size = config.get('hidden_size', 128)
            num_layers = config.get('num_layers', 2)
            dropout = float(config.get('dropout', 0.3)) # Ensure dropout is float
            feature_list = config.get('feature_list', None) # Get feature_list
            
            # Initialize model with configuration
            model = BiLSTMWithAttention(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                dropout=dropout
            )
            
            # Load state dict, handling both new and old format
            state_dict = checkpoint.get('model_state_dict', checkpoint)
            # If state_dict itself is a dictionary containing 'model_state_dict', use that inner one.
            if isinstance(state_dict, dict) and 'model_state_dict' in state_dict:
                state_dict = state_dict['model_state_dict']
            
            # Convert any numpy scalar types in state_dict to Python native types
            for key, value in state_dict.items():
                if isinstance(value, np.generic):
                    state_dict[key] = value.item()
            
            model.load_state_dict(state_dict)
            
            # Convert any numpy types in config to Python native types
            loaded_config = {
                'input_size': int(input_size) if isinstance(input_size, np.generic) else input_size,
                'hidden_size': int(hidden_size) if isinstance(hidden_size, np.generic) else hidden_size,
                'num_layers': int(num_layers) if isinstance(num_layers, np.generic) else num_layers,
                'dropout': float(dropout) if isinstance(dropout, np.generic) else dropout,
                'feature_list': feature_list,
                'best_epoch': config.get('best_epoch'),
                'best_metrics': config.get('best_metrics')
            }
            
            return model, loaded_config # Return model and the extracted/defaulted config
            
        except Exception as e:
            logger.error(f"Error loading checkpoint from {checkpoint_path}: {str(e)}")
            raise

def fetch_and_predict_btc_price(symbol="BTC", timeframe="1h"):
    """Fetch data and predict price for given timeframe"""
    from controllers.prediction import get_latest_data
    try:
        if timeframe not in settings.TIMEFRAME_MAP:
            raise ValueError(f"Invalid timeframe. Must be one of {list(settings.TIMEFRAME_MAP.keys())}")
        
        lookback = settings.TIMEFRAME_MAP[timeframe]["lookback"]
        
        df = get_latest_data(symbol, timeframe)
        
        model, scaler = load_model(symbol, timeframe, input_size=len(FEATURE_LIST))
        
        features = df[FEATURE_LIST].values
        scaled_features = scaler.transform(features)
        X_input = scaled_features[-lookback:].reshape(1, lookback, len(FEATURE_LIST))
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()  # Ensure model is in eval mode for prediction
        
        with torch.no_grad():
            predictions = []
            for _ in range(50):  # Monte Carlo dropout predictions
                pred = model(torch.FloatTensor(X_input).to(device))
                # Ensure prediction is properly shaped before converting to numpy
                if pred.dim() == 3:  # (batch, seq_len, 1)
                    pred = pred[:, -1, :]  # Take last timestep
                elif pred.dim() == 2:  # (batch, 1)
                    pass  # Already in correct shape
                pred = pred.cpu().numpy()
                predictions.append(pred)
            
            predictions = np.array(predictions)  # Shape: (50, batch_size, 1)
            prediction_scaled = np.mean(predictions, axis=0)  # Average across Monte Carlo samples
            confidence_interval = np.percentile(predictions, [5, 95], axis=0)
        
        # Ensure prediction has correct shape for inverse transform
        if prediction_scaled.ndim == 3:
            prediction_scaled = prediction_scaled.squeeze()  # Remove extra dimensions
        if prediction_scaled.ndim == 0:
            prediction_scaled = prediction_scaled.reshape(1,)
        elif prediction_scaled.ndim > 1:
            prediction_scaled = prediction_scaled.flatten()[:1]
        
        # Inverse transform predictions
        prediction = scaler.inverse_transform(
            np.concatenate([prediction_scaled.reshape(1, 1), np.zeros((1, len(FEATURE_LIST)-1))], axis=1)
        )[0, 0]
        ci_lower = scaler.inverse_transform(
            np.concatenate([confidence_interval[0].reshape(1, 1), np.zeros((1, len(FEATURE_LIST)-1))], axis=1)
        )[0, 0]
        ci_upper = scaler.inverse_transform(
            np.concatenate([confidence_interval[1].reshape(1, 1), np.zeros((1, len(FEATURE_LIST)-1))], axis=1)
        )[0, 0]
        
        last_actual_price = df['Close'].iloc[-1]
        time_delta = pd.Timedelta(hours=1 if timeframe != "24h" else 24)
        
        actuals, predictions = prepare_data_for_prediction(symbol, timeframe)
        mape = mean_absolute_error(actuals, predictions) / np.mean(np.abs(actuals)) * 100
        
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "predicted_price": float(prediction),
            "confidence_interval": [float(ci_lower), float(ci_upper)],
            "last_actual_price": float(last_actual_price),
            "prediction_time": (df.index[-1] + time_delta).isoformat(),
            "current_time": datetime.now(pytz.UTC).isoformat(),
            "rsi": float(df['RSI_14'].iloc[-1]),
            "adx": float(df['ADX'].iloc[-1]),
            "cci": float(df['CCI'].iloc[-1]),
            "price_source": "yfinance",
            "mape": float(mape)
        }
        logger.info(f"Predicted Price for {symbol} {timeframe}: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}", exc_info=True)
        raise

def prepare_data_for_prediction(symbol, timeframe="24h"):
    """Prepare data for evaluating model predictions"""
    from controllers.prediction import get_latest_data
    try:
        lookback = settings.TIMEFRAME_MAP[timeframe]["lookback"]
        latest_data = get_latest_data(symbol, timeframe)
        model, scaler = load_model(symbol, timeframe, input_size=len(FEATURE_LIST))
        model.eval()  # Ensure model is in eval mode
        
        features = latest_data[FEATURE_LIST].values
        scaled_features = scaler.transform(features)
        X = []
        for i in range(len(scaled_features) - lookback):
            X.append(scaled_features[i:i+lookback])
        X = np.array(X)
        if len(X) == 0:
            raise ValueError("Insufficient data for prediction")
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(device)
            predictions = model(X_tensor)
            # Ensure predictions have correct shape
            if predictions.dim() == 3:  # (batch, seq_len, 1)
                predictions = predictions[:, -1, :]  # Take last timestep
            predictions = predictions.cpu().numpy()
        
        # Ensure predictions have correct shape for inverse transform
        if predictions.ndim == 1:
            predictions = predictions.reshape(-1, 1)
        elif predictions.ndim > 2:
            predictions = predictions.reshape(predictions.shape[0], -1)
        
        predictions_denorm = scaler.inverse_transform(
            np.concatenate([predictions, np.zeros((len(predictions), len(FEATURE_LIST)-1))], axis=1)
        )[:, 0]
        
        actuals = latest_data['Close'].values[-len(predictions_denorm):]
        mae = mean_absolute_error(actuals, predictions_denorm)
        rmse = np.sqrt(mean_squared_error(actuals, predictions_denorm))
        r2 = r2_score(actuals, predictions_denorm)
        direction_correct = np.sum(np.sign(actuals[1:] - actuals[:-1]) == np.sign(predictions_denorm[1:] - predictions_denorm[:-1])) / (len(actuals) - 1)
        logger.info(f"Model performance - MAE: {mae:.2f}, RMSE: {rmse:.2f}, R2: {r2:.4f}, Directional Accuracy: {direction_correct:.4f}")
        
        return actuals, predictions_denorm
    except Exception as e:
        logger.error(f"Error in prepare_data_for_prediction: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        result = fetch_and_predict_btc_price(symbol="BTC", timeframe="1h")
        print(f"Prediction result: {result}")
    except Exception as e:
        print(f"Error: {str(e)}")