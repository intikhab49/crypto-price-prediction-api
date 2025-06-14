from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from config import settings
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from cachetools import TTLCache
import time
from utils.data_fetcher import DataFetcher

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Increase cache time to help with rate limits
cache = TTLCache(maxsize=100, ttl=600)  # Cache for 10 minutes

# Rate limiting
last_request_time = 0
MIN_REQUEST_INTERVAL = 60 / int(settings.MAX_REQUESTS_PER_MINUTE)  # Time in seconds between requests

# Initialize DataFetcher
data_fetcher = DataFetcher()

def rate_limit():
    """Simple rate limiting."""
    global last_request_time
    current_time = time.time()
    time_passed = current_time - last_request_time
    if time_passed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - time_passed)
    last_request_time = time.time()

# Map common symbols to CoinGecko IDs
symbol_to_id = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "XRP": "ripple",
    "SOL": "solana",
    "DOT": "polkadot",
    "LTC": "litecoin",
}

def get_headers():
    """Get headers for CoinGecko API requests."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    if settings.COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = settings.COINGECKO_API_KEY
    return headers

def symbol_to_coin_id(symbol: str) -> str:
    """Convert symbol to CoinGecko coin ID."""
    coin_id = symbol_to_id.get(symbol.upper())
    if not coin_id:
        raise HTTPException(status_code=400, detail=f"Symbol '{symbol}' is not supported or unknown.")
    return coin_id

@router.get("/realtime", operation_id="get_realtime_data")
def get_realtime_data():
    """Get realtime trending data."""
    cache_key = "realtime_data"
    if cache_key in cache:
        logger.info("Returning cached realtime data")
        return cache[cache_key]

    try:
        rate_limit()
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        
        url = f"{settings.COINGECKO_API_URL}/search/trending"
        logger.info("Fetching CoinGecko realtime market data")
        resp = session.get(url, headers=get_headers(), timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            cache[cache_key] = data
            return data
        elif resp.status_code == 429:
            logger.warning("Rate limit reached")
            return JSONResponse(
                content={"error": "Rate limit reached. Please try again later."},
                status_code=429
            )
        elif resp.status_code == 401:
            logger.error("Unauthorized. Check your API key.")
            return JSONResponse(
                content={"error": "Unauthorized. Check your API key."},
                status_code=401
            )

        logger.error(f"Failed to fetch realtime data: {resp.status_code}")
        return JSONResponse(
            content={"error": f"Failed to fetch from CoinGecko: {resp.status_code}"},
            status_code=resp.status_code
        )
    except Exception as e:
        logger.error(f"Error fetching realtime data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching from CoinGecko: {str(e)}")

@router.get("/historical/{coin_id}", operation_id="get_historical_data")
async def get_historical_data(coin_id: str, days: int = 7):
    """Get historical market data with fallback to Yahoo Finance."""
    cache_key = f"historical_{coin_id}_{days}"
    if cache_key in cache:
        logger.info(f"Returning cached historical data for {coin_id}")
        return cache[cache_key]

    try:
        # Try CoinGecko first, fallback to Yahoo Finance
        result = await data_fetcher.get_historical_data(coin_id, days, use_coingecko_first=True)
        cache[cache_key] = result
        return result
    except Exception as e:
        logger.error(f"Error fetching historical data for {coin_id}: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/by-symbol/{symbol}", operation_id="get_data_by_symbol")
def get_data_by_symbol(symbol: str):
    """Get data for a specific symbol."""
    try:
        coin_id = symbol_to_coin_id(symbol)
        return get_coin_data(coin_id)
    except Exception as e:
        logger.error(f"Error in get_data_by_symbol for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{coin_id}", operation_id="get_coin_data")
def get_coin_data(coin_id: str):
    """Get current data for a specific coin."""
    cache_key = f"coin_{coin_id}"
    if cache_key in cache:
        logger.info(f"Returning cached data for {coin_id}")
        return cache[cache_key]

    try:
        rate_limit()
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        
        url = f"{settings.COINGECKO_API_URL}/coins/{coin_id}"
        logger.info(f"Fetching CoinGecko data for {coin_id}")
        resp = session.get(url, headers=get_headers(), timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            cache[cache_key] = data
            return data
        elif resp.status_code == 429:
            logger.warning("Rate limit reached")
            return JSONResponse(
                content={"error": "Rate limit reached. Please try again later."},
                status_code=429
            )
        elif resp.status_code == 401:
            logger.error("Unauthorized. Check your API key.")
            return JSONResponse(
                content={"error": "Unauthorized. Check your API key."},
                status_code=401
            )

        logger.error(f"Failed to fetch data for {coin_id}: {resp.status_code}")
        return JSONResponse(
            content={"error": f"Failed to fetch from CoinGecko: {resp.status_code}"},
            status_code=resp.status_code
        )
    except Exception as e:
        logger.error(f"Error fetching data for {coin_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching from CoinGecko: {str(e)}")