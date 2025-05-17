import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routes.auth_routes import router as auth_router
from routes.prediction import router as prediction_router
from routes.coingecko import router as coingecko_router
from routes.yfinance import router as yfinance_router
from config import settings
from tortoise.contrib.fastapi import register_tortoise
from mangum import Mangum

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)
handler = Mangum(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origins in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
)

# Register routes
app.include_router(
    coingecko_router,
    prefix="/api/coingecko",
    tags=["CoinGecko"],
    responses={404: {"description": "Not found"}}
)
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}}
)
app.include_router(
    prediction_router,
    prefix=f"{settings.API_V1_PREFIX}/predictions",
    tags=["Predictions"],
    responses={404: {"description": "Not found"}}
)
app.include_router(
    yfinance_router,
    prefix=f"{settings.API_V1_PREFIX}/yfinance",
    tags=["YFinance"],
    responses={404: {"description": "Not found"}}
)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
register_tortoise(
    app,
    db_url=DATABASE_URL,
    modules={"models": ["models.user"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

@app.get("/")
def read_root():
    return {
        "status": "success",
        "message": "CryptoAion AI is running!",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_PREFIX}/docs"
    }

@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "CryptoAion AI is running"}

@app.options("/{path:path}")
async def options_handler(request: Request, path: str):
    return {"detail": "OK"}