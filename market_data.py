"""
JPTrades - Market Data Engine (Multi-Provider)
Primary: Angel One SmartAPI (works on Render)
Fallback: Yahoo Finance (works locally)
Last resort: Cached data

Provider chain:
  SmartAPIProvider → YahooProvider → CachedProvider
"""

import os
import json
import time
import platform
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands

from config import (
    SYMBOL, BANKNIFTY_SYMBOL, DATA_PERIOD, DATA_INTERVAL, RSI_PERIOD
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "models"
CACHE_DIR.mkdir(exist_ok=True)
MARKET_CACHE_FILE = CACHE_DIR / "market_data_cache.pkl"
PROVIDER_STATUS_FILE = CACHE_DIR / "provider_status.json"


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER STATUS TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

_provider_status = {
    "active_provider": "none",
    "last_success": None,
    "last_error": None,
    "data_rows": 0,
    "nifty_price": 0,
    "freshness": "stale",
    "smartapi": {"status": "unknown", "last_attempt": None},
    "yahoo": {"status": "unknown", "last_attempt": None},
    "cache": {"status": "unknown", "rows": 0},
}


def get_provider_status():
    """Get current provider health status."""
    return _provider_status.copy()


def _update_status(provider: str, success: bool, rows: int = 0, error: str = None, price: float = 0):
    """Update provider status tracking."""
    global _provider_status
    now = datetime.now().isoformat()

    _provider_status[provider]["last_attempt"] = now
    _provider_status[provider]["status"] = "ok" if success else "failed"

    if success:
        _provider_status["active_provider"] = provider
        _provider_status["last_success"] = now
        _provider_status["data_rows"] = rows
        _provider_status["nifty_price"] = price
        _provider_status["freshness"] = "live"
        _provider_status["last_error"] = None
    else:
        _provider_status["last_error"] = error

    # Save to file for API access
    try:
        with open(PROVIDER_STATUS_FILE, "w") as f:
            json.dump(_provider_status, f, indent=2, default=str)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# SMARTAPI PROVIDER (Primary - works on Render)
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_smartapi_historical():
    """
    Fetch historical candle data from Angel One SmartAPI.
    Returns DataFrame with OHLCV data or empty DataFrame on failure.
    """
    try:
        import pyotp
        from dotenv import load_dotenv
        from SmartApi import SmartConnect

        load_dotenv()

        api_key = os.getenv("ANGEL_API_KEY")
        client_code = os.getenv("ANGEL_CLIENT_CODE")
        pin = os.getenv("ANGEL_PIN")
        totp_secret = os.getenv("ANGEL_TOTP_SECRET")

        if not all([api_key, client_code, pin, totp_secret]):
            logger.warning("SmartAPI: credentials missing")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        smart = SmartConnect(api_key=api_key)
        session = smart.generateSession(client_code, pin, pyotp.TOTP(totp_secret).now())

        if not session or session.get("status") is False:
            logger.warning("SmartAPI: login failed")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # Calculate date range (last 60 days for 5-min candles, max allowed)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)  # SmartAPI allows ~30 days for 5min

        # NIFTY 50 (token: 99926000, exchange: NSE)
        nifty_params = {
            "exchange": "NSE",
            "symboltoken": "99926000",
            "interval": "FIVE_MINUTE",
            "fromdate": from_date.strftime("%Y-%m-%d 09:15"),
            "todate": to_date.strftime("%Y-%m-%d 15:30"),
        }

        logger.info("SmartAPI: Fetching NIFTY historical data...")
        nifty_resp = smart.getCandleData(nifty_params)

        nifty_df = pd.DataFrame()
        if nifty_resp and nifty_resp.get("status") and nifty_resp.get("data"):
            candles = nifty_resp["data"]
            nifty_df = pd.DataFrame(candles, columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])
            nifty_df["Datetime"] = pd.to_datetime(nifty_df["Datetime"])
            nifty_df = nifty_df.set_index("Datetime")
            nifty_df = nifty_df.astype(float)
            logger.info(f"SmartAPI: NIFTY {len(nifty_df)} rows")

        # BANKNIFTY (token: 99926009)
        bank_params = {
            "exchange": "NSE",
            "symboltoken": "99926009",
            "interval": "FIVE_MINUTE",
            "fromdate": from_date.strftime("%Y-%m-%d 09:15"),
            "todate": to_date.strftime("%Y-%m-%d 15:30"),
        }

        logger.info("SmartAPI: Fetching BANKNIFTY historical data...")
        bank_resp = smart.getCandleData(bank_params)

        bank_df = pd.DataFrame()
        if bank_resp and bank_resp.get("status") and bank_resp.get("data"):
            candles = bank_resp["data"]
            bank_df = pd.DataFrame(candles, columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])
            bank_df["Datetime"] = pd.to_datetime(bank_df["Datetime"])
            bank_df = bank_df.set_index("Datetime")
            bank_df = bank_df.astype(float)
            logger.info(f"SmartAPI: BANKNIFTY {len(bank_df)} rows")

        # INDIA VIX (token: 99926004)
        vix_params = {
            "exchange": "NSE",
            "symboltoken": "99926004",
            "interval": "FIVE_MINUTE",
            "fromdate": from_date.strftime("%Y-%m-%d 09:15"),
            "todate": to_date.strftime("%Y-%m-%d 15:30"),
        }

        logger.info("SmartAPI: Fetching VIX historical data...")
        vix_resp = smart.getCandleData(vix_params)

        vix_df = pd.DataFrame()
        if vix_resp and vix_resp.get("status") and vix_resp.get("data"):
            candles = vix_resp["data"]
            vix_df = pd.DataFrame(candles, columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])
            vix_df["Datetime"] = pd.to_datetime(vix_df["Datetime"])
            vix_df = vix_df.set_index("Datetime")
            vix_df = vix_df.astype(float)
            logger.info(f"SmartAPI: VIX {len(vix_df)} rows")

        return nifty_df, bank_df, vix_df

    except Exception as e:
        logger.error(f"SmartAPI provider failed: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# YAHOO PROVIDER (Fallback - works locally, fails on Render)
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_yahoo():
    """Fetch data from Yahoo Finance. Works locally but fails on cloud."""
    try:
        import yfinance as yf

        logger.info("Yahoo: Fetching NIFTY...")
        nifty_df = yf.download(SYMBOL, period=DATA_PERIOD, interval=DATA_INTERVAL,
                               auto_adjust=True, progress=False, timeout=15)
        if isinstance(nifty_df.columns, pd.MultiIndex):
            nifty_df.columns = nifty_df.columns.get_level_values(0)

        logger.info("Yahoo: Fetching BANKNIFTY...")
        bank_df = yf.download(BANKNIFTY_SYMBOL, period=DATA_PERIOD, interval=DATA_INTERVAL,
                              auto_adjust=True, progress=False, timeout=15)
        if isinstance(bank_df.columns, pd.MultiIndex):
            bank_df.columns = bank_df.columns.get_level_values(0)

        logger.info("Yahoo: Fetching VIX...")
        vix_df = yf.download("^INDIAVIX", period=DATA_PERIOD, interval=DATA_INTERVAL,
                             auto_adjust=True, progress=False, timeout=15)
        if isinstance(vix_df.columns, pd.MultiIndex):
            vix_df.columns = vix_df.columns.get_level_values(0)

        rows = len(nifty_df)
        logger.info(f"Yahoo: NIFTY={rows}, BANK={len(bank_df)}, VIX={len(vix_df)}")

        return nifty_df, bank_df, vix_df

    except Exception as e:
        logger.error(f"Yahoo provider failed: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN MARKET DATA CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class MarketData:

    def __init__(self):
        self.symbol = SYMBOL

    def add_indicators(self, data):
        """Compute all technical indicators."""
        data["RSI"] = RSIIndicator(close=data["Close"], window=RSI_PERIOD).rsi()
        data["EMA20"] = EMAIndicator(close=data["Close"], window=20).ema_indicator()
        data["EMA50"] = EMAIndicator(close=data["Close"], window=50).ema_indicator()
        data["EMA200"] = EMAIndicator(close=data["Close"], window=200).ema_indicator()

        macd = MACD(close=data["Close"])
        data["MACD"] = macd.macd()
        data["MACD_SIGNAL"] = macd.macd_signal()
        data["MACD_HIST"] = macd.macd_diff()

        atr = AverageTrueRange(high=data["High"], low=data["Low"], close=data["Close"])
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
        Download market data using provider chain:
        1. Angel One SmartAPI (primary - works on cloud)
        2. Yahoo Finance (fallback - works locally)
        3. Cached data (last resort)
        """
        nifty_df = pd.DataFrame()
        bank_df = pd.DataFrame()
        vix_df = pd.DataFrame()

        # === PROVIDER 1: SmartAPI (primary) ===
        logger.info("Trying SmartAPI provider...")
        try:
            nifty_df, bank_df, vix_df = _fetch_smartapi_historical()
            if not nifty_df.empty and len(nifty_df) >= 50:
                _update_status("smartapi", True, len(nifty_df),
                               price=float(nifty_df["Close"].iloc[-1]))
                logger.info(f"SmartAPI: SUCCESS ({len(nifty_df)} rows)")
            else:
                _update_status("smartapi", False, 0, "Insufficient data")
                nifty_df = pd.DataFrame()  # Reset to try next provider
        except Exception as e:
            _update_status("smartapi", False, 0, str(e))
            logger.warning(f"SmartAPI failed: {e}")

        # === PROVIDER 2: Yahoo Finance (fallback) ===
        if nifty_df.empty:
            logger.info("Trying Yahoo provider...")
            try:
                nifty_df, bank_df, vix_df = _fetch_yahoo()
                if not nifty_df.empty and len(nifty_df) >= 50:
                    _update_status("yahoo", True, len(nifty_df),
                                   price=float(nifty_df["Close"].iloc[-1]))
                    logger.info(f"Yahoo: SUCCESS ({len(nifty_df)} rows)")
                else:
                    _update_status("yahoo", False, 0, "Empty response")
                    nifty_df = pd.DataFrame()
            except Exception as e:
                _update_status("yahoo", False, 0, str(e))
                logger.warning(f"Yahoo failed: {e}")

        # === PROVIDER 3: Cache (last resort) ===
        if nifty_df.empty:
            logger.warning("All providers failed. Trying cache...")
            if MARKET_CACHE_FILE.exists():
                try:
                    cached = pd.read_pickle(str(MARKET_CACHE_FILE))
                    if not cached.empty and len(cached) >= 50:
                        _update_status("cache", True, len(cached),
                                       price=float(cached["Close"].iloc[-1]))
                        _provider_status["freshness"] = "cached"
                        logger.warning(f"Using CACHED data ({len(cached)} rows)")
                        return cached
                except Exception as e:
                    _update_status("cache", False, 0, str(e))

            raise Exception("All market data providers failed and no cache available")

        # === BUILD COMBINED DATASET ===
        data = nifty_df.copy()

        # BANKNIFTY
        if not bank_df.empty:
            data["BANK_CLOSE"] = bank_df["Close"]
        else:
            logger.warning("BANKNIFTY unavailable, using NIFTY as fallback")
            data["BANK_CLOSE"] = data["Close"]

        data["BANK_RETURN_1"] = data["BANK_CLOSE"].pct_change(1)
        data["BANK_RETURN_3"] = data["BANK_CLOSE"].pct_change(3)

        # VIX
        if not vix_df.empty:
            data["VIX_CLOSE"] = vix_df["Close"]
        else:
            logger.warning("VIX unavailable, using default 15.0")
            data["VIX_CLOSE"] = 15.0

        data["VIX_RETURN_1"] = data["VIX_CLOSE"].pct_change(1)
        data["VIX_RETURN_3"] = data["VIX_CLOSE"].pct_change(3)

        # Indicators
        data = self.add_indicators(data)
        data = data.dropna()

        # Cache successful result
        try:
            data.to_pickle(str(MARKET_CACHE_FILE))
            _provider_status["cache"]["status"] = "available"
            _provider_status["cache"]["rows"] = len(data)
        except Exception:
            pass

        return data


def get_diagnostics():
    """Get provider diagnostics for API."""
    if PROVIDER_STATUS_FILE.exists():
        try:
            with open(PROVIDER_STATUS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return _provider_status


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    md = MarketData()

    try:
        data = md.get_processed_data()
        print(f"\nSUCCESS: {len(data)} rows")
        print(f"Provider: {_provider_status['active_provider']}")
        print(f"NIFTY: {data.iloc[-1]['Close']:.2f}")
    except Exception as e:
        print(f"\nFAILED: {e}")
        print(f"Status: {_provider_status}")
