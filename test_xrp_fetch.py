import asyncio
import logging
from controllers.data_fetcher import DataFetcher

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_xrp_fetch():
    """Test XRP data fetching for different timeframes"""
    fetcher = DataFetcher()
    timeframes = ['30m', '1h', '4h', '24h']
    
    for timeframe in timeframes:
        logger.info(f"\nTesting XRP data fetch for {timeframe} timeframe")
        try:
            df = await fetcher.get_merged_data('XRP', timeframe)
            if df is not None and not df.empty:
                logger.info(f"Successfully fetched XRP {timeframe} data:")
                logger.info(f"- Shape: {df.shape}")
                logger.info(f"- Date range: {df.index.min()} to {df.index.max()}")
                logger.info(f"- Columns: {df.columns.tolist()}")
            else:
                logger.error(f"No data returned for XRP {timeframe}")
        except Exception as e:
            logger.error(f"Error fetching XRP {timeframe} data: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_xrp_fetch()) 