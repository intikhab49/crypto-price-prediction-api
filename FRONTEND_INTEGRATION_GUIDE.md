# Crypto Price Prediction API - Frontend Integration Guide

## Overview
This guide provides comprehensive instructions for frontend developers to integrate with the Crypto Price Prediction API. The API provides real-time cryptocurrency price predictions, historical data, and live price updates through both REST endpoints and WebSocket connections.

## Base URL
```
https://your-api-domain.com
```

## Authentication
The API uses token-based authentication for secure endpoints.

### Authentication Endpoints

#### 1. Register User
```
POST /auth/register
Content-Type: application/json

{
    "username": "string",
    "email": "string",
    "password": "string"
}
```

#### 2. Login
```
POST /auth/login
Content-Type: application/json

{
    "username": "string",
    "password": "string"
}

Response:
{
    "access_token": "string",
    "token_type": "bearer"
}
```

## Core Features

### 1. Price Predictions

#### Get Price Prediction
```
GET /api/predict/{symbol}?timeframe={timeframe}

Parameters:
- symbol: Cryptocurrency symbol (e.g., "BTC-USD")
- timeframe: Optional, defaults to "24h". Options: ["30m", "1h", "4h", "24h"]

Response:
{
    "symbol": "BTC-USD",
    "predicted_price": 45000.00,
    "confidence": 0.85,
    "timestamp": "2024-03-14T12:00:00Z"
}
```

### 2. Historical Data

#### CoinGecko Data Endpoints

1. Real-time Trending Data
```
GET /api/coingecko/realtime

Response:
{
    "coins": [...],
    "exchanges": [...]
}
```

2. Historical Data
```
GET /api/coingecko/historical/{coin_id}
Parameters:
- coin_id: Cryptocurrency ID (e.g., "bitcoin", "ethereum")
- days: Optional (default: 7) - Number of days of historical data

Response:
{
    "prices": [[timestamp, price], ...],
    "market_caps": [[timestamp, market_cap], ...],
    "total_volumes": [[timestamp, volume], ...]
}
```

3. Current Coin Data
```
GET /api/coingecko/by-symbol/{symbol}
GET /api/coingecko/{coin_id}

Parameters:
- symbol: Trading symbol (e.g., "BTC", "ETH")
- coin_id: CoinGecko coin ID (e.g., "bitcoin", "ethereum")

Response:
{
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "current_price": 45000.00,
    "market_cap": 850000000000,
    ...
}
```

Note: The API includes automatic rate limiting and caching to prevent hitting CoinGecko's rate limits. Responses are cached for 10 minutes.

#### Yahoo Finance Historical Data
```
GET /api/yfinance/historical/{symbol}
Parameters:
- symbol: Cryptocurrency symbol
- period: Optional (default: "7d", options: "1d", "7d", "1mo", "3mo", "6mo", "1y", "2y")
- interval: Optional (default: "1d")
```

### 3. Real-time Updates (WebSocket)

#### Connect to WebSocket
```javascript
const ws = new WebSocket('wss://your-api-domain.com/ws/{symbol}?timeframe=1h');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
};
```

## Implementation Examples

### 1. Basic Price Prediction
```javascript
async function getPrediction(symbol, timeframe = '24h') {
    try {
        const response = await fetch(`/api/predict/${symbol}?timeframe=${timeframe}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to get prediction');
        }
        
        return data;
    } catch (error) {
        console.error('Prediction error:', error);
        throw error;
    }
}
```

### 2. Historical Data with Error Handling
```javascript
async function getHistoricalData(symbol, period = '7d', source = 'coingecko') {
    const endpoint = source === 'coingecko' 
        ? `/api/coingecko/historical/${symbol}`
        : `/api/yfinance/historical/${symbol}`;
        
    try {
        const response = await fetch(`${endpoint}?period=${period}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch historical data');
        }
        
        return data;
    } catch (error) {
        console.error('Historical data error:', error);
        throw error;
    }
}
```

### 3. WebSocket Integration with Reconnection
```javascript
class CryptoWebSocket {
    constructor(symbol, timeframe = '1h') {
        this.symbol = symbol;
        this.timeframe = timeframe;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(`wss://your-api-domain.com/ws/${this.symbol}?timeframe=${this.timeframe}`);
        
        this.ws.onopen = () => {
            console.log('Connected to WebSocket');
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            // Handle the received data
            this.handleData(data);
        };

        this.ws.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            this.handleReconnection();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleData(data) {
        // Implement your data handling logic
        console.log('Received data:', data);
    }

    handleReconnection() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connect(), 5000);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}
```

### 4. Fetching Real-time Trending Data
```javascript
async function getTrendingData() {
    try {
        const response = await fetch('/api/coingecko/realtime');
        const data = await response.json();
        
        if (!response.ok) {
            if (response.status === 429) {
                // Handle rate limit
                throw new Error('Rate limit reached. Please try again later.');
            }
            throw new Error(data.error || 'Failed to fetch trending data');
        }
        
        return data;
    } catch (error) {
        console.error('Trending data error:', error);
        throw error;
    }
}

### 5. Complete Data Service Example
```javascript
class CryptoDataService {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.cache = new Map();
        this.cacheTimeout = 10 * 60 * 1000; // 10 minutes
    }

    async fetchWithCache(endpoint, cacheKey) {
        const cached = this.cache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }

        this.cache.set(cacheKey, {
            timestamp: Date.now(),
            data
        });

        return data;
    }

    async getTrendingCoins() {
        return this.fetchWithCache('/api/coingecko/realtime', 'trending');
    }

    async getHistoricalData(symbol, days = 7) {
        return this.fetchWithCache(
            `/api/coingecko/historical/${symbol}?days=${days}`,
            `historical_${symbol}_${days}`
        );
    }

    async getCoinData(symbol) {
        return this.fetchWithCache(
            `/api/coingecko/by-symbol/${symbol}`,
            `coin_${symbol}`
        );
    }

    async getPrediction(symbol, timeframe = '24h') {
        // Predictions shouldn't be cached
        const response = await fetch(
            `${this.baseUrl}/api/predict/${symbol}?timeframe=${timeframe}`
        );
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to get prediction');
        }

        return data;
    }
}
```

## Error Handling
The API returns standardized error responses:
```javascript
{
    "error": "Error message",
    "detail": "Detailed error information" // Optional
}
```

Common HTTP status codes:
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

## Best Practices

1. **Authentication**
   - Store the access token securely
   - Implement token refresh logic
   - Include the token in all authenticated requests

2. **WebSocket Management**
   - Implement reconnection logic
   - Handle connection errors gracefully
   - Clean up WebSocket connections when components unmount

3. **Error Handling**
   - Implement comprehensive error handling
   - Show user-friendly error messages
   - Log errors for debugging

4. **Data Caching**
   - Cache historical data when appropriate
   - Implement proper cache invalidation
   - Use local storage for frequently accessed data

5. **Rate Limiting**
   - Implement request throttling
   - Handle rate limit errors gracefully
   - Show appropriate feedback to users

## Support
For technical support or questions about the API integration, please contact our development team or refer to the API documentation. 