"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          JPTrades Trading Platform                            ║
║                     Premium Quantitative Trading Dashboard                  ║
║                                                                             ║
║  Live ML predictions connected to NIFTY/BANKNIFTY/VIX via yfinance          ║
║  Options data via Angel One SmartAPI                                        ║
║  Background prediction loop refreshes every 5 minutes during market hours   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import threading
import time
import traceback
import logging
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, jsonify, render_template

# ═══════════════════════════════════════════════════════════════════════════════
# SETUP LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs" / datetime.now().strftime("%Y-%m-%d")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS FROM PROJECT MODULES
# ═══════════════════════════════════════════════════════════════════════════════

from config import MODEL_FILE, DEFAULT_STOP_LOSS_PERCENT, DEFAULT_TARGET_PERCENT
from market_data import MarketData
from signal_engine import classify_signal
from option_features import get_option_features, get_multi_strike_prices
from signal_logger import (
    log_signal, get_signal_history, get_performance_stats, update_pending_signals
)
from trade_engine import (
    open_trade, monitor_open_trades, get_trade_metrics, get_open_trades,
    init_trades_table, get_timeout_comparison
)
from model_health import get_model_health
from premarket_brief import generate_premarket_brief, get_latest_brief

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE LISTS (must match training)
# ═══════════════════════════════════════════════════════════════════════════════

# Optimized feature set from quantitative audit (11 features)
FEATURES_WITH_OPTIONS = [
    "RETURN_6", "EMA_DIFF", "MACD_SIGNAL", "VIX_RETURN_3", "MINUTE",
    "EMA50", "BB_UPPER", "BANK_RETURN_1", "EMA20", "RETURN_3", "MACD",
    "ATM_STRIKE", "CE_LTP", "PE_LTP", "CE_PE_RATIO",
]

FEATURES_WITHOUT_OPTIONS = [
    "RETURN_6", "EMA_DIFF", "MACD_SIGNAL", "VIX_RETURN_3", "MINUTE",
    "EMA50", "BB_UPPER", "BANK_RETURN_1", "EMA20", "RETURN_3", "MACD",
]

# ═══════════════════════════════════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE DATA STATE (thread-safe)
# ═══════════════════════════════════════════════════════════════════════════════

data_lock = threading.Lock()

live_state = {
    "signal": "LOADING",
    "confidence": 0.0,
    "signal_strength": "WEAK",
    "nifty": 0.0,
    "nifty_change": 0.0,
    "nifty_change_pct": 0.0,
    "banknifty": 0.0,
    "banknifty_change": 0.0,
    "banknifty_change_pct": 0.0,
    "vix": 0.0,
    "vix_change": 0.0,
    "vix_change_pct": 0.0,
    "atm_strike": 0,
    "ce_price": 0.0,
    "pe_price": 0.0,
    "ce_pe_ratio": 1.0,
    "options_sentiment": "NEUTRAL",
    "wins": 0,
    "losses": 0,
    "total_signals": 0,
    "win_rate": 0.0,
    "avg_confidence": 0.0,
    "best_confidence": 0.0,
    "worst_confidence": 0.0,
    "current_streak": 0,
    "longest_win_streak": 0,
    "longest_loss_streak": 0,
    "signal_history": [],
    "win_rate_trend": [],
    "confidence_trend": [],
    "performance_curve": [],
    "bullish_signals": 0,
    "bearish_signals": 0,
    "no_trade_signals": 0,
    "last_update": "Starting...",
    "market_status": "CLOSED",
    "error": None,
    "trade_metrics": {},
    "trade_reco": None,
}


# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_prediction():
    """Run a full prediction cycle: fetch data, predict, update state."""
    global live_state

    try:
        logger.info("Starting prediction cycle...")

        # 1. Fetch market data
        md = MarketData()
        data = md.get_processed_data()
        latest = data.iloc[-1]

        nifty_price = float(latest["Close"])
        bank_price = float(latest["BANK_CLOSE"])
        vix_price = float(latest["VIX_CLOSE"])

        # Calculate changes
        if len(data) >= 2:
            prev = data.iloc[-2]
            nifty_change = nifty_price - float(prev["Close"])
            nifty_change_pct = (nifty_change / float(prev["Close"])) * 100
            bank_change = bank_price - float(prev["BANK_CLOSE"])
            bank_change_pct = (bank_change / float(prev["BANK_CLOSE"])) * 100 if float(prev["BANK_CLOSE"]) != 0 else 0
            vix_change = vix_price - float(prev["VIX_CLOSE"])
            vix_change_pct = (vix_change / float(prev["VIX_CLOSE"])) * 100 if float(prev["VIX_CLOSE"]) != 0 else 0
        else:
            nifty_change = nifty_change_pct = 0
            bank_change = bank_change_pct = 0
            vix_change = vix_change_pct = 0

        # 2. Fetch option features (optional - gracefully handles failure)
        option_data = get_option_features()
        has_options = option_data is not None

        # 3. Build feature vector for prediction
        latest_dict = latest.to_dict()
        if has_options:
            latest_dict["ATM_STRIKE"] = option_data["ATM_STRIKE"]
            latest_dict["CE_LTP"] = option_data["CE_LTP"]
            latest_dict["PE_LTP"] = option_data["PE_LTP"]
            latest_dict["CE_PE_RATIO"] = option_data["CE_PE_RATIO"]

        # 4. Load model and predict
        if not MODEL_FILE.exists():
            logger.error(f"Model file not found: {MODEL_FILE}")
            with data_lock:
                live_state["error"] = "Model not trained yet. Run: python train_model.py"
                live_state["signal"] = "NO TRADE"
                live_state["confidence"] = 0.0
                live_state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return

        model = joblib.load(MODEL_FILE)

        # Determine which features the model expects
        model_n_features = model.n_features_in_ if hasattr(model, 'n_features_in_') else None

        if model_n_features == len(FEATURES_WITH_OPTIONS) and has_options:
            features = FEATURES_WITH_OPTIONS
        else:
            # Default: use core 11 features (model was trained on these)
            features = FEATURES_WITHOUT_OPTIONS

        X = pd.DataFrame([{f: latest_dict.get(f, 0) for f in features}], columns=features)
        probabilities = model.predict_proba(X)[0]
        up_probability = float(probabilities[1]) if len(probabilities) > 1 else float(probabilities[0])

        # 5. Classify signal
        signal_result = classify_signal(up_probability)
        signal_text = signal_result["signal"]
        confidence_val = signal_result["confidence"]

        # Determine strength
        if confidence_val >= 75:
            strength = "STRONG"
        elif confidence_val >= 65:
            strength = "MODERATE"
        else:
            strength = "WEAK"

        # Normalize signal for display
        if "BULLISH" in signal_text:
            display_signal = "BULLISH"
        elif "BEARISH" in signal_text:
            display_signal = "BEARISH"
        else:
            display_signal = "NO TRADE"

        # 6. Update pending signals and save new one
        update_pending_signals(nifty_price)
        trade_reco = None  # Will be set if a trade fires

        # Only generate trades during market hours (Mon-Fri, 9:15-15:30)
        now = datetime.now()
        is_market_open = (
            now.weekday() < 5 and
            ((now.hour == 9 and now.minute >= 15) or (10 <= now.hour <= 14) or (now.hour == 15 and now.minute <= 30))
        )

        if display_signal != "NO TRADE" and is_market_open:
            log_signal(
                nifty_price, signal_text, confidence_val,
                option_data["CE_LTP"] if has_options else 0.0,
                option_data["PE_LTP"] if has_options else 0.0
            )

            # Open a real trade tracking the option premium
            # Only open if no existing open trade on the same strike+direction
            if has_options:
                trade_direction = "CE" if display_signal == "BULLISH" else "PE"
                trade_entry_premium = option_data["CE_LTP"] if trade_direction == "CE" else option_data["PE_LTP"]
                trade_strike = option_data["ATM_STRIKE"]

                # Check if we already have an open trade on this contract
                existing_open = [t for t in get_open_trades()
                                 if t["strike"] == trade_strike and t["direction"] == trade_direction]

                if trade_entry_premium > 0 and not existing_open:
                    # Open 3 trades with different timeouts to find optimal holding period
                    for timeout in [15, 30, 60]:
                        open_trade(
                            signal_id=0,
                            direction=trade_direction,
                            strike=trade_strike,
                            entry_premium=trade_entry_premium,
                            confidence=confidence_val,
                            timeout_minutes=timeout
                        )

                    # Build 3-tier trade recommendations (ITM / ATM / OTM)
                    multi_strikes = get_multi_strike_prices(trade_direction, trade_strike)

                    # The multi_strike function now returns full trade setups
                    trade_reco = {
                        "direction": trade_direction,
                        "strike": trade_strike,
                        "options": multi_strikes,
                    }

                    # Fallback if multi-strike API failed
                    if not multi_strikes and trade_entry_premium > 0:
                        sl_p = round(trade_entry_premium * 0.90, 2)
                        tgt1 = round(trade_entry_premium * 1.15, 2)
                        tgt2 = round(trade_entry_premium * 1.25, 2)
                        capital = round(trade_entry_premium * 25, 2)
                        trade_reco["options"] = [{
                            "strike": trade_strike,
                            "price": trade_entry_premium,
                            "label": "ATM",
                            "risk_level": "MEDIUM RISK",
                            "tier": "medium",
                            "contract": f"{trade_strike}{trade_direction}",
                            "capital_required": capital,
                            "budget": "2k-5k" if capital <= 5000 else "5k-10k" if capital <= 10000 else "10k+",
                            "sl_price": sl_p,
                            "target1": tgt1,
                            "target2": tgt2,
                            "entry_low": round(trade_entry_premium * 0.98, 2),
                            "entry_high": round(trade_entry_premium * 1.02, 2),
                            "risk_amount": round((trade_entry_premium - sl_p) * 25, 2),
                            "reward_amount": round((tgt1 - trade_entry_premium) * 25, 2),
                            "rr_ratio": round((tgt1 - trade_entry_premium) / (trade_entry_premium - sl_p), 2) if (trade_entry_premium - sl_p) > 0 else 0,
                            "lot_size": 25,
                        }]

        # 6b. Monitor open trades for SL/target hits
        if has_options:
            monitor_result = monitor_open_trades(
                current_ce_price=option_data["CE_LTP"],
                current_pe_price=option_data["PE_LTP"],
                current_strike=option_data["ATM_STRIKE"]
            )
            logger.info(f"Trade monitor: {monitor_result}")
        else:
            monitor_open_trades(0, 0, 0)  # Will skip trades with 0 price

        # 7. Get performance stats from DB
        stats = get_performance_stats()
        history = get_signal_history(10)
        trade_metrics = get_trade_metrics()

        # Options sentiment
        if has_options:
            ratio = option_data["CE_PE_RATIO"]
            opt_sentiment = "BULLISH" if ratio > 1.1 else ("BEARISH" if ratio < 0.9 else "NEUTRAL")
        else:
            opt_sentiment = "NEUTRAL"

        # 8. Update live state
        with data_lock:
            live_state.update({
                "signal": display_signal if is_market_open else "MARKET CLOSED",
                "confidence": confidence_val if is_market_open else 0.0,
                "signal_strength": strength if is_market_open else "WEAK",
                "nifty": round(nifty_price, 2),
                "nifty_change": round(nifty_change, 2),
                "nifty_change_pct": round(nifty_change_pct, 2),
                "banknifty": round(bank_price, 2),
                "banknifty_change": round(bank_change, 2),
                "banknifty_change_pct": round(bank_change_pct, 2),
                "vix": round(vix_price, 2),
                "vix_change": round(vix_change, 2),
                "vix_change_pct": round(vix_change_pct, 2),
                "atm_strike": option_data["ATM_STRIKE"] if has_options else int(round(nifty_price / 50) * 50),
                "ce_price": option_data["CE_LTP"] if has_options else 0.0,
                "pe_price": option_data["PE_LTP"] if has_options else 0.0,
                "ce_pe_ratio": round(option_data["CE_PE_RATIO"], 2) if has_options else 1.0,
                "options_sentiment": opt_sentiment,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "total_signals": stats["total_signals"],
                "win_rate": stats["win_rate"],
                "avg_confidence": stats["avg_confidence"],
                "best_confidence": stats["best_confidence"],
                "worst_confidence": stats["worst_confidence"],
                "current_streak": stats["current_streak"],
                "longest_win_streak": stats["longest_win_streak"],
                "longest_loss_streak": stats["longest_loss_streak"],
                "signal_history": history,
                "win_rate_trend": stats["win_rate_trend"],
                "confidence_trend": stats["confidence_trend"],
                "performance_curve": stats["performance_curve"],
                "bullish_signals": stats["bullish_signals"],
                "bearish_signals": stats["bearish_signals"],
                "no_trade_signals": stats["no_trade_signals"],
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": "OPEN" if is_market_open else "CLOSED",
                "error": None,
                "trade_metrics": trade_metrics,
                "trade_reco": trade_reco if trade_reco else live_state.get("trade_reco"),
            })

        logger.info(f"Prediction: {display_signal} ({confidence_val}%) | NIFTY: {nifty_price:.2f}")

    except Exception as e:
        logger.error(f"Prediction cycle failed: {e}")
        logger.error(traceback.format_exc())
        with data_lock:
            live_state["error"] = str(e)
            live_state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND PREDICTION LOOP
# ═══════════════════════════════════════════════════════════════════════════════

REFRESH_INTERVAL = 300  # 5 minutes


def prediction_loop():
    """Background thread: runs predictions every 5 minutes during market hours."""
    logger.info("Background prediction loop started")

    # Run immediately on startup
    run_prediction()

    last_retrain_date = None
    last_brief_date = None

    while True:
        time.sleep(REFRESH_INTERVAL)

        now = datetime.now()
        hour = now.hour
        minute = now.minute
        weekday = now.weekday()  # 0=Monday, 6=Sunday

        # Run during market hours (Mon-Fri, 9:15-15:30 IST)
        if weekday < 5 and ((hour == 9 and minute >= 15) or (10 <= hour <= 14) or (hour == 15 and minute <= 30)):
            run_prediction()
        else:
            with data_lock:
                live_state["market_status"] = "CLOSED"

            # Pre-market brief at 08:45 AM
            if weekday < 5 and hour == 8 and 45 <= minute <= 50:
                today = now.date()
                if last_brief_date != today:
                    last_brief_date = today
                    logger.info("Generating pre-market brief...")
                    try:
                        with data_lock:
                            vix = live_state.get("vix", 15.0)
                        generate_premarket_brief(vix=vix)
                    except Exception as e:
                        logger.error(f"Pre-market brief failed: {e}")

            # Auto-retrain daily at 3:45 PM after market close
            if weekday < 5 and hour == 15 and 45 <= minute <= 50:
                today = now.date()
                if last_retrain_date != today:
                    last_retrain_date = today
                    logger.info("Triggering daily auto-retrain...")
                    try:
                        from auto_retrain import retrain
                        result = retrain()
                        logger.info(f"Retrain result: {result['status']} "
                                    f"(candidate {result['candidate_accuracy']}% vs current {result['current_accuracy']}%)")
                    except Exception as e:
                        logger.error(f"Auto-retrain failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# AI INSIGHTS GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_ai_insights(state):
    """Generate intelligent observations based on current live data."""
    insights = []
    win_rate = state["win_rate"]
    confidence = state["confidence"]
    current_streak = state["current_streak"]
    vix = state["vix"]
    ce_pe_ratio = state["ce_pe_ratio"]
    bullish_signals = state["bullish_signals"]
    bearish_signals = state["bearish_signals"]
    no_trade_signals = state["no_trade_signals"]

    if win_rate > 70:
        insights.append({
            "icon": "trending_up", "title": "Strong Performance",
            "text": f"Win rate of {win_rate}% exceeds the 70% benchmark. Model is performing in the top quartile.",
            "type": "positive"
        })
    elif win_rate > 60:
        insights.append({
            "icon": "show_chart", "title": "Stable Performance",
            "text": f"Win rate of {win_rate}% is within acceptable range. Monitor for improvement opportunities.",
            "type": "neutral"
        })
    elif win_rate > 0:
        insights.append({
            "icon": "trending_down", "title": "Performance Alert",
            "text": f"Win rate of {win_rate}% is below optimal threshold. Consider reducing position sizing.",
            "type": "negative"
        })

    if confidence > 75:
        insights.append({
            "icon": "psychology", "title": "High Conviction Signal",
            "text": f"Current confidence at {confidence}% indicates strong model conviction.",
            "type": "positive"
        })
    elif confidence > 60:
        insights.append({
            "icon": "analytics", "title": "Moderate Conviction",
            "text": f"Confidence at {confidence}% suggests moderate edge. Consider standard position sizing.",
            "type": "neutral"
        })
    elif confidence > 0:
        insights.append({
            "icon": "warning", "title": "Low Conviction Alert",
            "text": f"Confidence at {confidence}% is below the high-conviction threshold. Exercise caution.",
            "type": "negative"
        })

    if current_streak > 3:
        insights.append({
            "icon": "local_fire_department", "title": "Hot Streak Active",
            "text": f"Currently on a {current_streak}-win streak. Model alignment with market conditions is strong.",
            "type": "positive"
        })
    elif current_streak < -2:
        insights.append({
            "icon": "ac_unit", "title": "Cold Streak Warning",
            "text": f"Currently on a {abs(current_streak)}-loss streak. Consider waiting for higher confidence signals.",
            "type": "negative"
        })

    if vix > 0 and vix < 14:
        insights.append({
            "icon": "spa", "title": "Low Volatility Environment",
            "text": f"VIX at {vix} indicates calm markets. Model performs well in low-vol regimes.",
            "type": "positive"
        })
    elif vix > 20:
        insights.append({
            "icon": "flash_on", "title": "High Volatility Alert",
            "text": f"VIX at {vix} signals elevated fear. Model accuracy may fluctuate.",
            "type": "negative"
        })

    if ce_pe_ratio > 1.2:
        insights.append({
            "icon": "call_made", "title": "Bullish Options Flow",
            "text": f"CE/PE ratio at {ce_pe_ratio:.2f} indicates strong call buying pressure.",
            "type": "positive"
        })
    elif ce_pe_ratio < 0.8:
        insights.append({
            "icon": "call_received", "title": "Bearish Options Flow",
            "text": f"CE/PE ratio at {ce_pe_ratio:.2f} shows put dominance. Protective positioning detected.",
            "type": "negative"
        })

    total = bullish_signals + bearish_signals + no_trade_signals
    if total > 0:
        bull_pct = (bullish_signals / total) * 100
        insights.append({
            "icon": "pie_chart", "title": "Signal Distribution",
            "text": f"Bullish signals comprise {bull_pct:.1f}% of total. Model shows {'bullish' if bull_pct > 55 else 'balanced'} tendencies.",
            "type": "neutral"
        })

    return insights[:6]


# ═══════════════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    """Render the premium trading dashboard."""
    return render_template("dashboard.html")


@app.route("/api/data")
def api_data():
    """API endpoint for live data refresh."""
    with data_lock:
        state = dict(live_state)

    state["ai_insights"] = generate_ai_insights(state)
    state["model_health"] = get_model_health()
    return jsonify(state)


@app.route("/api/tick")
def api_tick():
    """Lightweight endpoint for 1-second price updates (NIFTY, BANKNIFTY, VIX)."""
    import yfinance as yf

    try:
        # Fast single-ticker fetch for live tick
        nifty_tick = yf.download("^NSEI", period="1d", interval="1m", auto_adjust=True, progress=False)
        bank_tick = yf.download("^NSEBANK", period="1d", interval="1m", auto_adjust=True, progress=False)
        vix_tick = yf.download("^INDIAVIX", period="1d", interval="1m", auto_adjust=True, progress=False)

        def get_latest(df):
            if df.empty:
                return 0.0, 0.0, 0.0
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            price = float(df["Close"].iloc[-1])
            if len(df) >= 2:
                prev_close = float(df["Close"].iloc[0])  # day open
                change = price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
            else:
                change = 0.0
                change_pct = 0.0
            return round(price, 2), round(change, 2), round(change_pct, 2)

        nifty_price, nifty_chg, nifty_pct = get_latest(nifty_tick)
        bank_price, bank_chg, bank_pct = get_latest(bank_tick)
        vix_price, vix_chg, vix_pct = get_latest(vix_tick)

        return jsonify({
            "nifty": nifty_price, "nifty_change": nifty_chg, "nifty_change_pct": nifty_pct,
            "banknifty": bank_price, "banknifty_change": bank_chg, "banknifty_change_pct": bank_pct,
            "vix": vix_price, "vix_change": vix_chg, "vix_change_pct": vix_pct,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
    except Exception as e:
        # Fallback to cached state
        with data_lock:
            return jsonify({
                "nifty": live_state["nifty"], "nifty_change": live_state["nifty_change"],
                "nifty_change_pct": live_state["nifty_change_pct"],
                "banknifty": live_state["banknifty"], "banknifty_change": live_state["banknifty_change"],
                "banknifty_change_pct": live_state["banknifty_change_pct"],
                "vix": live_state["vix"], "vix_change": live_state["vix_change"],
                "vix_change_pct": live_state["vix_change_pct"],
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })


@app.route("/api/best-trades")
def api_best_trades():
    """Get top performing trades (highest profit signals)."""
    import sqlite3
    DB_FILE = str(BASE_DIR / "alphafx.db")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, signal, confidence, nifty, future_price, outcome,
               CASE
                   WHEN signal LIKE '%BULLISH%' THEN future_price - nifty
                   WHEN signal LIKE '%BEARISH%' THEN nifty - future_price
                   ELSE 0
               END as profit_points
        FROM signals
        WHERE outcome = 'WIN' AND future_price IS NOT NULL
        ORDER BY profit_points DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()

    best_trades = []
    for row in rows:
        best_trades.append({
            "timestamp": row[0][:19].replace("T", " ") if row[0] else "",
            "signal": row[1],
            "confidence": row[2],
            "entry_price": row[3],
            "exit_price": row[4],
            "outcome": row[5],
            "profit_points": round(row[6], 2) if row[6] else 0
        })

    return jsonify({"best_trades": best_trades})


@app.route("/api/trade-metrics")
def api_trade_metrics():
    """Real option P&L trade performance metrics."""
    metrics = get_trade_metrics()
    metrics["timeout_comparison"] = get_timeout_comparison()
    return jsonify(metrics)


@app.route("/api/premarket")
def api_premarket():
    """Get today's pre-market brief. Serves cache instantly, regenerates in background if stale."""
    brief = get_latest_brief()
    if brief:
        return jsonify(brief)
    # No cache - generate (this is slow first time)
    with data_lock:
        vix = live_state.get("vix", 15.0)
    brief = generate_premarket_brief(vix=vix)
    return jsonify(brief)


@app.route("/api/premarket/refresh", methods=["POST"])
def api_premarket_refresh():
    """Force regenerate pre-market brief."""
    with data_lock:
        vix = live_state.get("vix", 15.0)
    brief = generate_premarket_brief(vix=vix)
    return jsonify(brief)


@app.route("/api/open-trades")
def api_open_trades():
    """Currently monitored open trades."""
    trades = get_open_trades()
    return jsonify({"open_trades": trades})


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Force a prediction refresh (useful for testing)."""
    threading.Thread(target=run_prediction, daemon=True).start()
    return jsonify({"status": "refresh_started"})





# ═══════════════════════════════════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Auto-refresh instruments.csv if older than 1 day
    instruments_path = BASE_DIR / "instruments.csv"
    try:
        import os
        file_age_hours = (time.time() - os.path.getmtime(instruments_path)) / 3600 if instruments_path.exists() else 999
        if file_age_hours > 24:
            logger.info("Refreshing instruments.csv (older than 24h)...")
            import requests
            r = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30)
            import json as _json
            data = _json.loads(r.text)
            pd.DataFrame(data).to_csv(str(instruments_path), index=False)
            logger.info(f"Instruments updated: {len(data)} contracts")
    except Exception as e:
        logger.warning(f"Could not refresh instruments: {e}")

    # Start background prediction loop
    init_trades_table()
    prediction_thread = threading.Thread(target=prediction_loop, daemon=True)
    prediction_thread.start()

    print("\n" + "=" * 60)
    print("   JPTrades Quantitative Trading Platform")
    print("   Dashboard: http://127.0.0.1:5000")
    print("   API:       http://127.0.0.1:5000/api/data")
    print("   Access from phone: http://<your-pc-ip>:5000")
    print("=" * 60 + "\n")

    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
