import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to import from main project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from controllers.data_fetcher import DataFetcher
from controllers.prediction import predict_next_price, prepare_features, add_technical_indicators
from controllers.model_trainer import train_model
from controllers.error_handler import error_tracker, ErrorSeverity, ErrorCategory

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TestClient(app)

async def test_data_fetching():
    """Test data fetching for different timeframes"""
    symbols = ["BTC", "ETH", "BNB"]
    timeframes = ["1h", "4h", "24h", "7d"]
    
    data_fetcher = DataFetcher()
    results = {}
    
    for symbol in symbols:
        results[symbol] = {}
        for timeframe in timeframes:
            try:
                logger.info(f"Testing data fetch for {symbol} with timeframe {timeframe}")
                data = await data_fetcher.get_historical_data(symbol, timeframe)
                
                if data is not None:
                    results[symbol][timeframe] = {
                        "success": True,
                        "rows": len(data),
                        "columns": list(data.columns),
                        "date_range": f"{data.index.min()} to {data.index.max()}"
                    }
                else:
                    results[symbol][timeframe] = {
                        "success": False,
                        "error": "No data returned"
                    }
            except Exception as e:
                results[symbol][timeframe] = {
                    "success": False,
                    "error": str(e)
                }
                
    return results

def test_model_pipeline(symbol="BTC", timeframe="24h"):
    """Test the entire model pipeline"""
    try:
        # 1. Get historical data
        data_fetcher = DataFetcher()
        data = asyncio.run(data_fetcher.get_historical_data(symbol, timeframe))
        
        if data is None:
            raise ValueError(f"No data available for {symbol}")
            
        # 2. Add technical indicators
        data = add_technical_indicators(data)
        
        # 3. Prepare features
        features = prepare_features(data)
        
        # 4. Split data for training
        train_size = int(len(features) * 0.8)
        X_train = features[:train_size]
        y_train = data['Close'].values[:train_size]
        X_val = features[train_size:]
        y_val = data['Close'].values[train_size:]
        
        # 5. Train model
        model = train_model(X_train, y_train, X_val, y_val, None, timeframe, symbol)
        
        return {
            "success": True,
            "data_shape": data.shape,
            "features_shape": features.shape,
            "train_size": len(X_train),
            "val_size": len(X_val)
        }
        
    except Exception as e:
        error_id = error_tracker.track_error(
            error=e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.MODEL,
            source="test_pipeline"
        )
        return {
            "success": False,
            "error": str(e),
            "error_id": error_id
        }

def test_api_endpoints():
    """Test API endpoints for different timeframes"""
    symbols = ["BTC", "ETH"]
    timeframes = ["1h", "4h", "24h", "7d"]
    results = {}
    
    for symbol in symbols:
        results[symbol] = {}
        for timeframe in timeframes:
            try:
                # Test prediction endpoint
                response = client.get(f"/api/predict/{symbol}?timeframe={timeframe}")
                results[symbol][timeframe] = {
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else str(response.content)
                }
            except Exception as e:
                results[symbol][timeframe] = {
                    "status_code": 500,
                    "error": str(e)
                }
                
    return results

if __name__ == "__main__":
    # Run all tests
    logger.info("Starting pipeline tests...")
    
    # 1. Test data fetching
    logger.info("\nTesting data fetching...")
    data_results = asyncio.run(test_data_fetching())
    print("\nData Fetching Results:")
    print(pd.DataFrame(data_results).to_string())
    
    # 2. Test model pipeline
    logger.info("\nTesting model pipeline...")
    pipeline_results = test_model_pipeline()
    print("\nModel Pipeline Results:")
    print(pd.DataFrame([pipeline_results]).to_string())
    
    # 3. Test API endpoints
    logger.info("\nTesting API endpoints...")
    api_results = test_api_endpoints()
    print("\nAPI Testing Results:")
    print(pd.DataFrame(api_results).to_string()) 