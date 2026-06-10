"""
JPTrades - Signal Tracker
Resolves pending signals by comparing entry price with current NIFTY price.
Run this periodically to update win/loss outcomes.
"""

from pathlib import Path
from market_data import MarketData
from signal_logger import update_pending_signals

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_nifty():
    """Fetch the latest NIFTY price."""
    md = MarketData()
    data = md.get_processed_data()
    return float(data.iloc[-1]["Close"])


def run_tracker():
    """Fetch current price and resolve all pending signals."""
    current_price = get_current_nifty()
    logger.info(f"Current NIFTY: {current_price:.2f}")

    updated = update_pending_signals(current_price)
    logger.info(f"Updated {updated} pending signals")


if __name__ == "__main__":
    run_tracker()
