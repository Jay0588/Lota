"""
JPTrades - Prediction Logger (Legacy)
Logs predictions to the database/trading.db (used by predict.py standalone).
"""

from datetime import datetime
from database import DatabaseManager


def log_prediction(price, signal, confidence):
    """Save a prediction to the legacy predictions database."""
    db = DatabaseManager()
    prediction_id = db.save_prediction(
        timestamp=datetime.now().isoformat(),
        symbol="NIFTY",
        price=float(price),
        prediction=signal,
        confidence=float(confidence)
    )
    return prediction_id
