import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.prediction import router as prediction_router
from routes.coingecko import router as coingecko_router
from routes.yfinance import router as yfinance_router
import logging

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log')
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Crypto Price Prediction API",
    description="API for cryptocurrency price prediction using machine learning",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(prediction_router, prefix="/api")
app.include_router(coingecko_router, prefix="/api/coingecko", tags=["CoinGecko Data"])
app.include_router(yfinance_router, prefix="/api/yfinance", tags=["Yahoo Finance Data"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "online",
        "version": "1.0.0",
        "endpoints": [
            "/api/predict/{symbol}"
        ]
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": "2.0.0"}

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
