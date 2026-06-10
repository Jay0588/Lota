import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# Download data
data = yf.download("^NSEI", period="5d", interval="5m")

# Fix MultiIndex columns
data.columns = data.columns.get_level_values(0)

# Indicators
data["RSI"] = RSIIndicator(data["Close"], window=14).rsi()
data["EMA20"] = EMAIndicator(data["Close"], window=20).ema_indicator()

# Latest row
latest = data.iloc[-1]

close = float(latest["Close"])
rsi = float(latest["RSI"])
ema20 = float(latest["EMA20"])

print("\n=== NIFTY ANALYSIS ===")
print(f"Close: {close:.2f}")
print(f"RSI: {rsi:.2f}")
print(f"EMA20: {ema20:.2f}")

# Simple prediction
prediction = "DOWN"

if close > ema20 and rsi > 55:
    prediction = "UP"

print(f"\nPrediction: {prediction}")