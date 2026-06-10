"""
JPTrades - Signal Logger
Logs signals to the JPTrades database (alphafx.db).
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_FILE = str(Path(__file__).resolve().parent / "alphafx.db")


def init_db():
    """Ensure the signals table exists."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            nifty REAL,
            signal TEXT,
            confidence REAL,
            ce_price REAL,
            pe_price REAL,
            outcome TEXT,
            future_price REAL
        )
    """)
    conn.commit()
    conn.close()


def log_signal(nifty, signal, confidence, ce_price=0.0, pe_price=0.0):
    """Save a new signal to the database."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO signals (timestamp, nifty, signal, confidence, ce_price, pe_price, outcome, future_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        float(nifty),
        str(signal),
        float(confidence),
        float(ce_price),
        float(pe_price),
        None,
        None
    ))
    conn.commit()
    conn.close()


def get_signals(limit=50):
    """Get recent signals from database."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, nifty, signal, confidence, ce_price, pe_price, outcome, future_price
        FROM signals ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_signal_history(limit=10):
    """Get formatted signal history for dashboard with option trade details + open trades."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get closed trades (most recent first)
    cursor.execute("""
        SELECT t.opened_at, t.direction, t.strike, t.entry_premium, t.exit_premium,
               t.target_premium, t.sl_premium, t.exit_reason, t.pnl_percent, t.status,
               s.confidence
        FROM trades t
        LEFT JOIN signals s ON s.timestamp LIKE substr(t.opened_at, 1, 16) || '%'
        WHERE t.status = 'CLOSED'
        ORDER BY t.id DESC LIMIT ?
    """, (limit,))
    closed = cursor.fetchall()

    # Get open trades
    cursor.execute("""
        SELECT t.opened_at, t.direction, t.strike, t.entry_premium, t.target_premium,
               t.sl_premium, t.mfe, t.candles_elapsed, t.status,
               s.confidence
        FROM trades t
        LEFT JOIN signals s ON s.timestamp LIKE substr(t.opened_at, 1, 16) || '%'
        WHERE t.status = 'OPEN'
        ORDER BY t.id DESC
    """)
    open_trades = cursor.fetchall()

    conn.close()

    history = []

    # Add open trades first
    for row in open_trades:
        opened, direction, strike, entry, target, sl, mfe, candles, status, conf = row
        contract = f"{int(strike)}{direction}"
        history.append({
            "timestamp": opened[:16].replace("T", " ") if opened else "",
            "signal": contract,
            "confidence": conf or 0.0,
            "entry_price": entry or 0.0,
            "target_price": target or 0.0,
            "exit_price": 0.0,
            "outcome": "OPEN",
            "pnl_pct": 0.0,
        })

    # Add closed trades
    for row in closed:
        opened, direction, strike, entry, exit_p, target, sl, reason, pnl, status, conf = row
        contract = f"{int(strike)}{direction}"
        history.append({
            "timestamp": opened[:16].replace("T", " ") if opened else "",
            "signal": contract,
            "confidence": conf or 0.0,
            "entry_price": entry or 0.0,
            "target_price": target or 0.0,
            "exit_price": exit_p or 0.0,
            "outcome": reason or "CLOSED",
            "pnl_pct": pnl or 0.0,
        })

    return history[:limit + len(open_trades)]


def get_performance_stats():
    """Calculate wins, losses, streaks, and distribution from database."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Total counts
    cursor.execute("SELECT COUNT(*) FROM signals WHERE outcome IS NOT NULL")
    total_resolved = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM signals WHERE outcome = 'WIN'")
    wins = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM signals WHERE outcome = 'LOSS'")
    losses = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM signals")
    total_all = cursor.fetchone()[0] or 0

    # Confidence stats
    cursor.execute("SELECT AVG(confidence), MAX(confidence), MIN(confidence) FROM signals")
    conf_row = cursor.fetchone()
    avg_conf = conf_row[0] or 0.0
    best_conf = conf_row[1] or 0.0
    worst_conf = conf_row[2] or 0.0

    # Signal distribution
    cursor.execute("SELECT COUNT(*) FROM signals WHERE signal LIKE '%BULLISH%'")
    bullish_count = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM signals WHERE signal LIKE '%BEARISH%'")
    bearish_count = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM signals WHERE signal = 'NEUTRAL'")
    neutral_count = cursor.fetchone()[0] or 0

    # Current streak
    cursor.execute("SELECT outcome FROM signals WHERE outcome IS NOT NULL ORDER BY id DESC LIMIT 50")
    outcomes = [r[0] for r in cursor.fetchall()]

    current_streak = 0
    if outcomes:
        first = outcomes[0]
        for o in outcomes:
            if o == first:
                current_streak += 1
            else:
                break
        if first == "LOSS":
            current_streak = -current_streak

    # Longest streaks
    longest_win = 0
    longest_loss = 0
    cursor.execute("SELECT outcome FROM signals WHERE outcome IS NOT NULL ORDER BY id ASC")
    all_outcomes = [r[0] for r in cursor.fetchall()]

    streak = 0
    prev = None
    for o in all_outcomes:
        if o == prev:
            streak += 1
        else:
            streak = 1
        prev = o
        if o == "WIN" and streak > longest_win:
            longest_win = streak
        elif o == "LOSS" and streak > longest_loss:
            longest_loss = streak

    # Confidence trend (last 30)
    cursor.execute("SELECT confidence FROM signals ORDER BY id DESC LIMIT 30")
    conf_trend = [r[0] for r in cursor.fetchall()][::-1]

    # Performance curve (cumulative points)
    cursor.execute("""
        SELECT nifty, future_price, signal, outcome
        FROM signals WHERE outcome IS NOT NULL ORDER BY id ASC LIMIT 30
    """)
    perf_rows = cursor.fetchall()
    perf_curve = [0]
    cumulative = 0
    for row in perf_rows:
        entry, future, sig, outcome = row
        if entry and future:
            points = abs(future - entry)
            cumulative += points if outcome == "WIN" else -points
        perf_curve.append(round(cumulative, 1))

    # Win rate trend (rolling)
    cursor.execute("SELECT outcome FROM signals WHERE outcome IS NOT NULL ORDER BY id DESC LIMIT 300")
    all_resolved = [r[0] for r in cursor.fetchall()][::-1]

    win_rate_trend = []
    window = max(5, len(all_resolved) // 30) if all_resolved else 5
    for i in range(min(30, len(all_resolved))):
        start_idx = max(0, i - window + 1)
        chunk = all_resolved[start_idx:i + 1]
        if chunk:
            wr = sum(1 for x in chunk if x == "WIN") / len(chunk) * 100
            win_rate_trend.append(round(wr, 1))
        else:
            win_rate_trend.append(50.0)

    # Pad to at least some values
    while len(win_rate_trend) < 5:
        win_rate_trend.insert(0, 50.0)

    conn.close()

    win_rate = (wins / total_resolved * 100) if total_resolved > 0 else 0.0

    return {
        "wins": wins,
        "losses": losses,
        "total_signals": total_all,
        "win_rate": round(win_rate, 2),
        "avg_confidence": round(avg_conf, 1),
        "best_confidence": round(best_conf, 1),
        "worst_confidence": round(worst_conf, 1),
        "current_streak": current_streak,
        "longest_win_streak": longest_win,
        "longest_loss_streak": longest_loss,
        "bullish_signals": bullish_count,
        "bearish_signals": bearish_count,
        "no_trade_signals": neutral_count,
        "confidence_trend": conf_trend,
        "performance_curve": perf_curve,
        "win_rate_trend": win_rate_trend,
    }


def update_pending_signals(current_nifty):
    """Resolve pending signals by comparing with current price."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id, nifty, signal FROM signals WHERE outcome IS NULL")
    rows = cursor.fetchall()

    for row in rows:
        signal_id, entry_price, signal_text = row
        if not entry_price:
            continue

        if "BULLISH" in (signal_text or ""):
            outcome = "WIN" if current_nifty > entry_price else "LOSS"
        elif "BEARISH" in (signal_text or ""):
            outcome = "WIN" if current_nifty < entry_price else "LOSS"
        else:
            continue  # Skip NEUTRAL signals

        cursor.execute(
            "UPDATE signals SET outcome = ?, future_price = ? WHERE id = ?",
            (outcome, current_nifty, signal_id)
        )

    conn.commit()
    conn.close()
    return len(rows)


if __name__ == "__main__":
    init_db()
    print("Database ready.")
    print(f"Location: {DB_FILE}")

    signals = get_signals(5)
    if signals:
        print(f"\nLast {len(signals)} signals:")
        for s in signals:
            print(f"  {s[1][:19]} | {s[3]:15s} | {s[4]:.1f}% | {s[7] or 'PENDING'}")
    else:
        print("No signals recorded yet.")
