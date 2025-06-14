import os
import sys
import logging
import argparse
import numpy as np
import pandas as pd
import torch
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Tuple
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
from controllers.model_trainer import ModelTrainer
from controllers.data_fetcher import DataFetcher
from config import settings, FEATURE_LIST

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evaluation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ModelEvaluator:
    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.model_dir = os.path.join(settings.MODEL_PATH, symbol)
        self.model_path = os.path.join(self.model_dir, f'model_{timeframe}.pth')
        self.scaler_path = os.path.join(self.model_dir, f'scaler_{timeframe}.joblib')
        self.data_fetcher = DataFetcher()
        
    def load_model(self) -> Tuple[torch.nn.Module, Dict]:
        """Load trained model and its metadata"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"No trained model found for {self.symbol} ({self.timeframe})")
            
        # Load with weights_only=False to handle datetime objects
        checkpoint = torch.load(self.model_path, weights_only=False, map_location=torch.device('cpu'))
        
        if 'model_config' not in checkpoint:
            raise KeyError(f"'model_config' not found in checkpoint for {self.model_path}. Model may be outdated or saved incorrectly.")
        model_config = checkpoint['model_config']
        
        if not all(k in model_config for k in ['input_size', 'hidden_size', 'num_layers']):
            raise KeyError(f"'model_config' is missing required keys (input_size, hidden_size, num_layers) in {self.model_path}.")
        
        # Initialize model
        from controllers.model_trainer import BiLSTMWithAttention
        model = BiLSTMWithAttention(
            input_size=model_config['input_size'],
            hidden_size=model_config['hidden_size'],
            num_layers=model_config['num_layers']
        )
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        
        return model, checkpoint
        
    def evaluate(self, days_back: int = 30) -> Dict:
        """Evaluate model performance"""
        try:
            # Load model and data
            model, checkpoint = self.load_model()
            
            # Get recent data
            end_date = datetime.now(pytz.UTC)
            start_date = end_date - timedelta(days=days_back)
            
            data = self.data_fetcher.get_merged_data(self.symbol, self.timeframe)
            if data is None:
                raise ValueError(f"Could not fetch data for {self.symbol}")
                
            # Filter data for evaluation period
            data = data[data.index >= start_date]
            if len(data) < 10:
                raise ValueError(f"Insufficient data points for evaluation: {len(data)}")
            
            # Prepare features
            X = data[FEATURE_LIST].values
            y_true = data['Close'].values
            
            # Make predictions
            predictions = []
            uncertainties = []
            
            with torch.no_grad():
                for i in range(len(X)):
                    input_seq = torch.FloatTensor(X[max(0, i-60):i]).unsqueeze(0)
                    pred, aleatoric, epistemic = model(input_seq, return_uncertainty=True)
                    predictions.append(pred.item())
                    uncertainties.append((aleatoric.item(), epistemic.item()))
            
            predictions = np.array(predictions)
            uncertainties = np.array(uncertainties)
            
            # Calculate metrics
            metrics = {
                'mae': mean_absolute_error(y_true, predictions),
                'rmse': np.sqrt(mean_squared_error(y_true, predictions)),
                'r2': r2_score(y_true, predictions),
                'mape': np.mean(np.abs((y_true - predictions) / y_true)) * 100,
                'directional_accuracy': np.mean(np.sign(np.diff(predictions)) == np.sign(np.diff(y_true))) * 100
            }
            
            # Calculate prediction intervals
            confidence_intervals = []
            for pred, (aleatoric, epistemic) in zip(predictions, uncertainties):
                total_uncertainty = np.sqrt(aleatoric + epistemic)
                confidence_intervals.append((
                    pred - 1.96 * total_uncertainty,  # Lower bound (95% CI)
                    pred + 1.96 * total_uncertainty   # Upper bound (95% CI)
                ))
            
            # Plot results
            self._plot_predictions(data.index, y_true, predictions, confidence_intervals)
            
            return {
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'evaluation_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'metrics': metrics,
                'model_info': {
                    'training_date': checkpoint['training_date'].isoformat(),
                    'epochs_trained': checkpoint['epoch'],
                    'best_val_loss': checkpoint['val_loss']
                }
            }
            
        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            return {
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'status': 'error',
                'error': str(e)
            }
    
    def _plot_predictions(self, dates, y_true, predictions, confidence_intervals):
        """Plot actual vs predicted prices with confidence intervals"""
        plt.figure(figsize=(12, 6))
        
        # Plot actual prices
        plt.plot(dates, y_true, label='Actual', color='blue', alpha=0.7)
        
        # Plot predictions
        plt.plot(dates, predictions, label='Predicted', color='red', alpha=0.7)
        
        # Plot confidence intervals
        ci_lower = [ci[0] for ci in confidence_intervals]
        ci_upper = [ci[1] for ci in confidence_intervals]
        plt.fill_between(dates, ci_lower, ci_upper, color='red', alpha=0.2, label='95% CI')
        
        plt.title(f'{self.symbol} Price Predictions ({self.timeframe})')
        plt.xlabel('Date')
        plt.ylabel('Price (USD)')
        plt.legend()
        plt.grid(True)
        
        # Save plot
        os.makedirs('plots', exist_ok=True)
        plt.savefig(f'plots/{self.symbol}_{self.timeframe}_evaluation.png')
        plt.close()

def evaluate_all_models(symbols: List[str] = None, timeframes: List[str] = None, days_back: int = 30) -> List[Dict]:
    """Evaluate all models"""
    if symbols is None:
        symbols = ["BTC", "ETH", "BNB", "XRP", "ADA", "DOGE", "SOL"]
    if timeframes is None:
        timeframes = settings.TIMEFRAME_OPTIONS
        
    results = []
    
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                evaluator = ModelEvaluator(symbol, timeframe)
                result = evaluator.evaluate(days_back)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to evaluate {symbol} ({timeframe}): {str(e)}")
                results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'error',
                    'error': str(e)
                })
    
    return results

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Evaluate cryptocurrency prediction models')
    parser.add_argument('--symbols', nargs='+', help='Symbols to evaluate (default: all)')
    parser.add_argument('--timeframes', nargs='+', choices=settings.TIMEFRAME_OPTIONS,
                      help='Timeframes to evaluate (default: all)')
    parser.add_argument('--days', type=int, default=30,
                      help='Number of days to evaluate (default: 30)')
    args = parser.parse_args()
    
    try:
        logger.info("Starting model evaluation")
        results = evaluate_all_models(args.symbols, args.timeframes, args.days)
        
        # Print summary
        success_count = sum(1 for r in results if 'status' not in r or r['status'] != 'error')
        total_count = len(results)
        
        logger.info("\nEvaluation Summary:")
        logger.info(f"Total models evaluated: {total_count}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {total_count - success_count}")
        
        # Print metrics for successful evaluations
        logger.info("\nModel Performance:")
        for result in results:
            if 'metrics' in result:
                logger.info(f"\n{result['symbol']} ({result['timeframe']}):")
                logger.info(f"MAE: {result['metrics']['mae']:.4f}")
                logger.info(f"RMSE: {result['metrics']['rmse']:.4f}")
                logger.info(f"R²: {result['metrics']['r2']:.4f}")
                logger.info(f"MAPE: {result['metrics']['mape']:.2f}%")
                logger.info(f"Directional Accuracy: {result['metrics']['directional_accuracy']:.2f}%")
        
        # Print errors for failed evaluations
        if success_count < total_count:
            logger.info("\nFailed Evaluations:")
            for result in results:
                if 'status' in result and result['status'] == 'error':
                    logger.info(f"{result['symbol']} ({result['timeframe']}): {result['error']}")
        
        logger.info("\nEvaluation completed")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 