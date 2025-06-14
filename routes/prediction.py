from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from enum import Enum
from controllers.prediction import predict_next_price

router = APIRouter()

class Timeframe(str, Enum):
    thirty_min = "30m"
    one_hour = "1h"
    four_hour = "4h"
    twenty_four_hour = "24h"

@router.get("/predict/{symbol}", operation_id="get_prediction_for_symbol")
async def get_prediction(symbol: str, timeframe: Timeframe):
    """
    Get a prediction for a given symbol and timeframe.
    This endpoint is public and requires no authentication.
    """
    try:
        if not symbol or len(symbol.strip()) == 0:
            raise ValueError("Symbol cannot be empty")

        prediction_result = await predict_next_price(symbol.upper(), timeframe.value)

        if isinstance(prediction_result, dict) and "error" in prediction_result:
            raise HTTPException(status_code=400, detail=prediction_result["error"])

        return prediction_result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as he:
        raise he
    except Exception as e:
        return JSONResponse(
            content={"detail": f"An unexpected internal server error occurred: {str(e)}"},
            status_code=500,
        )