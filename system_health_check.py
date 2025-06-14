import asyncio
import logging
from datetime import datetime
import pytz
from controllers.data_fetcher import DataFetcher, is_crypto
from controllers.prediction import get_model, predict_next_price
import json
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_system_health(symbols=None, timeframes=None):
    """
    Run a comprehensive health check of the prediction system.
    
    Args:
        symbols (list): List of symbols to check. Defaults to ['BTC', 'XRP', 'AAPL']
        timeframes (list): List of timeframes. Defaults to ['30m', '1h', '4h', '24h']
    """
    if symbols is None:
        symbols = ['BTC', 'XRP', 'AAPL']
    if timeframes is None:
        timeframes = ['30m', '1h', '4h', '24h']
        
    results = {
        'timestamp': datetime.now(pytz.UTC).isoformat(),
        'checks': []
    }
    
    fetcher = DataFetcher()
    
    for symbol in symbols:
        asset_type = "cryptocurrency" if is_crypto(symbol) else "stock"
        logger.info(f"\nChecking {symbol} ({asset_type})")
        
        for timeframe in timeframes:
            # Skip 4h for stocks as it's not supported
            if not is_crypto(symbol) and timeframe == '4h':
                continue
                
            check_result = {
                'symbol': symbol,
                'asset_type': asset_type,
                'timeframe': timeframe,
                'data_fetch': {'status': 'not_started'},
                'model': {'status': 'not_started'},
                'prediction': {'status': 'not_started'}
            }
            
            try:
                # Check data fetching
                logger.info(f"Checking data fetch for {symbol} {timeframe}")
                df = await fetcher.get_merged_data(symbol, timeframe)
                if df is not None and not df.empty:
                    check_result['data_fetch'] = {
                        'status': 'success',
                        'points': len(df),
                        'columns': len(df.columns),
                        'date_range': {
                            'start': df.index.min().isoformat(),
                            'end': df.index.max().isoformat()
                        }
                    }
                else:
                    check_result['data_fetch'] = {
                        'status': 'failed',
                        'error': 'No data returned'
                    }
                
                # Check model loading
                logger.info(f"Checking model for {symbol} {timeframe}")
                model = await get_model(symbol, timeframe)
                if model:
                    check_result['model'] = {
                        'status': 'success',
                        'path': f"models/{symbol}_{timeframe}/model.pth"
                    }
                else:
                    check_result['model'] = {
                        'status': 'failed',
                        'error': 'Could not load model'
                    }
                
                # Check prediction
                if model:
                    logger.info(f"Checking prediction for {symbol} {timeframe}")
                    prediction = await predict_next_price(symbol, timeframe)
                    if prediction:
                        check_result['prediction'] = {
                            'status': 'success',
                            'prediction': prediction
                        }
                    else:
                        check_result['prediction'] = {
                            'status': 'failed',
                            'error': 'Could not generate prediction'
                        }
                
            except Exception as e:
                logger.error(f"Error checking {symbol} {timeframe}: {str(e)}")
                check_result['error'] = str(e)
            
            results['checks'].append(check_result)
            
    # Save results
    os.makedirs('health_checks', exist_ok=True)
    filename = f"health_checks/system_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=4)
    
    logger.info(f"\nHealth check complete. Results saved to {filename}")
    return results

if __name__ == "__main__":
    asyncio.run(check_system_health()) 