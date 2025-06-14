import asyncio
import websockets
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8000"
AUTH_URL = f"{BASE_URL}/auth"  # Auth endpoints are under /auth prefix
WS_BASE_URL = "ws://127.0.0.1:8000"

async def test_rest_api():
    print("\n=== Testing REST API ===")
    
    # 1. Register a test user
    register_url = f"{AUTH_URL}/register"
    user_data = {
        "username": "testuser123",
        "password": "testpass123",
        "email": "testuser123@example.com"  # Added required email field
    }
    
    try:
        response = requests.post(register_url, json=user_data)
        print(f"Registration response: {response.text}")  # Debug output
        if response.status_code == 201:
            print("✅ User registration successful")
            token = response.json()["access_token"]
        else:
            # Try logging in if user exists
            login_url = f"{AUTH_URL}/login"
            response = requests.post(login_url, json=user_data)
            print(f"Login response: {response.text}")  # Debug output
            if response.status_code == 200:
                print("✅ User login successful")
                token = response.json()["access_token"]
            else:
                print(f"❌ Authentication failed: {response.text}")
                return
        
        # 2. Test prediction endpoint
        headers = {"Authorization": f"Bearer {token}"}
        symbols = ["BTC-USD", "ETH-USD"]  # Reduced number of symbols for faster testing
        timeframes = ["30m", "24h"]  # Testing two timeframes
        
        for symbol in symbols:
            for timeframe in timeframes:
                print(f"\nTesting prediction for {symbol} ({timeframe})")
                pred_url = f"{BASE_URL}/api/predict/{symbol}?timeframe={timeframe}"
                response = requests.get(pred_url, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Prediction successful:")
                    print(json.dumps(result, indent=2))
                else:
                    print(f"❌ Prediction failed: {response.text}")
                await asyncio.sleep(1)  # Add small delay between requests
                
    except Exception as e:
        print(f"❌ Error during REST API testing: {str(e)}")

async def test_websocket():
    print("\n=== Testing WebSocket ===")
    
    # First get a token through REST API
    login_url = f"{AUTH_URL}/login"
    user_data = {
        "username": "testuser123",
        "password": "testpass123",
        "email": "testuser123@example.com"  # Added required email field
    }
    
    try:
        response = requests.post(login_url, json=user_data)
        if response.status_code != 200:
            print(f"❌ Failed to get token for WebSocket test: {response.text}")
            return
            
        token = response.json()["access_token"]
        symbol = "BTC-USD"
        timeframe = "24h"
        
        # Connect to WebSocket
        ws_url = f"{WS_BASE_URL}/ws/predict/{symbol}?token={token}&timeframe={timeframe}"
        print(f"\nConnecting to WebSocket: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connection established")
            
            # Wait for 2 predictions
            for i in range(2):
                try:
                    result = await websocket.recv()
                    print(f"\nPrediction {i+1}:")
                    print(json.dumps(json.loads(result), indent=2))
                    if i < 1:  # Don't sleep after last prediction
                        await asyncio.sleep(5)  # Wait between predictions
                except Exception as e:
                    print(f"❌ Error receiving prediction: {str(e)}")
                    break
                    
    except Exception as e:
        print(f"❌ Error during WebSocket testing: {str(e)}")

async def main():
    print("Starting API and WebSocket tests...")
    print(f"Time: {datetime.now()}")
    
    # Test REST API first
    await test_rest_api()
    
    # Then test WebSocket
    await test_websocket()

if __name__ == "__main__":
    asyncio.run(main())