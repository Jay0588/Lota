"""
JPTrades - Trade Lifecycle Engine
Tracks real option premium P&L from entry to exit.
Monitors open trades for SL/Target hits every prediction cycle.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

from config import DEFAULT_STOP_LOSS_PERCENT, DEFAULT_TARGET_PERCENT

logger = logging.getLogger(__name__)

DB_FILE = str(Path(__file__).resolve().parent / "alphafx.db")

# Maximum candles (5-min each) before a trade is force-closed
TIMEOUT_CANDLES = 6  # 6 × 5 min = 30 minutes


def init_trades_table():
    """Create the trades table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            direction TEXT NOT NULL,
            strike INTEGER NOT NULL,
            entry_premium REAL NOT NULL,
            exit_premium REAL,
            sl_premium REAL NOT NULL,
            target_premium REAL NOT NULL,
            mfe REAL NOT NULL,
            mae REAL NOT NULL,
            exit_reason TEXT,
            pnl_rupees REAL,
            pnl_percent REAL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            candles_elapsed INTEGER DEFAULT 0,
            timeout_minutes INTEGER DEFAULT 30
        )
    """)
    # Add timeout_minutes column if table already exists without it
    try:
        cursor.execute("ALTER TABLE trades ADD COLUMN timeout_minutes INTEGER DEFAULT 30")
    except Exception:
        pass  # Column already exists
    conn.commit()
    conn.close()


def open_trade(signal_id: int, direction: str, strike: int,
               entry_premium: float, confidence: float,
               timeout_minutes: int = 30):
    """
    Open a new trade when a signal fires.

    Args:
        signal_id: ID from the signals table (or 0 if not linked)
        direction: "CE" for bullish, "PE" for bearish
        strike: ATM strike price (e.g., 23200)
        entry_premium: Current option premium at entry (e.g., 185.60)
        confidence: Model confidence (used to adjust SL/target)
        timeout_minutes: How long before force-closing (15, 30, or 60)
    """
    init_trades_table()

    if entry_premium <= 0:
        logger.warning(f"Cannot open trade: entry_premium={entry_premium}")
        return None

    # Realistic SL/target scaled to timeout duration
    if timeout_minutes <= 15:
        # Short trade — tight SL, small target
        sl_pct = 0.04
        target_pct = 0.05
    elif timeout_minutes <= 30:
        # Medium trade
        if confidence >= 75:
            sl_pct = 0.06
            target_pct = 0.08
        elif confidence >= 65:
            sl_pct = 0.06
            target_pct = 0.07
        else:
            sl_pct = 0.05
            target_pct = 0.06
    else:
        # Long trade (60 min) — more room
        if confidence >= 75:
            sl_pct = 0.08
            target_pct = 0.12
        elif confidence >= 65:
            sl_pct = 0.07
            target_pct = 0.10
        else:
            sl_pct = 0.06
            target_pct = 0.08

    sl_premium = round(entry_premium * (1.0 - sl_pct), 2)
    target_premium = round(entry_premium * (1.0 + target_pct), 2)
    timeout_candles = timeout_minutes // 5

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades (
            signal_id, opened_at, direction, strike,
            entry_premium, sl_premium, target_premium,
            mfe, mae, status, candles_elapsed, timeout_minutes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 0, ?)
    """, (
        signal_id,
        datetime.now().isoformat(),
        direction,
        strike,
        entry_premium,
        sl_premium,
        target_premium,
        entry_premium,
        entry_premium,
        timeout_minutes,
    ))
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(
        f"Trade opened: #{trade_id} {direction} {strike} @ Rs.{entry_premium:.2f} "
        f"| SL: Rs.{sl_premium:.2f} | TGT: Rs.{target_premium:.2f} | Timeout: {timeout_minutes}min"
    )
    return trade_id


def monitor_open_trades(current_ce_price: float, current_pe_price: float,
                       current_strike: int = 0):
    """
    Check all open trades against current option prices.
    Updates MFE/MAE and closes trades that hit SL, target, or timeout.

    IMPORTANT: Only updates trades where the strike matches the current ATM strike.
    If the ATM has shifted away from a trade's strike, that trade is force-closed
    at timeout (since we can no longer reliably track its premium without
    fetching the specific contract price).

    Args:
        current_ce_price: Current ATM CE premium
        current_pe_price: Current ATM PE premium
        current_strike: Current ATM strike (to validate against open trades)

    Returns:
        dict with counts of actions taken
    """
    init_trades_table()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, direction, strike, entry_premium, sl_premium, target_premium,
               mfe, mae, candles_elapsed, timeout_minutes
        FROM trades WHERE status = 'OPEN'
    """)
    open_trades = cursor.fetchall()

    closed_count = 0
    updated_count = 0

    for trade in open_trades:
        trade_id, direction, strike, entry_premium, sl_premium, target_premium, \
            mfe, mae, candles_elapsed, timeout_mins = trade

        # Each trade has its own timeout
        trade_timeout_candles = (timeout_mins or 30) // 5

        new_candles = candles_elapsed + 1

        # If strike has shifted, close after 3 candles (15 min) — can't track accurately
        if current_strike > 0 and strike != current_strike:
            if new_candles >= 3:
                exit_reason = "TIMEOUT"
                estimated_exit = mfe if mfe > entry_premium else entry_premium
                pnl_rupees = round(estimated_exit - entry_premium, 2)
                pnl_percent = round(((estimated_exit - entry_premium) / entry_premium) * 100, 2)

                cursor.execute("""
                    UPDATE trades SET
                        closed_at = ?, exit_premium = ?, mfe = ?, mae = ?,
                        exit_reason = ?, pnl_rupees = ?, pnl_percent = ?,
                        status = 'CLOSED', candles_elapsed = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), estimated_exit, mfe, mae,
                      exit_reason, pnl_rupees, pnl_percent, new_candles, trade_id))
                closed_count += 1
                logger.info(
                    f"Trade #{trade_id} CLOSED [STRIKE_SHIFT]: "
                    f"{direction} {strike} (ATM now {current_strike}) | P&L: {pnl_percent:+.2f}%"
                )
            else:
                # Just increment candle count, can't update MFE/MAE
                cursor.execute("UPDATE trades SET candles_elapsed = ? WHERE id = ?",
                               (new_candles, trade_id))
                updated_count += 1
            continue

        # Get current price for this trade's direction
        current_price = current_ce_price if direction == "CE" else current_pe_price

        if current_price <= 0:
            # Can't get valid price, just increment candle count
            cursor.execute("UPDATE trades SET candles_elapsed = ? WHERE id = ?",
                           (new_candles, trade_id))
            updated_count += 1
            continue

        # Update MFE and MAE
        new_mfe = max(mfe, current_price)
        new_mae = min(mae, current_price)

        # Check exit conditions
        exit_reason = None

        if current_price <= sl_premium:
            exit_reason = "SL_HIT"
        elif current_price >= target_premium:
            exit_reason = "TARGET_HIT"
        elif new_candles >= trade_timeout_candles:
            exit_reason = "TIMEOUT"

        if exit_reason:
            # Close the trade
            pnl_rupees = round(current_price - entry_premium, 2)
            pnl_percent = round(((current_price - entry_premium) / entry_premium) * 100, 2)

            cursor.execute("""
                UPDATE trades SET
                    closed_at = ?, exit_premium = ?, mfe = ?, mae = ?,
                    exit_reason = ?, pnl_rupees = ?, pnl_percent = ?,
                    status = 'CLOSED', candles_elapsed = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), current_price, new_mfe, new_mae,
                  exit_reason, pnl_rupees, pnl_percent, new_candles, trade_id))
            closed_count += 1

            logger.info(
                f"Trade #{trade_id} CLOSED [{exit_reason}]: "
                f"{direction} entry Rs.{entry_premium:.2f} -> exit Rs.{current_price:.2f} "
                f"| P&L: {pnl_percent:+.2f}%"
            )
        else:
            # Update MFE/MAE and candle count
            cursor.execute("""
                UPDATE trades SET mfe = ?, mae = ?, candles_elapsed = ?
                WHERE id = ?
            """, (new_mfe, new_mae, new_candles, trade_id))
            updated_count += 1

    conn.commit()
    conn.close()

    return {"closed": closed_count, "updated": updated_count, "total_open": len(open_trades)}


def get_open_trades():
    """Get all currently open trades."""
    init_trades_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, direction, strike, entry_premium, sl_premium, target_premium,
               mfe, mae, candles_elapsed, opened_at, timeout_minutes
        FROM trades WHERE status = 'OPEN'
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    trades = []
    for row in rows:
        trades.append({
            "id": row[0],
            "direction": row[1],
            "strike": row[2],
            "entry_premium": row[3],
            "sl_premium": row[4],
            "target_premium": row[5],
            "mfe": row[6],
            "mae": row[7],
            "candles_elapsed": row[8],
            "opened_at": row[9][:19].replace("T", " ") if row[9] else "",
            "timeout_minutes": row[10] or 30,
        })
    return trades


def get_trade_metrics():
    """
    Compute real trade performance metrics based on actual option premium P&L.

    Returns dict with:
        total_trades, closed_trades, open_trades,
        real_win_rate, expectancy, profit_factor,
        avg_reward_risk, avg_option_return,
        gross_profit, gross_loss,
        avg_win_pct, avg_loss_pct,
        mfe_efficiency, mae_risk,
        sl_hits, target_hits, timeouts,
        best_trade_pct, worst_trade_pct,
        recent_trades (last 10 closed trades)
    """
    init_trades_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Counts
    cursor.execute("SELECT COUNT(*) FROM trades")
    total_trades = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'CLOSED'")
    closed_trades = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'OPEN'")
    open_trades_count = cursor.fetchone()[0] or 0

    if closed_trades == 0:
        conn.close()
        return {
            "total_trades": total_trades,
            "closed_trades": 0,
            "open_trades": open_trades_count,
            "real_win_rate": 0.0,
            "expectancy": 0.0,
            "profit_factor": 0.0,
            "avg_reward_risk": 0.0,
            "avg_option_return": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "avg_win_pct": 0.0,
            "avg_loss_pct": 0.0,
            "mfe_efficiency": 0.0,
            "mae_risk": 0.0,
            "sl_hits": 0,
            "target_hits": 0,
            "timeouts": 0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "recent_trades": [],
        }

    # Win/loss by actual P&L (not just exit reason)
    cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'CLOSED' AND pnl_rupees > 0")
    wins = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'CLOSED' AND pnl_rupees <= 0")
    losses = cursor.fetchone()[0] or 0

    real_win_rate = round((wins / closed_trades) * 100, 2) if closed_trades > 0 else 0.0

    # Exit reason distribution
    cursor.execute("SELECT COUNT(*) FROM trades WHERE exit_reason = 'SL_HIT'")
    sl_hits = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM trades WHERE exit_reason = 'TARGET_HIT'")
    target_hits = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM trades WHERE exit_reason = 'TIMEOUT'")
    timeouts = cursor.fetchone()[0] or 0

    # Gross profit and loss
    cursor.execute("SELECT SUM(pnl_rupees) FROM trades WHERE status = 'CLOSED' AND pnl_rupees > 0")
    gross_profit = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(ABS(pnl_rupees)) FROM trades WHERE status = 'CLOSED' AND pnl_rupees <= 0")
    gross_loss = cursor.fetchone()[0] or 0.0

    # Profit factor
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (
        999.0 if gross_profit > 0 else 0.0
    )

    # Average win % and loss %
    cursor.execute("SELECT AVG(pnl_percent) FROM trades WHERE status = 'CLOSED' AND pnl_rupees > 0")
    avg_win_pct = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT AVG(ABS(pnl_percent)) FROM trades WHERE status = 'CLOSED' AND pnl_rupees <= 0")
    avg_loss_pct = cursor.fetchone()[0] or 0.0

    # Average reward:risk
    avg_reward_risk = round(avg_win_pct / avg_loss_pct, 2) if avg_loss_pct > 0 else 0.0

    # Expectancy: (win_rate × avg_win) - (loss_rate × avg_loss)
    win_rate_decimal = wins / closed_trades if closed_trades > 0 else 0
    loss_rate_decimal = losses / closed_trades if closed_trades > 0 else 0
    expectancy = round(
        (win_rate_decimal * avg_win_pct) - (loss_rate_decimal * avg_loss_pct), 2
    )

    # Average option return (across all trades)
    cursor.execute("SELECT AVG(pnl_percent) FROM trades WHERE status = 'CLOSED'")
    avg_option_return = round(cursor.fetchone()[0] or 0.0, 2)

    # MFE efficiency: how much of available profit do we capture?
    # For winning trades: pnl / (mfe - entry)
    cursor.execute("""
        SELECT AVG(
            CASE WHEN (mfe - entry_premium) > 0
            THEN pnl_rupees / (mfe - entry_premium)
            ELSE 0 END
        )
        FROM trades WHERE status = 'CLOSED' AND pnl_rupees > 0
    """)
    mfe_efficiency = round((cursor.fetchone()[0] or 0.0) * 100, 1)

    # MAE risk: average drawdown as % of entry
    cursor.execute("""
        SELECT AVG((entry_premium - mae) / entry_premium * 100)
        FROM trades WHERE status = 'CLOSED'
    """)
    mae_risk = round(cursor.fetchone()[0] or 0.0, 2)

    # Best and worst trades
    cursor.execute("SELECT MAX(pnl_percent) FROM trades WHERE status = 'CLOSED'")
    best_trade_pct = round(cursor.fetchone()[0] or 0.0, 2)

    cursor.execute("SELECT MIN(pnl_percent) FROM trades WHERE status = 'CLOSED'")
    worst_trade_pct = round(cursor.fetchone()[0] or 0.0, 2)

    # Recent closed trades (last 10)
    cursor.execute("""
        SELECT opened_at, closed_at, direction, strike, entry_premium,
               exit_premium, pnl_percent, exit_reason
        FROM trades WHERE status = 'CLOSED'
        ORDER BY id DESC LIMIT 10
    """)
    recent_rows = cursor.fetchall()

    recent_trades = []
    for row in recent_rows:
        recent_trades.append({
            "opened_at": row[0][:19].replace("T", " ") if row[0] else "",
            "closed_at": row[1][:19].replace("T", " ") if row[1] else "",
            "direction": row[2],
            "strike": row[3],
            "entry": row[4],
            "exit": row[5],
            "pnl_pct": round(row[6], 2) if row[6] else 0,
            "exit_reason": row[7] or ""
        })

    conn.close()

    return {
        "total_trades": total_trades,
        "closed_trades": closed_trades,
        "open_trades": open_trades_count,
        "real_win_rate": real_win_rate,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "avg_reward_risk": avg_reward_risk,
        "avg_option_return": avg_option_return,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "avg_win_pct": round(avg_win_pct, 2),
        "avg_loss_pct": round(avg_loss_pct, 2),
        "mfe_efficiency": mfe_efficiency,
        "mae_risk": mae_risk,
        "sl_hits": sl_hits,
        "target_hits": target_hits,
        "timeouts": timeouts,
        "best_trade_pct": best_trade_pct,
        "worst_trade_pct": worst_trade_pct,
        "recent_trades": recent_trades,
    }


def get_timeout_comparison():
    """
    Compare performance across different timeout durations.
    Returns dict showing which timeout works best.
    """
    init_trades_table()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    results = {}
    for timeout in [15, 30, 60]:
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END),
                   AVG(pnl_percent),
                   SUM(CASE WHEN exit_reason = 'TARGET_HIT' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN exit_reason = 'SL_HIT' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN exit_reason = 'TIMEOUT' THEN 1 ELSE 0 END)
            FROM trades
            WHERE status = 'CLOSED' AND timeout_minutes = ?
        """, (timeout,))
        row = cursor.fetchone()
        total = row[0] or 0
        wins = row[1] or 0
        avg_pnl = row[2] or 0
        targets = row[3] or 0
        sl_hits = row[4] or 0
        timeouts = row[5] or 0

        results[f"{timeout}min"] = {
            "total": total,
            "wins": wins,
            "win_rate": round((wins / total * 100), 1) if total > 0 else 0,
            "avg_pnl": round(avg_pnl, 2),
            "target_hits": targets,
            "sl_hits": sl_hits,
            "timeouts": timeouts,
        }

    conn.close()

    # Determine best timeout
    best_timeout = "30min"
    best_pnl = -999
    for key, data in results.items():
        if data["total"] >= 3 and data["avg_pnl"] > best_pnl:
            best_pnl = data["avg_pnl"]
            best_timeout = key

    return {"comparison": results, "best_timeout": best_timeout}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_trades_table()
    print("Trades table ready.")

    metrics = get_trade_metrics()
    print(f"\n=== Trade Metrics ===")
    for k, v in metrics.items():
        if k != "recent_trades":
            print(f"  {k}: {v}")

    print(f"\n  Recent trades: {len(metrics['recent_trades'])}")
    for t in metrics["recent_trades"]:
        print(f"    {t['direction']} {t['strike']} | ₹{t['entry']:.2f} → ₹{t['exit']:.2f} | {t['pnl_pct']:+.1f}% [{t['exit_reason']}]")
