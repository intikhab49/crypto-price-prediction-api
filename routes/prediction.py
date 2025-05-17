from fastapi import APIRouter, HTTPException
from controllers.prediction import predict_next_price
from config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@router.get("/prediction/{symbol}/{timeframe}")
async def get_prediction(symbol: str, timeframe: str):
    try:
        logger.debug(f"Received GET request for prediction: symbol={symbol}, timeframe={timeframe}")
        if timeframe not in settings.TIMEFRAME_OPTIONS:
            error_msg = f"Invalid timeframe. Must be one of: {', '.join(settings.TIMEFRAME_OPTIONS)}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        result = predict_next_price(symbol, timeframe)
        if "error" in result:
            logger.error(f"Prediction error: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
        
        logger.debug(f"Prediction successful: {result}")
        return result
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/predict")
async def post_prediction(data: dict):
    try:
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        if not symbol or not timeframe:
            error_msg = "Missing symbol or timeframe in request body"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.debug(f"Received POST request for prediction: symbol={symbol}, timeframe={timeframe}")
        if timeframe not in settings.TIMEFRAME_OPTIONS:
            error_msg = f"Invalid timeframe. Must be one of: {', '.join(settings.TIMEFRAME_OPTIONS)}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        result = predict_next_price(symbol, timeframe)
        if "error" in result:
            logger.error(f"Prediction error: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
        
        logger.debug(f"Prediction successful: {result}")
        return result
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")