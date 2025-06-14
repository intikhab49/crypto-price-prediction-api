from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Set, Optional
import json
import asyncio
import logging
from datetime import datetime
import pytz
from .prediction import predict_next_price, fetch_coingecko_price, fetch_yfinance_data
from config import settings
import time
from .websocket_manager import manager

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, rate_limit=30):  # 30 seconds minimum between updates
        self.rate_limit = rate_limit
        self.last_update: Dict[str, float] = {}

    def can_update(self, symbol: str) -> bool:
        current_time = time.time()
        if symbol not in self.last_update:
            self.last_update[symbol] = current_time
            return True
        
        if current_time - self.last_update[symbol] >= self.rate_limit:
            self.last_update[symbol] = current_time
            return True
        return False

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.update_interval = 30  # seconds
        self.rate_limiter = RateLimiter()
        self.last_prices: Dict[str, tuple] = {}  # Store last price and source

    async def connect(self, websocket: WebSocket, symbol: str, timeframe: str = "1h"):
        await websocket.accept()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = set()
            # Start price updates for this symbol
            self.tasks[symbol] = asyncio.create_task(self._price_updates(symbol))
        self.active_connections[symbol].add(websocket)
        
        # Send last known price immediately if available
        if symbol in self.last_prices:
            price, source, timestamp = self.last_prices[symbol]
            await websocket.send_json({
                "symbol": symbol,
                "price": price,
                "source": source,
                "timestamp": timestamp.isoformat(),
                "type": "price_update"
            })
        
        logger.info(f"Client connected for {symbol}. Total connections: {len(self.active_connections[symbol])}")

    def disconnect(self, websocket: WebSocket, symbol: str, timeframe: str = "1h"):
        try:
            if symbol in self.active_connections:
                self.active_connections[symbol].remove(websocket)
                if not self.active_connections[symbol]:
                    # Cancel updates if no clients are listening
                    if symbol in self.tasks:
                        self.tasks[symbol].cancel()
                        del self.tasks[symbol]
                    del self.active_connections[symbol]
            logger.info(f"Client disconnected from {symbol}. Remaining connections: {len(self.active_connections.get(symbol, set()))}")
        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")

    async def broadcast(self, symbol: str, message: dict):
        if symbol in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[symbol]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to client: {str(e)}")
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead in dead_connections:
                try:
                    self.disconnect(dead, symbol)
                except Exception as e:
                    logger.error(f"Error removing dead connection: {str(e)}")

    async def _price_updates(self, symbol: str):
        """Background task to update prices"""
        error_count = 0
        MAX_ERRORS = 5
        
        while True:
            try:
                if not self.rate_limiter.can_update(symbol):
                    await asyncio.sleep(1)
                    continue

                current_time = datetime.now(pytz.UTC)
                
                # Get price from multiple sources with error handling
                try:
                    yf_data = fetch_yfinance_data(f"{symbol}-USD", "1d", "1m")
                    yf_price = float(yf_data['Close'].iloc[-1]) if not yf_data.empty else None
                except Exception as e:
                    logger.error(f"YFinance error for {symbol}: {str(e)}")
                    yf_price = None

                try:
                    cg_price = fetch_coingecko_price(symbol)
                except Exception as e:
                    logger.error(f"CoinGecko error for {symbol}: {str(e)}")
                    cg_price = None

                # Use the most reliable price
                if cg_price and yf_price:
                    price = cg_price if abs(yf_price - cg_price) / cg_price < 0.02 else yf_price
                    source = "CoinGecko" if price == cg_price else "yfinance"
                else:
                    price = cg_price or yf_price
                    source = "CoinGecko" if cg_price else "yfinance"

                if price:
                    # Store last known good price
                    self.last_prices[symbol] = (price, source, current_time)
                    
                    # Get prediction with error handling
                    try:
                        prediction = predict_next_price(symbol)
                    except Exception as e:
                        logger.error(f"Prediction error for {symbol}: {str(e)}")
                        prediction = {"error": str(e)}
                    
                    message = {
                        "symbol": symbol,
                        "price": price,
                        "source": source,
                        "timestamp": current_time.isoformat(),
                        "prediction": prediction if "error" not in prediction else None,
                        "type": "price_update"
                    }
                    
                    await self.broadcast(symbol, message)
                    logger.debug(f"Price update sent for {symbol}: {price}")
                    error_count = 0  # Reset error count on successful update
                else:
                    error_count += 1
                    logger.error(f"No price available for {symbol}")
                    if error_count >= MAX_ERRORS:
                        logger.error(f"Too many errors for {symbol}, stopping updates")
                        break
            
            except Exception as e:
                error_count += 1
                logger.error(f"Error in price updates for {symbol}: {str(e)}")
                if error_count >= MAX_ERRORS:
                    logger.error(f"Too many errors for {symbol}, stopping updates")
                    break
            
            await asyncio.sleep(self.update_interval)

async def websocket_endpoint(websocket: WebSocket, symbol: str, timeframe: str = "1h"):
    """WebSocket endpoint for real-time price and prediction updates"""
    try:
        await manager.connect(websocket, symbol, timeframe)
        
        while True:
            try:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    await manager.handle_client_message(websocket, symbol, timeframe, message)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid message received: {data}")
            except WebSocketDisconnect:
                manager.disconnect(websocket, symbol, timeframe)
                break
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                break
    except Exception as e:
        logger.error(f"Failed to establish WebSocket connection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        manager.disconnect(websocket, symbol, timeframe) 

    while True:
        prediction = await predict_next_price(symbol, timeframe)
        await websocket.send_json(prediction)
        await asyncio.sleep(60) 