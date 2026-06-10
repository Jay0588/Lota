"""
JPTrades - Configuration
Central configuration file for all modules.
"""

from pathlib import Path

# ==========================================
# PROJECT PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_DIR = BASE_DIR / "database"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"

DATABASE_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ==========================================
# DATABASE
# ==========================================

DATABASE_PATH = DATABASE_DIR / "trading.db"

# ==========================================
# MARKET SETTINGS
# ==========================================

SYMBOL = "^NSEI"              # NIFTY 50
BANKNIFTY_SYMBOL = "^NSEBANK" # BANKNIFTY

DATA_PERIOD = "60d"           # 60 days (max for 5-min candles on yfinance)
DATA_INTERVAL = "5m"          # 5-minute candles
# Note: yfinance caps intraday data at 60 days. For longer history, use daily interval.

# ==========================================
# INDICATORS
# ==========================================

RSI_PERIOD = 14
EMA_FAST = 20
EMA_SLOW = 50

# ==========================================
# PREDICTION SETTINGS
# ==========================================

PREDICTION_HORIZON = 3
# 3 candles = 15 minutes on 5m timeframe
# Target: price moves >0.3% in this window (audit-optimized)

TARGET_THRESHOLD = 0.003  # 0.3% move required

TEST_SIZE = 0.20
RANDOM_STATE = 42

# ==========================================
# MODEL FILES
# ==========================================

MODEL_FILE = MODELS_DIR / "nifty_model.pkl"

# ==========================================
# SIGNAL SETTINGS
# ==========================================

BULLISH_THRESHOLD = 0.60   # Minimum confidence to generate a signal
BEARISH_THRESHOLD = 0.40   # Below this = bearish

# ==========================================
# TRADE SETTINGS
# ==========================================

DEFAULT_STOP_LOSS_PERCENT = 10
DEFAULT_TARGET_PERCENT = 20

# ==========================================
# REFRESH SETTINGS
# ==========================================

PREDICTION_REFRESH_SECONDS = 300  # 5 minutes

# ==========================================
# LOGGING
# ==========================================

LOG_FILE = LOGS_DIR / "JPTrades.log"
