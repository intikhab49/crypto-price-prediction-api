import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
import joblib
import logging
from datetime import datetime
import pytz
from typing import Tuple, Optional, Dict, Any, List
from config import settings
from .data_fetcher import DataFetcher
import ta
from pathlib import Path
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_percentage_error
import json
from .prediction_config import TIMEFRAME_CONFIG
from torch.utils.data import TensorDataset, DataLoader

# Setup logging
logger = logging.getLogger(__name__)

class BiLSTMWithAttention(nn.Module):
    def __init__(self, input_size: int = 21, hidden_size: int = 128, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        
        # Input validation
        if input_size <= 0 or hidden_size <= 0 or num_layers <= 0:
            raise ValueError("Invalid model parameters")
            
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout_rate = float(dropout)  # Store the actual dropout rate value
        
        # Input normalization
        self.input_norm = nn.LayerNorm(input_size)
        
        # Bidirectional LSTM with residual connections
        self.lstm_layers = nn.ModuleList([
            nn.LSTM(
                input_size=input_size if i == 0 else hidden_size * 2,
                hidden_size=hidden_size,
                num_layers=1,
                bidirectional=True,
                batch_first=True
            ) for i in range(num_layers)
        ])
        
        # Dropout layers
        self.dropouts = nn.ModuleList([
            nn.Dropout(p=float(self.dropout_rate)) for _ in range(num_layers)
        ])
        
        # Layer normalization after each LSTM
        self.layer_norms = nn.ModuleList([
            nn.LayerNorm(hidden_size * 2) for _ in range(num_layers)
        ])
        
        # Attention mechanism
        self.attention = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, 1)
        )
        
        # Output layers
        self.fc1 = nn.Linear(hidden_size * 2, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 1)
        self.output_activation = nn.Tanh()
    
    def forward(self, x):
        # Input shape: (batch_size, seq_length, input_size)
        batch_size = x.size(0)
        
        # Apply input normalization
        x = self.input_norm(x)
        
        # Process through LSTM layers with residual connections
        for i in range(self.num_layers):
            # LSTM layer
            lstm_out, _ = self.lstm_layers[i](x)
            
            # Residual connection if input size matches
            if i > 0 and x.size(-1) == lstm_out.size(-1):
                lstm_out = lstm_out + x
            
            # Layer normalization and dropout
            lstm_out = self.layer_norms[i](lstm_out)
            lstm_out = self.dropouts[i](lstm_out)
            
            x = lstm_out
        
        # Attention mechanism
        attention_weights = self.attention(x)  # (batch_size, seq_length, 1)
        attention_weights = torch.softmax(attention_weights, dim=1)
        context_vector = torch.bmm(attention_weights.transpose(1, 2), x)  # (batch_size, 1, hidden_size * 2)
        
        # Final prediction
        out = context_vector.squeeze(1)  # (batch_size, hidden_size * 2)
        out = self.fc1(out)  # (batch_size, hidden_size)
        out = torch.relu(out)
        out = self.dropouts[0](out)  # Reuse first dropout layer
        out = self.fc2(out)  # (batch_size, 1)
        out = self.output_activation(out)  # Scale to [-1, 1] range
        
        return out

class ModelTrainer:
    # Enhanced feature list with more technical indicators
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
    
    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.model_dir = Path(settings.MODEL_PATH) / symbol
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_path = self.model_dir / f'model_{timeframe}.pth'
        self.scaler_path = self.model_dir / f'scaler_{timeframe}.joblib'
        self.metadata_path = self.model_dir / f'metadata_{timeframe}.json'
        
        # Get config for this timeframe
        self.config = TIMEFRAME_CONFIG[timeframe]
        
        # Training parameters
        self.batch_size = self.config["batch_size"]
        self.validation_split = settings.VALIDATION_SPLIT
        self.patience = 40  # Increased patience for slower convergence
        self.max_epochs = 200
        self.min_data_points = 1000  # Minimum required data points
        
        # Initialize data fetcher
        self.data_fetcher = DataFetcher()
        
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators using the ta library"""
        try:
            # Basic price indicators
            df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
            df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
            
            # Momentum indicators
            df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14)
            macd = ta.trend.MACD(df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            df['MACD_Hist'] = macd.macd_diff()
            
            # Volatility indicators
            bollinger = ta.volatility.BollingerBands(df['Close'])
            df['Bollinger_middle'] = bollinger.bollinger_mavg()
            df['Bollinger_Upper'] = bollinger.bollinger_hband()
            df['Bollinger_Lower'] = bollinger.bollinger_lband()
            df['BB_Width'] = ((df['Bollinger_Upper'] - df['Bollinger_Lower']) / df['Bollinger_middle']) * 100
            
            df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'])
            
            # Volume indicators
            df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
            df['VWAP'] = ta.volume.volume_weighted_average_price(
                df['High'], df['Low'], df['Close'], df['Volume']
            )
            
            # Additional indicators
            stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'])
            df['Stoch_%K'] = stoch.stoch()
            df['Stoch_%D'] = stoch.stoch_signal()
            
            df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'])
            df['MFI'] = ta.volume.money_flow_index(
                df['High'], df['Low'], df['Close'], df['Volume']
            )
            
            # Add KAMA
            kama = ta.momentum.KAMAIndicator(df['Close'], window=10, pow1=2, pow2=30)
            df['KAMA'] = kama.kama()
            
            # Add TSI
            tsi = ta.momentum.TSIIndicator(df['Close'], window_slow=25, window_fast=13)
            df['TSI'] = tsi.tsi()
            
            # Add normalized price ratios
            df['Price_to_SMA'] = df['Close'] / df['SMA_20']
            df['HL_Range_Ratio'] = (df['High'] - df['Low']) / df['Close']
            df['Close_to_HL_Range'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
            
            # Forward fill and then backward fill any remaining NaN values
            df = df.ffill().bfill()
            
            return df[self.FEATURE_LIST]
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            raise
    
    def prepare_data(self) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, RobustScaler]:
        """Prepare data for training with enhanced validation"""
        try:
            # Fetch data with fallback mechanism
            data = self.data_fetcher.get_merged_data(self.symbol, self.timeframe)
            if data is None or len(data) < self.min_data_points:
                raise ValueError(f"Insufficient data points for {self.symbol}: got {len(data) if data is not None else 0}, require {self.min_data_points}")
            
            # Calculate technical indicators
            data = self._add_technical_indicators(data)
            
            # Validate data quality
            if data.isnull().any().any():
                raise ValueError("Data contains NaN values after preprocessing")
            
            if len(data) < self.min_data_points:
                raise ValueError(f"Insufficient data points after preprocessing: {len(data)}")
            
            # Scale features
            scaler = RobustScaler()
            scaled_data = scaler.fit_transform(data)
            
            # Create sequences with validation
            X, y = [], []
            # Get lookback from timeframe config
            lookback = self.config["lookback"]
            
            for i in range(len(scaled_data) - lookback - 1):
                X.append(scaled_data[i:i+lookback])
                y.append(scaled_data[i+lookback, data.columns.get_loc('Close')])
            
            X = np.array(X)
            y = np.array(y)
            
            if len(X) < 100:  # Minimum sequences required
                raise ValueError(f"Insufficient sequences generated: {len(X)}")
            
            # Split data with shuffling for better training
            indices = np.arange(len(X))
            np.random.shuffle(indices)
            split = int(len(indices) * (1 - self.validation_split))
            
            train_idx = indices[:split]
            val_idx = indices[split:]
            
            X_train = torch.FloatTensor(X[train_idx])
            y_train = torch.FloatTensor(y[train_idx])
            X_val = torch.FloatTensor(X[val_idx])
            y_val = torch.FloatTensor(y[val_idx])
            
            return X_train, y_train, X_val, y_val, scaler
            
        except Exception as e:
            logger.error(f"Error preparing data: {str(e)}")
            raise
        
    def train(self) -> Dict[str, Any]:
        """Train the model with enhanced monitoring and validation"""
        try:
            # Prepare data
            X_train, y_train, X_val, y_val, scaler = self.prepare_data()
            
            # Initialize model with size based on features
            input_size = len(self.FEATURE_LIST)
            model = BiLSTMWithAttention(
                input_size=input_size,
                hidden_size=self.config["hidden_size"],
                num_layers=self.config["num_layers"],
                dropout=self.config["dropout"]
            )
            
            # Move to GPU if available
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            model = model.to(device)
            X_train = X_train.to(device)
            y_train = y_train.to(device)
            X_val = X_val.to(device)
            y_val = y_val.to(device)
            
            # Loss function and optimizer with advanced training configuration
            criterion = nn.HuberLoss(delta=1.0)
            optimizer = optim.AdamW(
                model.parameters(),
                lr=self.config["learning_rate"],  # Use config learning rate
                weight_decay=0.01,  # L2 regularization
                betas=(0.9, 0.999),  # Default Adam betas
                eps=1e-8  # Default Adam epsilon
            )
            
            # Calculate steps per epoch and total steps
            steps_per_epoch = len(X_train) // self.batch_size
            total_steps = steps_per_epoch * self.max_epochs
            
            # OneCycleLR scheduler for better convergence
            scheduler = optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=self.config["learning_rate"] * 10,  # Peak learning rate (10x initial lr)
                total_steps=total_steps,
                pct_start=0.3,  # Warm up for 30% of training
                div_factor=10.0,  # Initial lr = max_lr/10
                final_div_factor=1000.0,  # Final lr = initial_lr/100
                anneal_strategy='cos'
            )
            
            # Training loop with enhanced monitoring
            best_val_loss = float('inf')
            best_r2_score = float('-inf')
            patience_counter = 0
            training_history = []
            best_model_state = None
            
            for epoch in range(self.max_epochs):
                model.train()
                train_loss = 0
                train_predictions = []
                train_actuals = []
                
                # Batch training with progress tracking
                for i in range(0, len(X_train), self.batch_size):
                    batch_X = X_train[i:i+self.batch_size]
                    batch_y = y_train[i:i+self.batch_size]
                    
                    optimizer.zero_grad()
                    output = model(batch_X)
                    loss = criterion(output.squeeze(), batch_y)
                    
                    # Backward pass with gradient clipping
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                    scheduler.step()
                    
                    train_loss += loss.item()
                    train_predictions.extend(output.squeeze().detach().cpu().numpy())
                    train_actuals.extend(batch_y.cpu().numpy())
                
                # Validation
                model.eval()
                val_loss = 0
                val_predictions = []
                val_actuals = []
                
                with torch.no_grad():
                    for i in range(0, len(X_val), self.batch_size):
                        batch_X = X_val[i:i+self.batch_size]
                        batch_y = y_val[i:i+self.batch_size]
                        
                        output = model(batch_X)
                        val_loss += criterion(output.squeeze(), batch_y).item()
                        
                        val_predictions.extend(output.squeeze().cpu().numpy())
                        val_actuals.extend(batch_y.cpu().numpy())
                
                # Calculate metrics
                train_loss /= (len(X_train) // self.batch_size)
                val_loss /= (len(X_val) // self.batch_size)
                
                # Convert lists to numpy arrays for metric calculation
                train_predictions = np.array(train_predictions)
                train_actuals = np.array(train_actuals)
                val_predictions = np.array(val_predictions)
                val_actuals = np.array(val_actuals)
                
                # Calculate R2 scores
                train_r2 = r2_score(train_actuals, train_predictions)
                val_r2 = r2_score(val_actuals, val_predictions)
                
                # Calculate MAPE
                train_mape = mean_absolute_percentage_error(train_actuals, train_predictions) * 100
                val_mape = mean_absolute_percentage_error(val_actuals, val_predictions) * 100
                
                # Calculate RMSE
                train_rmse = np.sqrt(mean_squared_error(train_actuals, train_predictions))
                val_rmse = np.sqrt(mean_squared_error(val_actuals, val_predictions))
                
                # Get current learning rate
                current_lr = scheduler.get_last_lr()[0]
                
                logger.info(
                    f"Epoch {epoch + 1}/{self.max_epochs}\n"
                    f"Train - Loss: {train_loss:.6f}, R2: {train_r2:.4f}, MAPE: {train_mape:.2f}%, RMSE: {train_rmse:.4f}\n"
                    f"Val   - Loss: {val_loss:.6f}, R2: {val_r2:.4f}, MAPE: {val_mape:.2f}%, RMSE: {val_rmse:.4f}\n"
                    f"Learning Rate: {current_lr:.8f}"
                )
                
                # Save training history
                training_history.append({
                    'epoch': epoch + 1,
                    'train_loss': float(train_loss),
                    'val_loss': float(val_loss),
                    'train_r2': float(train_r2),
                    'val_r2': float(val_r2),
                    'train_mape': float(train_mape),
                    'val_mape': float(val_mape),
                    'train_rmse': float(train_rmse),
                    'val_rmse': float(val_rmse),
                    'learning_rate': float(current_lr)
                })
                
                # Early stopping check - prioritize R2 improvement
                improved = False
                
                # Check if R2 score improved
                if val_r2 > best_r2_score:
                    best_r2_score = val_r2
                    improved = True
                    best_model_state = model.state_dict().copy()
                    
                    # Save best model
                    torch.save({
                        'epoch': epoch + 1,
                        'model_state_dict': model.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict(),
                        'scheduler_state_dict': scheduler.state_dict(),
                        'val_loss': val_loss,
                        'val_r2': val_r2,
                        'val_mape': val_mape,
                        'train_loss': train_loss,
                        'train_r2': train_r2,
                        'train_mape': train_mape,
                        'rmse': val_rmse,
                        'learning_rate': current_lr
                    }, self.model_path)
                    
                    # Save scaler
                    joblib.dump(scaler, self.scaler_path)
                # If R2 didn't improve but loss did significantly
                elif val_loss < best_val_loss * 0.95:  # 5% improvement threshold
                    best_val_loss = val_loss
                    improved = True
                
                if not improved:
                    patience_counter += 1
                    if patience_counter >= self.patience:
                        logger.info(f"Early stopping triggered after {epoch + 1} epochs")
                        break
                else:
                    patience_counter = 0
                
                # Save training curves after each epoch
                curves_path = self.model_dir / f'training_curves_{self.timeframe}.json'
                with open(curves_path, 'w') as f:
                    json.dump(training_history, f, indent=2)
            
            # Load best model state
            if best_model_state is not None:
                model.load_state_dict(best_model_state)
            
            # Save final training metadata
            metadata = {
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'training_date': datetime.now(pytz.UTC).isoformat(),
                'epochs_trained': epoch + 1,
                'best_val_loss': float(best_val_loss),
                'best_val_r2': float(best_r2_score),
                'final_val_mape': float(val_mape),
                'final_rmse': float(val_rmse),
                'data_points': len(X_train) + len(X_val),
                'feature_list': self.FEATURE_LIST,
                'model_parameters': {
                    'input_size': input_size,
                    'hidden_size': self.config["hidden_size"],
                    'num_layers': self.config["num_layers"],
                    'dropout': self.config["dropout"],
                    'batch_size': self.batch_size,
                    'learning_rate': self.config["learning_rate"],
                    'weight_decay': 0.01
                },
                'training_history': training_history
            }
            
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                'status': 'success',
                'epochs_trained': epoch + 1,
                'best_val_loss': float(best_val_loss),
                'best_val_r2': float(best_r2_score),
                'final_val_mape': float(val_mape),
                'final_rmse': float(val_rmse),
                'model_path': str(self.model_path),
                'data_points': len(X_train) + len(X_val),
                'validation_metrics': {
                    'rmse': float(val_rmse),
                    'r2': float(val_r2),
                    'mape': float(val_mape)
                }
            }
            
        except Exception as e:
            logger.error(f"Training error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

def train_model(X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray, 
                model: BiLSTMWithAttention, timeframe: str = "24h", symbol: str = "BTC",
                batch_size: int = 32, learning_rate: float = 0.001) -> BiLSTMWithAttention:
    """Train the model with early stopping and enhanced monitoring"""
    try:
        # Define constants
        EPOCHS = 100  # Maximum number of epochs
        PATIENCE = 20  # Increased patience for early stopping (was 15)
        CLIP_GRAD_NORM = 1.0  # Maximum gradient norm for clipping
        
        logger.info(f"Starting model training for {symbol} {timeframe}")
        logger.info(f"Training data shape: X_train {X_train.shape}, y_train {y_train.shape}")
        logger.info(f"Validation data shape: X_val {X_val.shape}, y_val {y_val.shape}")
        logger.info(f"Model hyperparameters: batch_size={batch_size}, learning_rate={learning_rate}")
        
        # Initialize lists to store metrics for plotting
        train_losses = []
        val_losses = []
        val_mapes = []
        val_rmses = []
        val_r2s = []
        
        # Convert data to tensors and ensure correct shape
        X_train_tensor = torch.FloatTensor(X_train)
        y_train_tensor = torch.FloatTensor(y_train).reshape(-1)  # Flatten to 1D
        X_val_tensor = torch.FloatTensor(X_val)
        y_val_tensor = torch.FloatTensor(y_val).reshape(-1)  # Flatten to 1D
        
        # Create data loaders
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # Initialize optimizer and scheduler
        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)
        
        # Loss function
        criterion = nn.MSELoss()
        
        # Early stopping variables
        best_val_loss = float('inf')
        best_model_state = None
        patience_counter = 0
        
        # Training loop
        for epoch in range(EPOCHS):
            model.train()
            total_train_loss = 0
            num_batches = 0
            
            # Training phase
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                
                # Forward pass
                outputs = model(batch_X)
                # Ensure both tensors are the same shape before computing loss
                outputs = outputs.view(-1)  # Flatten predictions
                batch_y = batch_y.view(-1)  # Flatten targets
                loss = criterion(outputs, batch_y)
                
                # Backward pass
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP_GRAD_NORM)
                
                # Optimizer step
                optimizer.step()
                
                total_train_loss += loss.item()
                num_batches += 1
            
            avg_train_loss = total_train_loss / num_batches
            
            # Validation phase
            model.eval()
            with torch.no_grad():
                val_outputs = model(X_val_tensor)
                # Ensure both tensors are the same shape before computing loss
                val_outputs = val_outputs.view(-1)  # Flatten predictions
                y_val_tensor_reshaped = y_val_tensor.view(-1)  # Flatten targets
                val_loss = criterion(val_outputs, y_val_tensor_reshaped)
                
                # Calculate additional metrics
                val_mape = mean_absolute_percentage_error(y_val_tensor_reshaped.numpy(), val_outputs.numpy())
                val_rmse = np.sqrt(mean_squared_error(y_val_tensor_reshaped.numpy(), val_outputs.numpy()))
                val_r2 = r2_score(y_val_tensor_reshaped.numpy(), val_outputs.numpy())
            
            # Monitor training data quality
            monitor_training_data_quality(model, X_train_tensor, y_train_tensor, X_val_tensor, y_val_tensor, epoch)
            
            # Store metrics
            train_losses.append(avg_train_loss)
            val_losses.append(val_loss.item())
            val_mapes.append(val_mape)
            val_rmses.append(val_rmse)
            val_r2s.append(val_r2)
            
            # Update learning rate
            scheduler.step(val_loss)
            
            # Log progress
            logger.info(f"Epoch {epoch} - Training Data Stats: {get_data_stats(X_train_tensor, y_train_tensor)}")
            logger.info(f"Epoch {epoch} - Validation Data Stats: {get_data_stats(X_val_tensor, y_val_tensor)}")
            logger.info(f"Epoch {epoch}: Train Loss = {avg_train_loss:.4f}, Val Loss = {val_loss:.4f}, MAPE = {val_mape:.2f}%, RMSE = {val_rmse:.4f}, R2 = {val_r2:.4f}")
            
            # Early stopping check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_model_state = model.state_dict()
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= PATIENCE:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break
        
        # Load best model state
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
            logger.info("Loaded best model state from training")
        
        # Save training curves
        save_training_curves(train_losses, val_losses, val_mapes, val_rmses, val_r2s, os.path.join(settings.MODEL_PATH, f"{symbol}_{timeframe}"))
        
        return model
        
    except Exception as e:
        logger.error(f"Error in train_model: {str(e)}")
        raise 