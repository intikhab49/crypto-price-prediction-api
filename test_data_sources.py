import logging
import pandas as pd
from datetime import datetime
import time
from controllers.data_fetcher import DataFetcher
from config import settings, TIMEFRAME_MAP

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_source_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_coingecko_api(data_fetcher: DataFetcher, symbol: str, timeframe: str):
    """Test CoinGecko API data fetching"""
    logger.info(f"\nTesting CoinGecko API for {symbol} ({timeframe})")
    try:
        start_time = time.time()
        df = data_fetcher.get_coingecko_data(symbol, timeframe)
        duration = time.time() - start_time
        
        if df is not None:
            logger.info(f"✓ Successfully fetched data from CoinGecko")
            logger.info(f"  - Data points: {len(df)}")
            logger.info(f"  - Date range: {df.index.min()} to {df.index.max()}")
            logger.info(f"  - Columns: {', '.join(df.columns)}")
            logger.info(f"  - Request duration: {duration:.2f} seconds")
            
            # Check for missing values
            missing = df.isnull().sum()
            if missing.any():
                logger.warning("Missing values detected:")
                for col, count in missing[missing > 0].items():
                    logger.warning(f"  - {col}: {count} missing values")
        else:
            logger.error("× Failed to fetch data from CoinGecko")
    except Exception as e:
        logger.error(f"× Error testing CoinGecko API: {str(e)}")

def test_yfinance_api(data_fetcher: DataFetcher, symbol: str, timeframe: str):
    """Test yfinance API data fetching"""
    logger.info(f"\nTesting yfinance API for {symbol} ({timeframe})")
    try:
        start_time = time.time()
        df = data_fetcher.fetch_yfinance_data(symbol, timeframe)
        duration = time.time() - start_time
        
        if df is not None:
            logger.info(f"✓ Successfully fetched data from yfinance")
            logger.info(f"  - Data points: {len(df)}")
            logger.info(f"  - Date range: {df.index.min()} to {df.index.max()}")
            logger.info(f"  - Columns: {', '.join(df.columns)}")
            logger.info(f"  - Request duration: {duration:.2f} seconds")
            
            # Check for missing values
            missing = df.isnull().sum()
            if missing.any():
                logger.warning("Missing values detected:")
                for col, count in missing[missing > 0].items():
                    logger.warning(f"  - {col}: {count} missing values")
        else:
            logger.error("× Failed to fetch data from yfinance")
    except Exception as e:
        logger.error(f"× Error testing yfinance API: {str(e)}")

def test_merged_data(data_fetcher: DataFetcher, symbol: str, timeframe: str):
    """Test merged data functionality"""
    logger.info(f"\nTesting merged data for {symbol} ({timeframe})")
    try:
        start_time = time.time()
        df = data_fetcher.get_merged_data(symbol, timeframe)
        duration = time.time() - start_time
        
        if df is not None:
            logger.info(f"✓ Successfully fetched merged data")
            logger.info(f"  - Data points: {len(df)}")
            logger.info(f"  - Date range: {df.index.min()} to {df.index.max()}")
            logger.info(f"  - Columns: {', '.join(df.columns)}")
            logger.info(f"  - Request duration: {duration:.2f} seconds")
            
            # Check data requirements
            min_required = TIMEFRAME_MAP[timeframe].get('min_samples', settings.MIN_DATA_POINTS)
            if len(df) < min_required:
                logger.warning(f"× Insufficient data points: {len(df)} < {min_required} required")
            else:
                logger.info(f"✓ Sufficient data points: {len(df)} >= {min_required} required")
                
            # Check for missing values
            missing = df.isnull().sum()
            if missing.any():
                logger.warning("Missing values detected:")
                for col, count in missing[missing > 0].items():
                    logger.warning(f"  - {col}: {count} missing values")
        else:
            logger.error("× Failed to fetch merged data")
    except Exception as e:
        logger.error(f"× Error testing merged data: {str(e)}")

def main():
    logger.info("Starting data source tests...")
    logger.info(f"CoinGecko API Key: {'Set' if settings.COINGECKO_API_KEY else 'Not Set'}")
    
    data_fetcher = DataFetcher()
    symbols = ["BTC", "ETH"]
    timeframes = ["30m", "1h", "4h", "24h"]
    
    for symbol in symbols:
        for timeframe in timeframes:
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing {symbol} - {timeframe}")
            logger.info(f"{'='*50}")
            
            # Test individual sources
            test_coingecko_api(data_fetcher, symbol, timeframe)
            test_yfinance_api(data_fetcher, symbol, timeframe)
            
            # Test merged data
            test_merged_data(data_fetcher, symbol, timeframe)
            
            # Add delay between tests to respect rate limits
            time.sleep(2)

if __name__ == "__main__":
    main() 