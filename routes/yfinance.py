from fastapi import APIRouter, HTTPException
import yfinance as yf
from typing import Optional
import logging
import sys
import pandas as pd
from utils.data_fetcher import DataFetcher
from fastapi.responses import JSONResponse

router = APIRouter()

# Setup logging
logger = logging.getLogger('yfinance_routes')
logger.setLevel(logging.DEBUG)

# Ensure we don't duplicate handlers
if not logger.handlers:
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler
    fh = logging.FileHandler('yfinance_debug.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

# Initialize DataFetcher
data_fetcher = DataFetcher()

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify yfinance is working."""
    try:
        logger.debug("Testing yfinance with BTC-USD")
        data = data_fetcher.get_yfinance_data("BTC-USD", period="1d", interval="1h")
        return {"status": "success", "message": "yfinance is working correctly", "data": data}
    except Exception as e:
        logger.error(f"Error testing yfinance: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/historical/{symbol}")
async def get_historical_data(symbol: str, period: str = "7d", interval: str = "1d"):
    """Get historical market data with fallback to CoinGecko."""
    try:
        # Convert period to days for DataFetcher
        period_map = {
            "1d": 1, "7d": 7, "1mo": 30, "3mo": 90,
            "6mo": 180, "1y": 365, "2y": 730
        }
        days = period_map.get(period, 7)  # Default to 7 days if period not recognized
        
        # Try Yahoo Finance first, fallback to CoinGecko
        result = await data_fetcher.get_historical_data(symbol, days, use_coingecko_first=False)
        return result
        
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        return JSONResponse(status_code=503, content={"error": str(e)})

@router.get("/info/{symbol}")
async def get_symbol_info(symbol: str):
    """Get current market info for a symbol."""
    try:
        logger.debug(f"Fetching info for {symbol}")
        data = data_fetcher.get_yfinance_info(symbol)
        logger.debug(f"Successfully processed info for {symbol}")
        return {"status": "success", "data": data}
        
    except Exception as e:
        logger.error(f"Error processing info for {symbol}: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})