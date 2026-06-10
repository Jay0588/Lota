"""
JPTrades - Signal Classification Engine
Converts model probability into a trading signal with strength classification.
"""

from config import BULLISH_THRESHOLD, BEARISH_THRESHOLD


def classify_signal(up_probability: float) -> dict:
    """
    Classify a model's UP probability into a trading signal.

    Args:
        up_probability: float between 0 and 1 representing P(price goes up)

    Returns:
        dict with 'signal' (str) and 'confidence' (float, 0-100)
    """
    down_probability = 1.0 - up_probability
    confidence = max(up_probability, down_probability)
    confidence_percent = round(confidence * 100, 2)

    # Below threshold = no trade
    if confidence < BULLISH_THRESHOLD:
        return {
            "signal": "NEUTRAL",
            "confidence": confidence_percent
        }

    if up_probability > down_probability:
        if confidence >= 0.70:
            signal = "STRONG BULLISH"
        else:
            signal = "BULLISH"
    else:
        if confidence >= 0.70:
            signal = "STRONG BEARISH"
        else:
            signal = "BEARISH"

    return {
        "signal": signal,
        "confidence": confidence_percent
    }
