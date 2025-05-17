from fastapi import APIRouter, HTTPException
import yfinance as yf
from typing import Optional
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def fetch_yfinance_data(symbol: str, period: str, interval: str):
    for attempt in range(3):
        try:
            logger.info(f"Attempt {attempt + 1}: Fetching data for {symbol}, period={period}, interval={interval}")
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval, timeout=10, auto_adjust=False)
            if data.empty:
                logger.warning(f"No data found for {symbol}")
                return None
            return data
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == 2:
                raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")
            await asyncio.sleep(2)

@router.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    period: Optional[str] = "1y",
    interval: Optional[str] = "1d"
):
    try:
        if not symbol.endswith('-USD'):
            symbol = f"{symbol}-USD"
        data = await fetch_yfinance_data(symbol, period, interval)
        if data is None:
            alt_symbol = symbol.replace("-USD", "-USDT")
            data = await fetch_yfinance_data(alt_symbol, period, interval)
            if data is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data found for symbol {symbol} or {alt_symbol}"
                )
        result = {
            "dates": data.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            "open": data['Open'].tolist(),
            "high": data['High'].tolist(),
            "low": data['Low'].tolist(),
            "close": data['Close'].tolist(),
            "volume": data['Volume'].tolist()
        }
        return result
    except Exception as e:
        logger.error(f"Final error for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

@router.get("/info/{symbol}")
async def get_symbol_info(symbol: str):
    try:
        if not symbol.endswith('-USD'):
            symbol = f"{symbol}-USD"
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"No information found for symbol {symbol}"
            )
        return {
            "name": info.get("longName", ""),
            "symbol": symbol,
            "currentPrice": info.get("currentPrice", 0),
            "marketCap": info.get("marketCap", 0),
            "volume24h": info.get("volume24h", 0),
            "change24h": info.get("regularMarketChangePercent", 0)
        }
    except Exception as e:
        logger.error(f"Error fetching info for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching symbol info: {str(e)}")