"""
JPTrades - Trade Generator
Converts a signal + confidence into a concrete trade recommendation.
"""

from config import DEFAULT_STOP_LOSS_PERCENT, DEFAULT_TARGET_PERCENT


def generate_trade(signal: str, confidence: float) -> dict:
    """
    Generate a trade recommendation based on signal and confidence.

    Args:
        signal: "BULLISH", "STRONG BULLISH", "BEARISH", "STRONG BEARISH", or "NEUTRAL"
        confidence: 0-100 confidence percentage

    Returns:
        dict with trade, risk, sl, target
    """
    if signal == "NEUTRAL" or "NO TRADE" in signal:
        return {
            "trade": "NO TRADE",
            "risk": "NONE",
            "sl": "N/A",
            "target": "N/A"
        }

    # Adjust SL/target based on confidence
    if confidence >= 75:
        risk = "HIGH CONVICTION"
        sl_pct = DEFAULT_STOP_LOSS_PERCENT
        target_pct = DEFAULT_TARGET_PERCENT + 10  # More aggressive target
    elif confidence >= 65:
        risk = "MODERATE"
        sl_pct = DEFAULT_STOP_LOSS_PERCENT
        target_pct = DEFAULT_TARGET_PERCENT
    else:
        risk = "LOW CONVICTION"
        sl_pct = DEFAULT_STOP_LOSS_PERCENT - 3  # Tighter SL
        target_pct = DEFAULT_TARGET_PERCENT - 5  # Conservative target

    if "BULLISH" in signal:
        return {
            "trade": "BUY ATM CALL (CE)",
            "risk": risk,
            "sl": f"-{sl_pct}%",
            "target": f"+{target_pct}%"
        }

    return {
        "trade": "BUY ATM PUT (PE)",
        "risk": risk,
        "sl": f"-{sl_pct}%",
        "target": f"+{target_pct}%"
    }
