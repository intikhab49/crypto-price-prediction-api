from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # Database settings
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite://./db.sqlite3')
    
    # JWT settings
    JWT_SECRET: str = os.getenv('JWT_SECRET', 'your-secret-key')
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    
    # API settings
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "CryptoAion AI"
    BACKEND_CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    # Prediction settings
    DEFAULT_TIMEFRAME: str = "24h"
    TIMEFRAME_OPTIONS: list = ["30m", "1h", "4h", "24h"]
    
    # External API settings
    COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3"

# Tortoise ORM Settings
TORTOISE_ORM = {
    "connections": {"default": Settings().DATABASE_URL},
    "apps": {
        "models": {
            "models": ["models.user", "aerich.models"],
            "default_connection": "default",
        },
    },
}

settings = Settings()