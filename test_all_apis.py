import asyncio
import logging
import pandas as pd

# Adjust the import path if your DataFetcher is in a different location
# Assuming execution from the project root and DataFetcher is in controllers.data_fetcher
from controllers.data_fetcher import DataFetcher

# Configure logging to see output from DataFetcher and this script
# The DataFetcher module itself configures its logger to DEBUG and adds a StreamHandler,
# so this basicConfig might primarily affect other loggers or the root logger.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()] # Ensure logs go to console
)
logger = logging.getLogger(__name__)
# To make DataFetcher's DEBUG logs visible if they aren't already:
logging.getLogger('controllers.data_fetcher').setLevel(logging.DEBUG)


async def run_tests():
    fetcher = DataFetcher()
    
    # Test cases: symbol and timeframe
    # Using symbols from your config.settings.SYMBOLS and TIMEFRAMES
    test_cases = [
        {"symbol": "BTC", "timeframe": "1h"},
        {"symbol": "ETH", "timeframe": "24h"},
        # Add more test cases as needed:
        # {"symbol": "SOL", "timeframe": "4h"},
        # {"symbol": "ADA", "timeframe": "30m"},
        # Consider a less common symbol if you want to test fallbacks more rigorously,
        # though it's hard to guarantee a specific source will fail on demand.
    ]

    logger.info("Starting data fetching tests...")

    for case in test_cases:
        symbol = case["symbol"]
        timeframe = case["timeframe"]
        
        logger.info(f"--- Testing: Symbol='{symbol}', Timeframe='{timeframe}' ---")
        try:
            df = await fetcher.get_historical_data(symbol, timeframe)
            
            if df is not None and not df.empty:
                logger.info(f"Successfully fetched data for {symbol} - {timeframe}.")
                logger.info(f"Data Shape: {df.shape}")
                logger.info(f"First 3 rows:\n{df.head(3)}")
                logger.info(f"Last 3 rows:\n{df.tail(3)}")
                # Check for NaNs
                nan_counts = df.isnull().sum()
                logger.info(f"NaN counts per column:\n{nan_counts[nan_counts > 0]}")

            elif df is not None and df.empty:
                logger.warning(f"Fetched an EMPTY DataFrame for {symbol} - {timeframe}.")
            else:
                logger.error(f"Failed to fetch data for {symbol} - {timeframe}. Received None.")
                
        except Exception as e:
            logger.error(f"Exception during test for {symbol} - {timeframe}: {e}", exc_info=True)
        logger.info(f"--- Finished Test: Symbol='{symbol}', Timeframe='{timeframe}' ---\n")

    logger.info("All data fetching tests completed.")

if __name__ == "__main__":
    # Ensure that if you're running this in an environment where an event loop might already be running (e.g. Jupyter),
    # you might need a different way to run the async code, like `await run_tests()` if in an async context.
    # For a standard Python script, asyncio.run() is appropriate.
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        logger.info("Test run interrupted by user.")
    except Exception as e:
        logger.critical(f"Critical error in test script execution: {e}", exc_info=True) 