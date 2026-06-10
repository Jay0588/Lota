"""
JPTrades - Market Data Engine (Cloud-Hardened)
Downloads NIFTY, BANKNIFTY, VIX data from yfinance with:
- Retry logic with exponential backoff
- Fallback periods (60d → 30d → 7d → 5d)
- Data caching for cloud reliability
- Detailed diagnostics
"""

import os
import json
import time
import platform
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

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
DIAGNOSTICS_FILE = CACHE_DIR / "market_diagnostics.json"

# Fallback periods (try in order)
FALLBACK_PERIODS = ["60d", "30d", "7d", "5d"]


def _download_with_retry(symbol: str, period: str = "60d", interval: str = "5m",
                         max_retries: int = 3) -> pd.DataFrame:
    """
    Download data from yfinance with retry logic and exponential backoff.
    Returns DataFrame or empty DataFrame on failure.
    """
    for attempt in range(max_retries):
        try:
            wait_time = (2 ** attempt) * 1  # 1s, 2s, 4s
            if attempt > 0:
                logger.info(f"  Retry {attempt + 1}/{max_retries} for {symbol} (waiting {wait_time}s)...")
                time.sleep(wait_time)

            start_time = time.time()
            data = yf.download(
                symbol,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
                timeout=20,
            )
            duration = round(time.time() - start_time, 2)

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            if not data.empty:
                logger.info(f"  {symbol}: {len(data)} rows in {duration}s (period={period})")
                return data
            else:
                logger.warning(f"  {symbol}: empty response (attempt {attempt + 1}, period={period})")

        except Exception as e:
            logger.warning(f"  {symbol}: error on attempt {attempt + 1}: {e}")

    return pd.DataFrame()


def _download_with_fallback(symbol: str, interval: str = "5m") -> pd.DataFrame:
    """
    Try downloading with progressively shorter periods until one works.
    """
    for period in FALLBACK_PERIODS:
        logger.info(f"  Trying {symbol} with period={period}...")
        data = _download_with_retry(symbol, period=period, interval=interval)
        if not data.empty:
            return data
        logger.warning(f"  {symbol} failed with period={period}")

    # Final attempt: daily data (almost always works)
    logger.warning(f"  {symbol}: All intraday attempts failed. Trying daily data...")
    data = _download_with_retry(symbol, period="60d", interval="1d")
    return data


def _save_diagnostics(results: dict):
    """Save download diagnostics for debugging."""
    try:
        results["timestamp"] = datetime.now().isoformat()
        results["python_version"] = platform.python_version()
        results["platform"] = platform.platform()
        results["is_cloud"] = os.getenv("RENDER", "") != "" or os.getenv("DYNO", "") != ""

        with open(DIAGNOSTICS_FILE, "w") as f:
            json.dump(results, f, indent=2, default=str)
    except Exception:
        pass


def get_diagnostics() -> dict:
    """Get latest market data diagnostics."""
    if DIAGNOSTICS_FILE.exists():
        try:
            with open(DIAGNOSTICS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"status": "no_diagnostics"}


class MarketData:

    def __init__(self):
        self.symbol = SYMBOL
        self._diagnostics = {}

    def download_data(self):
        """Download NIFTY 50 OHLCV data with full retry/fallback."""
        logger.info("Downloading NIFTY data...")
        data = _download_with_fallback(self.symbol, interval=DATA_INTERVAL)

        if data.empty:
            self._diagnostics["nifty"] = {"status": "FAILED", "rows": 0}
            raise Exception(f"No NIFTY data returned from yfinance after all retries")

        self._diagnostics["nifty"] = {"status": "OK", "rows": len(data)}
        return data

    def download_banknifty(self):
        """Download BANKNIFTY data with retry."""
        logger.info("Downloading BANKNIFTY data...")
        data = _download_with_fallback(BANKNIFTY_SYMBOL, interval=DATA_INTERVAL)
        self._diagnostics["banknifty"] = {
            "status": "OK" if not data.empty else "FAILED",
            "rows": len(data)
        }
        return data

    def download_vix(self):
        """Download India VIX data with retry."""
        logger.info("Downloading VIX data...")
        data = _download_with_fallback("^INDIAVIX", interval=DATA_INTERVAL)
        self._diagnostics["vix"] = {
            "status": "OK" if not data.empty else "FAILED",
            "rows": len(data)
        }
        return data

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
        Download all market data and compute features.
        Uses cache as fallback if downloads fail.
        """
        start_time = time.time()
        self._diagnostics = {}

        try:
            data = self.download_data()

            # BANKNIFTY
            bank = self.download_banknifty()
            if not bank.empty:
                data["BANK_CLOSE"] = bank["Close"]
            else:
                logger.warning("BANKNIFTY unavailable, using NIFTY as fallback")
                data["BANK_CLOSE"] = data["Close"]

            data["BANK_RETURN_1"] = data["BANK_CLOSE"].pct_change(1)
            data["BANK_RETURN_3"] = data["BANK_CLOSE"].pct_change(3)

            # VIX
            vix = self.download_vix()
            if not vix.empty:
                data["VIX_CLOSE"] = vix["Close"]
            else:
                logger.warning("VIX unavailable, using default 15.0")
                data["VIX_CLOSE"] = 15.0

            data["VIX_RETURN_1"] = data["VIX_CLOSE"].pct_change(1)
            data["VIX_RETURN_3"] = data["VIX_CLOSE"].pct_change(3)

            # Indicators
            data = self.add_indicators(data)
            data = data.dropna()

            # Cache successful download
            try:
                data.to_pickle(str(MARKET_CACHE_FILE))
                logger.info(f"Market data cached ({len(data)} rows)")
            except Exception as e:
                logger.warning(f"Failed to cache: {e}")

            duration = round(time.time() - start_time, 2)
            self._diagnostics["total_duration"] = duration
            self._diagnostics["total_rows"] = len(data)
            self._diagnostics["status"] = "SUCCESS"
            _save_diagnostics(self._diagnostics)

            return data

        except Exception as e:
            logger.error(f"Market data download failed: {e}")
            self._diagnostics["error"] = str(e)
            self._diagnostics["status"] = "FAILED"
            _save_diagnostics(self._diagnostics)

            # Try cache
            if MARKET_CACHE_FILE.exists():
                try:
                    cached = pd.read_pickle(str(MARKET_CACHE_FILE))
                    logger.warning(f"Using cached market data ({len(cached)} rows)")
                    self._diagnostics["status"] = "CACHED"
                    _save_diagnostics(self._diagnostics)
                    return cached
                except Exception:
                    pass

            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    md = MarketData()

    try:
        data = md.get_processed_data()
        print(f"\n=== SUCCESS: {len(data)} rows ===")
        print(f"Latest NIFTY: {data.iloc[-1]['Close']:.2f}")
    except Exception as e:
        print(f"\n=== FAILED: {e} ===")

    print(f"\nDiagnostics: {md._diagnostics}")
