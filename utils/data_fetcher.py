from fastapi import HTTPException
import logging
from typing import Dict, Any, Optional, List
import yfinance as yf
import requests
from config import settings
import time
import json
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import os
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

class DataFetcher:
    # Cache directory
    CACHE_DIR = Path("cache/market_data")
    CACHE_DURATION = {
        "1h": timedelta(minutes=30),  # Cache 1h data for 30 minutes
        "1d": timedelta(hours=4),     # Cache daily data for 4 hours
        "7d": timedelta(hours=12),    # Cache weekly data for 12 hours
        "30d": timedelta(days=1),     # Cache monthly data for 1 day
        "365d": timedelta(days=7)     # Cache yearly data for 7 days
    }
    
    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._last_coingecko_call = 0
        self._last_yfinance_call = 0
        self.coingecko_rate_limit = 30  # calls per minute
        self.yfinance_rate_limit = 2    # seconds between calls
        
        # Initialize YFinance session
        self.yf_session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        self.yf_session.mount("https://", HTTPAdapter(max_retries=retries))
    
    @staticmethod
    def coingecko_to_yahoo_symbol(coin_id: str) -> str:
        """Convert CoinGecko coin ID to Yahoo Finance symbol."""
        symbol_map = {
            "bitcoin": "BTC-USD",
            "ethereum": "ETH-USD",
            "binancecoin": "BNB-USD",
            "cardano": "ADA-USD",
            "solana": "SOL-USD",
            "ripple": "XRP-USD",
            "polkadot": "DOT-USD",
            "dogecoin": "DOGE-USD"
        }
        return symbol_map.get(coin_id, f"{coin_id.upper()}-USD")

    @staticmethod
    def yahoo_to_coingecko_id(symbol: str) -> str:
        """Convert Yahoo Finance symbol to CoinGecko coin ID."""
        symbol = symbol.replace("-USD", "").lower()
        id_map = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "bnb": "binancecoin",
            "ada": "cardano",
            "sol": "solana",
            "xrp": "ripple",
            "dot": "polkadot",
            "doge": "dogecoin"
        }
        return id_map.get(symbol, symbol)

    def _get_cache_key(self, identifier: str, params: Dict[str, Any], source: str) -> str:
        """Generate cache key for data storage"""
        # Sort params to ensure consistent cache keys
        param_str = json.dumps(params, sort_keys=True)
        key = f"{identifier}_{param_str}_{source}"
        return hashlib.md5(key.encode()).hexdigest()

    def _get_cached_data(self, cache_key: str, duration: timedelta) -> Optional[Dict]:
        """Retrieve data from cache if valid"""
        cache_file = self.CACHE_DIR / f"{cache_key}.json"
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            
            # Check if cache is still valid
            cached_time = datetime.fromisoformat(cached['timestamp'])
            
            if datetime.now() - cached_time < duration:
                logger.debug(f"Using cached data for {cache_key}")
                return cached['data']
                
        except Exception as e:
            logger.warning(f"Cache read error for {cache_key}: {str(e)}")
            if cache_file.exists():
                try:
                    os.remove(cache_file)
                except:
                    pass
            
        return None

    def _save_to_cache(self, cache_key: str, data: Dict):
        """Save data to cache"""
        try:
            cache_file = self.CACHE_DIR / f"{cache_key}.json"
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Cache write error for {cache_key}: {str(e)}")

    def _respect_rate_limit(self, service: str):
        """Ensure rate limits are respected"""
        current_time = time.time()
        
        if service == "coingecko":
            time_since_last = current_time - self._last_coingecko_call
            if time_since_last < 60 / self.coingecko_rate_limit:
                time.sleep((60 / self.coingecko_rate_limit) - time_since_last)
            self._last_coingecko_call = time.time()
            
        elif service == "yfinance":
            time_since_last = current_time - self._last_yfinance_call
            if time_since_last < self.yfinance_rate_limit:
                time.sleep(self.yfinance_rate_limit - time_since_last)
            self._last_yfinance_call = time.time()

    def get_yfinance_data(self, symbol: str, period: str = "7d", interval: str = "1d") -> Dict[str, Any]:
        """
        Fetch data from Yahoo Finance with proper error handling and caching
        """
        params = {"period": period, "interval": interval}
        cache_key = self._get_cache_key(symbol, params, "yfinance")
        
        # Determine cache duration based on interval
        if interval in ["1m", "2m", "5m", "15m", "30m", "60m", "90m"]:
            cache_duration = timedelta(minutes=30)
        elif interval == "1h":
            cache_duration = timedelta(hours=1)
        else:
            cache_duration = timedelta(hours=4)
            
        cached_data = self._get_cached_data(cache_key, cache_duration)
        if cached_data:
            return cached_data

        self._respect_rate_limit("yfinance")
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                raise ValueError(f"No data returned for {symbol}")
                
            # Convert DataFrame to dict format
            data = {
                "source": "yfinance",
                "symbol": symbol,
                "data": {
                    "dates": df.index.astype(str).tolist(),
                    "open": df["Open"].tolist(),
                    "high": df["High"].tolist(),
                    "low": df["Low"].tolist(),
                    "close": df["Close"].tolist(),
                    "volume": df["Volume"].tolist()
                }
            }
            
            self._save_to_cache(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"YFinance error for {symbol}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch data from Yahoo Finance: {str(e)}")

    def get_yfinance_info(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch real-time info from Yahoo Finance
        """
        cache_key = self._get_cache_key(symbol, {}, "yfinance_info")
        cached_data = self._get_cached_data(cache_key, timedelta(minutes=5))
        if cached_data:
            return cached_data

        self._respect_rate_limit("yfinance")
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Extract relevant info
            data = {
                "source": "yfinance",
                "symbol": symbol,
                "name": info.get("longName", ""),
                "currentPrice": info.get("regularMarketPrice", None),
                "marketCap": info.get("marketCap", None),
                "volume24h": info.get("volume24Hr", None),
                "change24h": info.get("regularMarketChangePercent", None),
                "high24h": info.get("dayHigh", None),
                "low24h": info.get("dayLow", None)
            }
            
            self._save_to_cache(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"YFinance info error for {symbol}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch info from Yahoo Finance: {str(e)}")

    async def get_historical_data(self, identifier: str, days: int = 7, use_coingecko_first: bool = True) -> Dict[str, Any]:
        """
        Fetch historical data with fallback between CoinGecko and Yahoo Finance.
        
        Args:
            identifier: Either CoinGecko coin ID or Yahoo Finance symbol
            days: Number of days of historical data
            use_coingecko_first: Whether to try CoinGecko first (True) or Yahoo Finance first (False)
        """
        errors = []
        params = {"days": days}
        cache_key = self._get_cache_key(identifier, params, "combined")
        
        # Determine cache duration based on days
        if days <= 1:
            cache_duration = timedelta(minutes=30)
        elif days <= 7:
            cache_duration = timedelta(hours=4)
        else:
            cache_duration = timedelta(hours=12)
            
        cached_data = self._get_cached_data(cache_key, cache_duration)
        if cached_data:
            return cached_data
            
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
        
        services = ["coingecko", "yfinance"] if use_coingecko_first else ["yfinance", "coingecko"]
        
        for service in services:
            try:
                self._respect_rate_limit(service)
                
                if service == "coingecko":
                    coin_id = self.yahoo_to_coingecko_id(identifier) if "-USD" in identifier else identifier
                    
                    # Adjust days for free tier limitation
                    adjusted_days = min(days, 365)
                    if days > 365:
                        logger.warning(f"Adjusting period from {days} to {adjusted_days} days due to CoinGecko free tier limitation")
                    
                    url = f"{settings.COINGECKO_API_URL}/coins/{coin_id}/market_chart"
                    params = {
                        'vs_currency': 'usd',
                        'days': str(adjusted_days),
                        'interval': 'hourly' if adjusted_days <= 90 else 'daily'
                    }
                    headers = {
                        "Accept": "application/json",
                        "x-cg-demo-api-key": settings.COINGECKO_API_KEY
                    }
                    
                    response = session.get(url, params=params, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = {
                            "source": "coingecko",
                            "data": {
                                "dates": [datetime.fromtimestamp(price[0]/1000).isoformat() for price in data["prices"]],
                                "prices": [price[1] for price in data["prices"]],
                                "volumes": [vol[1] for vol in data["total_volumes"]]
                            }
                        }
                        self._save_to_cache(cache_key, result)
                        return result
                    else:
                        errors.append(f"CoinGecko API error: {response.status_code}")
                        continue

                else:  # yfinance
                    symbol = identifier if "-USD" in identifier else self.coingecko_to_yahoo_symbol(identifier)
                    period = f"{days}d"
                    interval = "1h" if days <= 7 else "1d"
                    
                    try:
                        data = self.get_yfinance_data(symbol, period=period, interval=interval)
                        self._save_to_cache(cache_key, data)
                        return data
                    except Exception as e:
                        errors.append(f"YFinance error: {str(e)}")
                        continue
                        
            except Exception as e:
                errors.append(f"{service.capitalize()} error: {str(e)}")
                continue
                
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch data from all sources: {'; '.join(errors)}"
        ) 