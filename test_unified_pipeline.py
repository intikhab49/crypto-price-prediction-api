import argparse
import logging
import asyncio
from datetime import datetime
import pytz
from controllers.prediction import get_model, predict_next_price
from controllers.data_fetcher import is_crypto
import json
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_test(symbol: str, timeframe: str):
    """
    Run a complete test of the prediction pipeline for a given symbol and timeframe.
    
    Args:
        symbol (str): Trading symbol (e.g., 'BTC', 'AAPL')
        timeframe (str): Time interval ('30m', '1h', '4h', '24h')
    """
    asset_type = "cryptocurrency" if is_crypto(symbol) else "stock"
    logger.info(f"--- Starting Test for {symbol} ({asset_type}) - {timeframe} ---")
        
    try:
        logger.info("Phase 1: Loading/Training Model")
        model = await get_model(symbol, timeframe)
        if not model:
            raise ValueError(f"Failed to get model for {symbol} {timeframe}")
        
        logger.info("Phase 2: Making Predictions")
        prediction = await predict_next_price(symbol, timeframe)
        if not prediction:
            raise ValueError(f"Failed to get prediction for {symbol} {timeframe}")
        
        # Save results
        results = {
            'symbol': symbol,
            'asset_type': asset_type,
            'timeframe': timeframe,
            'timestamp': datetime.now(pytz.UTC).isoformat(),
            'prediction': prediction
        }
        
        # Ensure results directory exists
        os.makedirs('results', exist_ok=True)
        
        # Save to file
        filename = f"results/test_results_{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=4)
        
        logger.info(f"Test completed successfully. Results saved to {filename}")
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Test the unified prediction pipeline')
    parser.add_argument('--symbol', type=str, default='BTC',
                      help='Trading symbol (e.g., BTC for Bitcoin, AAPL for Apple)')
    parser.add_argument('--timeframe', type=str, choices=['30m', '1h', '4h', '24h'],
                      default='1h', help='Time interval for predictions')
    
    args = parser.parse_args()
    
    # Run the async test
    asyncio.run(run_test(args.symbol, args.timeframe))

if __name__ == "__main__":
    main() 