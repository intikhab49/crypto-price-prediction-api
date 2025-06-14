import asyncio
import websockets
import json
import requests
import logging
import sys
from datetime import datetime
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Valid timeframes from the server's Timeframe enum
VALID_TIMEFRAMES = ["30m", "1h", "4h", "24h"]

async def get_auth_token():
    """Get authentication token by logging in with admin credentials"""
    login_data = {
        "username": "testadmin",
        "password": "testpass",
        "email": "testadmin@example.com"
    }
    
    try:
        # Try admin login
        login_response = requests.post(
            "http://localhost:8000/auth/admin/login",
            json=login_data
        )
        
        if login_response.status_code == 200:
            logger.info("Admin login successful")
            return login_response.json()["access_token"]
        
        logger.error(f"Admin login failed with status {login_response.status_code}: {login_response.text}")
        raise Exception(f"Admin login failed: {login_response.text}")
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise

async def test_websocket_connection(uri: str, timeout: int = 30) -> Optional[websockets.WebSocketClientProtocol]:
    """Test WebSocket connection with timeout"""
    try:
        websocket = await asyncio.wait_for(
            websockets.connect(uri, ping_interval=None),
            timeout=timeout
        )
        logger.info("WebSocket connection established")
        return websocket
    except asyncio.TimeoutError:
        logger.error(f"Connection timeout after {timeout} seconds")
        return None
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        return None

async def test_websocket_prediction(symbol: str, timeframe: str, token: str):
    """Test WebSocket prediction for a specific symbol and timeframe"""
    uri = f"ws://localhost:8000/ws/predict/{symbol}?token={token}&timeframe={timeframe}"
    logger.info(f"Testing {symbol} with {timeframe} timeframe")
    
    try:
        websocket = await test_websocket_connection(uri)
        if not websocket:
            return
        
        try:
            # Wait for 2 predictions
            for i in range(2):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(response)
                    logger.info(f"Received prediction {i+1} for {symbol}:")
                    logger.info(json.dumps(data, indent=2))
                    
                    # Verify prediction data
                    if "error" in data:
                        logger.error(f"Prediction error: {data['error']}")
                    else:
                        logger.info(f"Prediction successful: {data.get('predicted_price', 'N/A')}")
                        
                except asyncio.TimeoutError:
                    logger.warning(f"No prediction received for {symbol} within timeout")
                    break
                    
        finally:
            await websocket.close()
            
    except Exception as e:
        logger.error(f"Error testing {symbol}: {str(e)}")

async def main():
    """Run WebSocket tests for different symbols and timeframes"""
    try:
        # Get auth token
        token = await get_auth_token()
        
        # Test cases
        test_cases = [
            ("BTC-USD", "24h"),  # Test ensemble prediction
            ("ETH-USD", "1h"),   # Test standard prediction
            ("BNB-USD", "4h")    # Test another timeframe
        ]
        
        for symbol, timeframe in test_cases:
            if timeframe not in VALID_TIMEFRAMES:
                logger.error(f"Invalid timeframe {timeframe}")
                continue
                
            await test_websocket_prediction(symbol, timeframe, token)
            # Wait between tests
            await asyncio.sleep(5)
            
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
    except Exception as e:
        logger.error(f"Main loop error: {str(e)}")