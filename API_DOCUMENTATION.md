# Crypto Price Prediction API Documentation

**Version:** 1.0.0  
**Last Updated:** March 2024  
**Author:** CryptoAion AI Team

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
5. [WebSocket Integration](#websocket-integration)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [Code Examples](#code-examples)
9. [Troubleshooting](#troubleshooting)
10. [Support](#support)

---

## 1. Introduction

The CryptoAion AI API provides real-time cryptocurrency price predictions, historical data, and live market updates through both REST endpoints and WebSocket connections. This documentation provides comprehensive guidance for frontend developers to integrate with our services.

### Key Features

- Real-time price predictions using advanced AI models
- Historical data from multiple sources (CoinGecko and Yahoo Finance)
- Live price updates via WebSocket
- Secure authentication system
- Automatic rate limiting and caching
- Multiple timeframe support (30m, 1h, 4h, 24h)

---

## 2. Getting Started

### Base URL
```
https://your-api-domain.com
```

### Requirements
- Valid API credentials
- HTTPS support
- Modern web browser or Node.js environment

### Supported Cryptocurrencies
- Bitcoin (BTC)
- Ethereum (ETH)
- Binance Coin (BNB)
- And more...

---

## 3. Authentication

### Registration
```http
POST /auth/register
Content-Type: application/json

{
    "username": "string",
    "email": "string",
    "password": "string"
}
```

### Login
```http
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

### Authentication Headers
```http
Authorization: Bearer <your_access_token>
```

---

## 4. API Endpoints

### 4.1 Price Predictions

#### Get Price Prediction
```http
GET /api/predict/{symbol}?timeframe={timeframe}

Parameters:
- symbol: Cryptocurrency symbol (e.g., "BTC-USD")
- timeframe: Optional, defaults to "24h"
  Options: ["30m", "1h", "4h", "24h"]

Response:
{
    "symbol": "BTC-USD",
    "predicted_price": 45000.00,
    "confidence": 0.85,
    "timestamp": "2024-03-14T12:00:00Z"
}
```

### 4.2 Historical Data

#### CoinGecko Historical Data
```http
GET /api/coingecko/historical/{coin_id}
Parameters:
- coin_id: Cryptocurrency ID (e.g., "bitcoin")
- days: Optional (default: 7)

Response:
{
    "prices": [[timestamp, price], ...],
    "market_caps": [[timestamp, market_cap], ...],
    "total_volumes": [[timestamp, volume], ...]
}
```

#### Yahoo Finance Historical Data
```http
GET /api/yfinance/historical/{symbol}
Parameters:
- symbol: Cryptocurrency symbol
- period: Optional (default: "7d")
  Options: ["1d", "7d", "1mo", "3mo", "6mo", "1y", "2y"]
- interval: Optional (default: "1d")
```

### 4.3 Real-time Market Data

#### Get Trending Coins
```http
GET /api/coingecko/realtime

Response:
{
    "coins": [...],
    "exchanges": [...]
}
```

#### Get Specific Coin Data
```http
GET /api/coingecko/by-symbol/{symbol}
GET /api/coingecko/{coin_id}

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

---

## 5. WebSocket Integration

### Connection
```javascript
const ws = new WebSocket('wss://your-api-domain.com/ws/{symbol}?timeframe=1h');
```

### Event Handling
```javascript
ws.onopen = () => {
    console.log('Connected to WebSocket');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle real-time updates
};

ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

---

## 6. Error Handling

### Error Response Format
```javascript
{
    "error": "Error message",
    "detail": "Detailed error information" // Optional
}
```

### HTTP Status Codes
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Rate Limit Exceeded
- 500: Internal Server Error

---

## 7. Best Practices

### Authentication
- Store access tokens securely
- Implement token refresh logic
- Include authentication headers in all requests

### Rate Limiting
- Implement request throttling
- Cache responses when appropriate
- Handle rate limit errors gracefully

### WebSocket Management
- Implement automatic reconnection
- Handle connection errors
- Clean up connections properly

### Data Handling
- Implement proper error handling
- Cache frequently accessed data
- Validate data before display

---

## 8. Code Examples

### Complete Data Service Implementation
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

### WebSocket Manager Implementation
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
        this.ws = new WebSocket(
            `wss://your-api-domain.com/ws/${this.symbol}?timeframe=${this.timeframe}`
        );
        
        this.ws.onopen = () => {
            console.log('Connected to WebSocket');
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
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
            console.log(
                `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
            );
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

---

## 9. Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify API credentials
   - Check token expiration
   - Ensure proper header format

2. **Rate Limiting**
   - Implement caching
   - Add request throttling
   - Use bulk endpoints when available

3. **WebSocket Disconnections**
   - Implement reconnection logic
   - Check network stability
   - Monitor connection status

4. **Data Inconsistencies**
   - Validate response data
   - Check timestamp alignment
   - Verify data source status

---

## 10. Support

### Contact Information
- Technical Support: support@cryptoaion.ai
- API Status: status.cryptoaion.ai
- Documentation Updates: docs.cryptoaion.ai

### Additional Resources
- API Status Dashboard
- GitHub Repository
- Community Forum
- Developer Blog

---

*Note: This documentation is continuously updated. Please check regularly for the latest information and features.* 