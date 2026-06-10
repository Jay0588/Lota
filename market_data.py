"""
JPTrades - Market Data Engine
Downloads NIFTY, BANKNIFTY, VIX data from yfinance and computes technical indicators.
Option features from Angel One are loaded separately and are optional.
"""

import pandas as pd
import yfinance as yf
import logging

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands

from config import (
    SYMBOL,
    BANKNIFTY_SYMBOL,
    DATA_PERIOD,
    DATA_INTERVAL,
    RSI_PERIOD
)

logger = logging.getLogger(__name__)


class MarketData:

    def __init__(self):
        self.symbol = SYMBOL

    def download_data(self):
        """Download NIFTY 50 OHLCV data."""
        data = yf.download(
            self.symbol,
            period=DATA_PERIOD,
            interval=DATA_INTERVAL,
            auto_adjust=True,
            progress=False
        )

        if data.empty:
            raise Exception("No NIFTY data returned from yfinance")

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        return data

    def download_banknifty(self):
        """Download BANKNIFTY data."""
        bank = yf.download(
            BANKNIFTY_SYMBOL,
            period=DATA_PERIOD,
            interval=DATA_INTERVAL,
            auto_adjust=True,
            progress=False
        )

        if isinstance(bank.columns, pd.MultiIndex):
            bank.columns = bank.columns.get_level_values(0)

        return bank

    def download_vix(self):
        """Download India VIX data."""
        vix = yf.download(
            "^INDIAVIX",
            period=DATA_PERIOD,
            interval=DATA_INTERVAL,
            auto_adjust=True,
            progress=False
        )

        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)

        return vix

    def add_indicators(self, data):
        """Compute all technical indicators."""
        data["RSI"] = RSIIndicator(
            close=data["Close"], window=RSI_PERIOD
        ).rsi()

        data["EMA20"] = EMAIndicator(
            close=data["Close"], window=20
        ).ema_indicator()

        data["EMA50"] = EMAIndicator(
            close=data["Close"], window=50
        ).ema_indicator()

        data["EMA200"] = EMAIndicator(
            close=data["Close"], window=200
        ).ema_indicator()

        macd = MACD(close=data["Close"])
        data["MACD"] = macd.macd()
        data["MACD_SIGNAL"] = macd.macd_signal()
        data["MACD_HIST"] = macd.macd_diff()

        atr = AverageTrueRange(
            high=data["High"], low=data["Low"], close=data["Close"]
        )
        data["ATR"] = atr.average_true_range()

        bb = BollingerBands(close=data["Close"])
        data["BB_UPPER"] = bb.bollinger_hband()
        data["BB_LOWER"] = bb.bollinger_lband()
        data["BB_WIDTH"] = data["BB_UPPER"] - data["BB_LOWER"]

        data["EMA_DIFF"] = data["EMA20"] - data["EMA50"]
        data["PRICE_EMA20"] = data["Close"] - data["EMA20"]

        data["RETURN_1"] = data["Close"].pct_change(1)
        data["RETURN_3"] = data["Close"].pct_change(3)
        data["RETURN_6"] = data["Close"].pct_change(6)

        data["HOUR"] = data.index.hour
        data["MINUTE"] = data.index.minute

        return data

    def get_processed_data(self):
        """
        Download all market data and compute features.
        Returns a clean DataFrame with no NaN rows.
        Option features are NOT included here (handled separately in app.py).
        """
        data = self.download_data()

        # BANKNIFTY
        bank = self.download_banknifty()
        if not bank.empty:
            data["BANK_CLOSE"] = bank["Close"]
        else:
            logger.warning("BANKNIFTY data unavailable, using NIFTY Close as fallback")
            data["BANK_CLOSE"] = data["Close"]

        data["BANK_RETURN_1"] = data["BANK_CLOSE"].pct_change(1)
        data["BANK_RETURN_3"] = data["BANK_CLOSE"].pct_change(3)

        # INDIA VIX
        vix = self.download_vix()
        if not vix.empty:
            data["VIX_CLOSE"] = vix["Close"]
        else:
            logger.warning("VIX data unavailable, using default 15.0")
            data["VIX_CLOSE"] = 15.0

        data["VIX_RETURN_1"] = data["VIX_CLOSE"].pct_change(1)
        data["VIX_RETURN_3"] = data["VIX_CLOSE"].pct_change(3)

        # Technical indicators
        data = self.add_indicators(data)

        return data.dropna()


if __name__ == "__main__":
    md = MarketData()
    data = md.get_processed_data()

    print(f"\n=== DATA LOADED ({len(data)} rows) ===\n")
    print(data.tail())

    latest = data.iloc[-1]
    print(f"\n=== LATEST ===")
    print(f"NIFTY:     {latest['Close']:.2f}")
    print(f"BANKNIFTY: {latest['BANK_CLOSE']:.2f}")
    print(f"VIX:       {latest['VIX_CLOSE']:.2f}")
    print(f"RSI:       {latest['RSI']:.2f}")
    print(f"MACD:      {latest['MACD']:.4f}")
