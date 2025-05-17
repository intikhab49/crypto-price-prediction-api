from fastapi import APIRouter, HTTPException
import requests
from fastapi.responses import JSONResponse
from config import settings
import logging
from cachetools import TTLCache

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
cache = TTLCache(maxsize=100, ttl=60)  # Cache for 60 seconds

COINGECKO_API_KEY = ""  # Trial API key

@router.get("/{coin_id}")
def proxy_coingecko(coin_id: str):
    try:
        url = f"{settings.COINGECKO_API_URL}/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false"
        headers = {"x-cg-demo-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}
        logger.info(f"Fetching CoinGecko data for {coin_id}")
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"Failed to fetch from CoinGecko for {coin_id}: {resp.status_code}")
        return JSONResponse(
            content={"error": "Failed to fetch from CoinGecko", "status_code": resp.status_code},
            status_code=resp.status_code
        )
    except Exception as e:
        logger.error(f"Error fetching CoinGecko data for {coin_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching from CoinGecko: {str(e)}")

@router.get("/realtime")
def get_realtime_data():
    cache_key = "realtime_data"
    if cache_key in cache:
        logger.info("Returning cached realtime data")
        return cache[cache_key]
    try:
        url = f"{settings.COINGECKO_API_URL}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1&sparkline=false"
        headers = {"x-cg-demo-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}
        logger.info("Fetching CoinGecko realtime market data")
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            cache[cache_key] = data
            return data
        logger.error(f"Failed to fetch realtime data: {resp.status_code}")
        return JSONResponse(
            content={"error": "Failed to fetch from CoinGecko", "status_code": resp.status_code},
            status_code=resp.status_code
        )
    except Exception as e:
        logger.error(f"Error fetching realtime data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching from CoinGecko: {str(e)}")

@router.get("/historical/{coin_id}")
def get_historical_data(coin_id: str, days: int = 365):
    try:
        url = f"{settings.COINGECKO_API_URL}/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
        headers = {"x-cg-demo-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}
        logger.info(f"Fetching CoinGecko historical data for {coin_id}")
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "dates": [price[0] for price in data.get("prices", [])],
                "prices": [price[1] for price in data.get("prices", [])],
                "market_caps": [mc[1] for mc in data.get("market_caps", [])],
                "total_volumes": [vol[1] for vol in data.get("total_volumes", [])]
            }
        logger.error(f"Failed to fetch historical data for {coin_id}: {resp.status_code}")
        return JSONResponse(
            content={"error": "Failed to fetch from CoinGecko", "status_code": resp.status_code},
            status_code=resp.status_code
        )
    except Exception as e:
        logger.error(f"Error fetching historical data for {coin_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching from CoinGecko: {str(e)}")