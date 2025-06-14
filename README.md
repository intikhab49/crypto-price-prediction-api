# Crypto Price Prediction API

A machine learning-based cryptocurrency price prediction system using FastAPI, PyTorch, and multiple data sources.

## Features
- Real-time price predictions using BiLSTM with Attention mechanism
- Multiple timeframe support (30m, 1h, 4h, 24h)
- Data from both CoinGecko and Yahoo Finance
- WebSocket support for real-time updates
- Ensemble predictions for improved accuracy
- Support/Resistance level detection
- Technical indicators and sentiment analysis

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/crypto-prediction.git
cd crypto-prediction
```

2. Create a virtual environment:
```bash
python -m venv env
source env/bin/activate  # Linux/Mac
# or
.\env\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a .env file with the following configuration:
```
# API Keys
COINGECKO_API_KEY=your_api_key_here

# Database
DATABASE_URL=sqlite://db.sqlite3

# Model Settings
MODEL_PATH=models
CACHE_DIR=cache

# Logging
LOG_LEVEL=INFO
LOG_FILE=crypto_prediction.log

# Server
PORT=8000
HOST=0.0.0.0
```

5. Run migrations:
```bash
python run_migrations.py
```

6. Start the server:
```bash
uvicorn main:app --reload
```

## API Documentation

Once the server is running, visit:
- API documentation: http://localhost:8000/docs
- Alternative documentation: http://localhost:8000/redoc

## Environment Variables

- `COINGECKO_API_KEY`: Your CoinGecko API key (required for Pro API)
- `DATABASE_URL`: Database connection string (default: SQLite)
- `MODEL_PATH`: Directory for saved models
- `CACHE_DIR`: Directory for cached data
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `LOG_FILE`: Log file path
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

## Supported Cryptocurrencies

- BTC (Bitcoin)
- ETH (Ethereum)
- BNB (Binance Coin)
- XRP (Ripple)
- ADA (Cardano)
- DOGE (Dogecoin)
- SOL (Solana)

## Data Sources

1. CoinGecko API
   - Primary data source
   - Supports both free and Pro API
   - Automatic fallback to free API if Pro fails

2. Yahoo Finance
   - Secondary data source
   - Used as fallback when CoinGecko fails
   - More historical data available

## Model Architecture

The system uses a Bidirectional LSTM with Attention mechanism, featuring:
- Multiple timeframe support
- Ensemble predictions
- Technical indicators
- Sentiment analysis
- Support/Resistance detection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
