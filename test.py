import yfinance as yf
ticker = yf.Ticker("BTC-USD")
data = ticker.history(period="1y")
print(data)
