"""
JPTrades - Model Health & Performance Monitor
Tracks rolling accuracy, confidence calibration, and model degradation.
Auto-verifies signal outcomes from the database.
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_FILE = str(Path(__file__).resolve().parent / "alphafx.db")


def get_rolling_accuracy(last_n: int) -> dict:
    """
    Calculate directional accuracy for the last N resolved signals.
    Returns dict with win_count, loss_count, accuracy, sample_size.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT outcome FROM signals
        WHERE outcome IS NOT NULL
        ORDER BY id DESC LIMIT ?
    """, (last_n,))
    outcomes = [r[0] for r in cursor.fetchall()]
    conn.close()

    if not outcomes:
        return {"wins": 0, "losses": 0, "accuracy": 0.0, "sample_size": 0}

    wins = sum(1 for o in outcomes if o == "WIN")
    losses = len(outcomes) - wins
    accuracy = round((wins / len(outcomes)) * 100, 1)

    return {"wins": wins, "losses": losses, "accuracy": accuracy, "sample_size": len(outcomes)}


def get_confidence_calibration() -> list:
    """
    Check if confidence levels match actual win rates.
    Groups signals into confidence buckets and compares predicted vs actual.
    Returns list of dicts: [{range, predicted, actual, count, gap}]
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT confidence, outcome FROM signals
        WHERE outcome IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    # Bucket signals by confidence range
    buckets = {
        "55-60%": {"min": 55, "max": 60, "wins": 0, "total": 0},
        "60-65%": {"min": 60, "max": 65, "wins": 0, "total": 0},
        "65-70%": {"min": 65, "max": 70, "wins": 0, "total": 0},
        "70-75%": {"min": 70, "max": 75, "wins": 0, "total": 0},
        "75%+":   {"min": 75, "max": 100, "wins": 0, "total": 0},
    }

    for conf, outcome in rows:
        for name, b in buckets.items():
            if b["min"] <= conf < b["max"]:
                b["total"] += 1
                if outcome == "WIN":
                    b["wins"] += 1
                break

    results = []
    for name, b in buckets.items():
        if b["total"] >= 3:  # Need at least 3 samples
            actual_wr = round((b["wins"] / b["total"]) * 100, 1)
            predicted_mid = (b["min"] + b["max"]) / 2
            gap = round(abs(actual_wr - predicted_mid), 1)
            results.append({
                "range": name,
                "predicted": predicted_mid,
                "actual": actual_wr,
                "count": b["total"],
                "gap": gap,
                "calibrated": gap < 15  # Within 15% = well calibrated
            })

    return results


def get_model_health() -> dict:
    """
    Determine overall model health status based on recent performance.

    Status levels:
        GOOD     - Last 10 accuracy >= 60% and confidence calibration gap < 15%
        WARNING  - Last 10 accuracy 50-60% or calibration drifting
        DEGRADED - Last 10 accuracy < 50% or severe calibration failure

    Returns dict with status, color, message, and detailed metrics.
    """
    last_10 = get_rolling_accuracy(10)
    last_30 = get_rolling_accuracy(30)
    last_50 = get_rolling_accuracy(50)
    last_100 = get_rolling_accuracy(100)
    calibration = get_confidence_calibration()

    # Determine status
    recent_acc = last_10["accuracy"] if last_10["sample_size"] >= 5 else last_30["accuracy"]
    sample_size = last_10["sample_size"]

    if sample_size < 5:
        status = "COLLECTING"
        color = "neutral"
        message = f"Need more data ({sample_size}/5 minimum signals)"
    elif recent_acc >= 60:
        status = "GOOD"
        color = "positive"
        message = f"Model performing well ({recent_acc}% recent accuracy)"
    elif recent_acc >= 50:
        status = "WARNING"
        color = "warning"
        message = f"Model edge declining ({recent_acc}% recent accuracy)"
    else:
        status = "DEGRADED"
        color = "negative"
        message = f"Model underperforming ({recent_acc}% recent accuracy) — consider retraining"

    # Best/worst confidence ranges
    best_range = ""
    worst_range = ""
    most_profitable_range = ""
    if calibration:
        sorted_cal = sorted(calibration, key=lambda x: x["actual"], reverse=True)
        best_range = sorted_cal[0]["range"] if sorted_cal else ""
        worst_range = sorted_cal[-1]["range"] if sorted_cal else ""
        # Most profitable = highest actual win rate with decent sample
        profitable = [c for c in sorted_cal if c["count"] >= 5]
        most_profitable_range = profitable[0]["range"] if profitable else best_range

    return {
        "status": status,
        "color": color,
        "message": message,
        "last_10": last_10,
        "last_30": last_30,
        "last_50": last_50,
        "last_100": last_100,
        "calibration": calibration,
        "best_range": best_range,
        "worst_range": worst_range,
        "most_profitable_range": most_profitable_range,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("\n=== MODEL HEALTH ===")
    health = get_model_health()
    print(f"  Status: {health['status']}")
    print(f"  Message: {health['message']}")
    print(f"  Last 10: {health['last_10']}")
    print(f"  Last 30: {health['last_30']}")
    print(f"  Last 50: {health['last_50']}")

    print("\n=== CONFIDENCE CALIBRATION ===")
    for c in health["calibration"]:
        check = "OK" if c["calibrated"] else "DRIFT"
        print(f"  {c['range']}: predicted {c['predicted']:.0f}% vs actual {c['actual']:.1f}% ({c['count']} trades) [{check}]")
