import os
import sys
import logging
import argparse
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict
from controllers.model_trainer import ModelTrainer
from config import settings
import time
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Supported cryptocurrencies
SUPPORTED_COINS = [
    "BTC",  # Bitcoin
    "ETH",  # Ethereum
    "BNB",  # Binance Coin
    "XRP",  # Ripple
    "ADA",  # Cardano
    "DOGE", # Dogecoin
    "SOL"   # Solana
]

def train_model(symbol: str, timeframe: str) -> Dict:
    """Train model for a specific symbol and timeframe"""
    max_retries = 3
    retry_delay = 60  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Training model for {symbol} ({timeframe}) - Attempt {attempt + 1}/{max_retries}")
            trainer = ModelTrainer(symbol, timeframe)
            result = trainer.train()
            
            if result['status'] == 'success':
                logger.info(f"Successfully trained model for {symbol} ({timeframe})")
                logger.info(f"Best validation loss: {result['best_val_loss']:.6f}")
                logger.info(f"Epochs trained: {result['epochs_trained']}")
                
                # Save training metadata
                metadata = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'training_date': datetime.now().isoformat(),
                    'data_points': result.get('data_points', 0),
                    'validation_metrics': result.get('validation_metrics', {}),
                    'model_path': result.get('model_path', '')
                }
                
                # Save metadata to file
                metadata_path = os.path.join(settings.MODEL_PATH, f"{symbol}_{timeframe}_metadata.json")
                with open(metadata_path, 'w') as f:
                    import json
                    json.dump(metadata, f, indent=2)
                
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'result': result
                }
            else:
                logger.error(f"Failed to train model for {symbol} ({timeframe}): {result['error']}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                    
        except Exception as e:
            logger.error(f"Error training model for {symbol} ({timeframe}): {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'result': {
                    'status': 'error',
                    'error': str(e)
                }
            }
    
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'result': {
            'status': 'error',
            'error': f"Failed after {max_retries} attempts"
        }
    }

def train_all_models(symbols: List[str] = None, timeframes: List[str] = None, max_workers: int = None) -> List[Dict]:
    """Train models for all symbols and timeframes"""
    if symbols is None:
        symbols = SUPPORTED_COINS
    if timeframes is None:
        timeframes = settings.TIMEFRAME_OPTIONS
        
    # Create model directory if it doesn't exist
    os.makedirs(settings.MODEL_PATH, exist_ok=True)
    
    # Prepare training tasks
    tasks = [(symbol, timeframe) for symbol in symbols for timeframe in timeframes]
    results = []
    
    # Train models in parallel with reduced workers to avoid overwhelming APIs
    max_workers = min(max_workers or 3, 3)  # Limit to 3 parallel workers
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for symbol, timeframe in tasks:
            # Add delay between submissions to avoid API rate limits
            if futures:
                time.sleep(5)
            futures.append(executor.submit(train_model, symbol, timeframe))
        
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Task failed: {str(e)}")
    
    # Summarize results
    successful = [r for r in results if r['result']['status'] == 'success']
    failed = [r for r in results if r['result']['status'] == 'error']
    
    logger.info("\nTraining Summary:")
    logger.info(f"Total models: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    
    if failed:
        logger.info("\nFailed Models:")
        for f in failed:
            logger.info(f"{f['symbol']} ({f['timeframe']}): {f['result']['error']}")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train cryptocurrency prediction models")
    parser.add_argument("--symbol", type=str, help="Specific symbol to train (e.g., BTC)")
    parser.add_argument("--timeframe", type=str, help="Specific timeframe to train (e.g., 24h)")
    parser.add_argument("--workers", type=int, help="Number of parallel workers")
    
    args = parser.parse_args()
    
    if args.symbol and args.timeframe:
        results = [train_model(args.symbol, args.timeframe)]
    else:
        symbols = [args.symbol] if args.symbol else None
        timeframes = [args.timeframe] if args.timeframe else None
        results = train_all_models(symbols, timeframes, args.workers)
    
    logger.info("\nTraining completed") 