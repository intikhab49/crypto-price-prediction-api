import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ---- Model Architecture (from notebook) ----
class BiLSTMAttentionModel(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size):
        super(BiLSTMAttentionModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, bidirectional=True)
        self.attention = nn.Linear(hidden_size * 2, 1)
        self.fc = nn.Linear(hidden_size * 2, output_size)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attention_weights = torch.softmax(self.attention(lstm_out), dim=1)
        context = torch.sum(attention_weights * lstm_out, dim=1)
        return self.fc(context)

# ---- Fetch BTC Data ----
def fetch_btc_data():
    data = yf.download(tickers="BTC-USD", period="60d", interval="1h")
    if data.empty:
        raise ValueError("No data fetched from yfinance")
    return data

# ---- Add Technical Indicators ----
def add_technical_indicators(df):
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
    df['Bollinger_Upper'] = df['Close'].rolling(window=20).mean() + 2 * df['Close'].rolling(window=20).std()
    df['Bollinger_Lower'] = df['Close'].rolling(window=20).mean() - 2 * df['Close'].rolling(window=20).std()
    df.dropna(inplace=True)
    return df

# ---- Optional: Add Sentiment Score ----
def add_sentiment_score(df):
    analyzer = SentimentIntensityAnalyzer()
    sentiment_score = analyzer.polarity_scores("Bitcoin is trending bullish")['compound']
    df['Sentiment'] = sentiment_score
    return df

# ---- Normalize and Prepare Input Tensor ----
def prepare_features(df):
    features = df[['Close', 'SMA_10', 'RSI', 'MACD', 'Bollinger_Upper', 'Bollinger_Lower']]
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(features)
    input_seq = torch.tensor(scaled[-60:], dtype=torch.float32).unsqueeze(0)  # (1, 60, 6)
    return input_seq

# ---- Load Model from File ----
def load_model(path='bilstm_attention_model.pth'):
    model = BiLSTMAttentionModel(input_size=6, hidden_size=64, num_layers=2, output_size=1)
    model.load_state_dict(torch.load(path, map_location=torch.device('cpu')))
    model.eval()
    return model

# ---- High-Level Inference Function ----
def fetch_and_predict_btc_price():
    df = fetch_btc_data()
    df = add_technical_indicators(df)
    df = add_sentiment_score(df)
    input_tensor = prepare_features(df)
    model = load_model()
    with torch.no_grad():
        prediction = model(input_tensor).item()
    return prediction

#temprary adding 
if __name__ == "__main__":
    price = fetch_and_predict_btc_price()
    print("Predicted BTC Price:", price)
