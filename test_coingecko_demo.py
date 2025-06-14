import os
import requests
import time
import pandas as pd
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CoinGecko API configuration
DEMO_API_KEY = ""
BASE_URL = "https://api.coingecko.com/api/v3"

def test_api_endpoints():
    session = requests.Session()
    session.headers.update({
        'x-cg-demo-api-key': DEMO_API_KEY,
        'Accept': 'application/json'
    })

    endpoints = [
        ("/ping", "Basic API health check"),
        ("/simple/price?ids=bitcoin&vs_currencies=usd", "Simple price endpoint"),
        ("/coins/bitcoin/market_chart?vs_currency=usd&days=1&interval=hourly", "Historical data endpoint"),
        ("/coins/markets?vs_currency=usd&ids=bitcoin&order=market_cap_desc&per_page=1&page=1&sparkline=false", "Markets endpoint")
    ]

    results = []
    for endpoint, description in endpoints:
        try:
            logger.info(f"\nTesting: {description}")
            start_time = time.time()
            response = session.get(f"{BASE_URL}{endpoint}")
            duration = time.time() - start_time

            result = {
                "endpoint": endpoint,
                "description": description,
                "status_code": response.status_code,
                "response_time": f"{duration:.2f}s",
                "rate_limit_remaining": response.headers.get('x-ratelimit-remaining', 'N/A'),
                "success": response.status_code == 200
            }

            if response.status_code == 200:
                logger.info(f"✅ Success - Response time: {duration:.2f}s")
                logger.info(f"Rate limit remaining: {result['rate_limit_remaining']}")
            else:
                logger.error(f"❌ Failed - Status: {response.status_code}")
                logger.error(f"Error message: {response.text}")

            results.append(result)
            time.sleep(2)  # Respect rate limiting

        except Exception as e:
            logger.error(f"Error testing {endpoint}: {str(e)}")
            results.append({
                "endpoint": endpoint,
                "description": description,
                "status_code": "Error",
                "response_time": "N/A",
                "rate_limit_remaining": "N/A",
                "success": False
            })

    return results

def test_historical_data():
    """Test historical data fetching with different timeframes"""
    session = requests.Session()
    session.headers.update({
        'x-cg-demo-api-key': DEMO_API_KEY,
        'Accept': 'application/json'
    })

    timeframes = [
        ("1h", "1"),
        ("4h", "7"),
        ("24h", "30")
    ]

    results = []
    for interval, days in timeframes:
        try:
            logger.info(f"\nTesting {interval} historical data ({days} days)")
            url = f"{BASE_URL}/coins/bitcoin/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'hourly' if interval != '24h' else 'daily'
            }

            start_time = time.time()
            response = session.get(url, params=params)
            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                result = {
                    "timeframe": interval,
                    "days": days,
                    "data_points": len(df),
                    "date_range": f"{df['timestamp'].min()} to {df['timestamp'].max()}",
                    "response_time": f"{duration:.2f}s",
                    "success": True
                }
                
                logger.info(f"✅ Success - Got {len(df)} data points")
                logger.info(f"Date range: {result['date_range']}")
                logger.info(f"Response time: {duration:.2f}s")
                
            else:
                result = {
                    "timeframe": interval,
                    "days": days,
                    "data_points": 0,
                    "date_range": "N/A",
                    "response_time": f"{duration:.2f}s",
                    "success": False
                }
                logger.error(f"❌ Failed - Status: {response.status_code}")
                logger.error(f"Error message: {response.text}")

            results.append(result)
            time.sleep(2)  # Respect rate limiting

        except Exception as e:
            logger.error(f"Error testing {interval} timeframe: {str(e)}")
            results.append({
                "timeframe": interval,
                "days": days,
                "data_points": 0,
                "date_range": "N/A",
                "response_time": "N/A",
                "success": False
            })

    return results

if __name__ == "__main__":
    logger.info("Starting CoinGecko Demo API Tests")
    
    logger.info("\n=== Testing API Endpoints ===")
    endpoint_results = test_api_endpoints()
    
    logger.info("\n=== Testing Historical Data ===")
    historical_results = test_historical_data()
    
    # Summary
    logger.info("\n=== Test Summary ===")
    logger.info(f"Endpoints tested: {len(endpoint_results)}")
    successful_endpoints = sum(1 for r in endpoint_results if r['success'])
    logger.info(f"Successful endpoints: {successful_endpoints}/{len(endpoint_results)}")
    
    logger.info(f"\nTimeframes tested: {len(historical_results)}")
    successful_timeframes = sum(1 for r in historical_results if r['success'])
    logger.info(f"Successful timeframes: {successful_timeframes}/{len(historical_results)}") 