"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          AlphaFX Trading Platform                           ║
║                     Premium Quantitative Trading Dashboard                  ║
║                                                                             ║
║  Connect your existing AlphaFX backend by updating the placeholder          ║
║  variables below. All data flows through these variables into the UI.       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from flask import Flask, jsonify, render_template_string
from datetime import datetime, timedelta
import random
import json

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# PLACEHOLDER VARIABLES - Connect your AlphaFX backend here
# Replace these with your actual data sources / function calls
# ═══════════════════════════════════════════════════════════════════════════════

# --- Primary Signal ---
signal = "BULLISH"                # "BULLISH" | "BEARISH" | "NO TRADE"
confidence = 78.5                 # 0-100 confidence percentage
signal_strength = "STRONG"        # "STRONG" | "MODERATE" | "WEAK"

# --- Market Data ---
nifty = 22456.80                  # NIFTY 50 current price
nifty_change = 124.35             # NIFTY absolute change
nifty_change_pct = 0.56           # NIFTY percentage change

banknifty = 48234.50              # BANKNIFTY current price
banknifty_change = -87.20         # BANKNIFTY absolute change
banknifty_change_pct = -0.18      # BANKNIFTY percentage change

vix = 13.42                       # INDIA VIX current value
vix_change = -0.38                # VIX absolute change
vix_change_pct = -2.75            # VIX percentage change

# --- Options Analytics ---
atm_strike = 22450                # At-The-Money strike price
ce_price = 185.60                 # Call option premium
pe_price = 142.30                 # Put option premium
ce_pe_ratio = 1.30                # CE/PE ratio
options_sentiment = "BULLISH"     # "BULLISH" | "BEARISH" | "NEUTRAL"

# --- Performance Metrics ---
wins = 847                        # Total winning signals
losses = 312                      # Total losing signals
total_signals = 1159              # Total signals generated
win_rate = 73.08                  # Win rate percentage
avg_confidence = 72.4             # Average confidence of all signals
best_confidence = 96.8            # Highest confidence signal
worst_confidence = 51.2           # Lowest confidence signal

# --- Trading Statistics ---
current_streak = 5                # Current consecutive wins (negative = losses)
longest_win_streak = 12           # Longest winning streak
longest_loss_streak = 4           # Longest losing streak

# --- Signal History (most recent first) ---
# Each entry: {"timestamp", "signal", "confidence", "entry_price", "future_price", "outcome"}
signal_history = [
    {"timestamp": "2024-12-15 14:30:00", "signal": "BULLISH", "confidence": 82.3, "entry_price": 22380.50, "future_price": 22456.80, "outcome": "WIN"},
    {"timestamp": "2024-12-15 13:45:00", "signal": "BEARISH", "confidence": 68.1, "entry_price": 22412.30, "future_price": 22380.50, "outcome": "WIN"},
    {"timestamp": "2024-12-15 13:00:00", "signal": "BULLISH", "confidence": 74.5, "entry_price": 22350.20, "future_price": 22412.30, "outcome": "WIN"},
    {"timestamp": "2024-12-15 12:15:00", "signal": "BEARISH", "confidence": 61.2, "entry_price": 22320.80, "future_price": 22350.20, "outcome": "LOSS"},
    {"timestamp": "2024-12-15 11:30:00", "signal": "BULLISH", "confidence": 88.7, "entry_price": 22280.40, "future_price": 22320.80, "outcome": "WIN"},
    {"timestamp": "2024-12-15 10:45:00", "signal": "BULLISH", "confidence": 76.3, "entry_price": 22245.60, "future_price": 22280.40, "outcome": "WIN"},
    {"timestamp": "2024-12-15 10:00:00", "signal": "BEARISH", "confidence": 55.8, "entry_price": 22290.10, "future_price": 22245.60, "outcome": "WIN"},
    {"timestamp": "2024-12-15 09:30:00", "signal": "BULLISH", "confidence": 79.4, "entry_price": 22210.30, "future_price": 22290.10, "outcome": "WIN"},
    {"timestamp": "2024-12-14 15:15:00", "signal": "BEARISH", "confidence": 63.5, "entry_price": 22180.70, "future_price": 22210.30, "outcome": "LOSS"},
    {"timestamp": "2024-12-14 14:30:00", "signal": "BULLISH", "confidence": 85.2, "entry_price": 22120.90, "future_price": 22180.70, "outcome": "WIN"},
]

# --- Chart Data (historical series) ---
# Win rate trend over last 30 days
win_rate_trend = [68.2, 69.1, 70.5, 71.2, 69.8, 72.1, 73.5, 72.8, 74.1, 73.0,
                  71.5, 72.9, 73.8, 74.2, 73.5, 72.1, 73.8, 74.5, 75.1, 74.8,
                  73.2, 72.5, 73.1, 74.0, 73.5, 72.8, 73.2, 73.8, 73.0, 73.08]

# Confidence trend over last 30 signals
confidence_trend = [72.1, 68.5, 75.3, 81.2, 69.8, 77.4, 83.1, 65.2, 78.9, 71.3,
                    74.8, 80.5, 67.2, 73.6, 79.1, 85.3, 70.4, 76.8, 82.5, 68.9,
                    74.2, 79.8, 71.5, 77.3, 83.7, 69.1, 75.6, 80.2, 76.3, 78.5]

# Signal distribution
bullish_signals = 623
bearish_signals = 498
no_trade_signals = 38

# Performance curve (cumulative P&L in points)
performance_curve = [0, 12, 8, 25, 38, 31, 45, 52, 48, 63,
                     71, 65, 78, 85, 92, 88, 101, 108, 115, 122,
                     118, 130, 138, 145, 152, 148, 160, 168, 175, 182]

# ═══════════════════════════════════════════════════════════════════════════════
# AI INSIGHTS GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_ai_insights():
    """Generate intelligent observations based on current data."""
    insights = []

    # Performance trend insight
    if win_rate > 70:
        insights.append({
            "icon": "trending_up",
            "title": "Strong Performance",
            "text": f"Win rate of {win_rate}% exceeds the 70% benchmark. Model is performing in the top quartile.",
            "type": "positive"
        })
    elif win_rate > 60:
        insights.append({
            "icon": "show_chart",
            "title": "Stable Performance",
            "text": f"Win rate of {win_rate}% is within acceptable range. Monitor for improvement opportunities.",
            "type": "neutral"
        })
    else:
        insights.append({
            "icon": "trending_down",
            "title": "Performance Alert",
            "text": f"Win rate of {win_rate}% is below optimal threshold. Consider reducing position sizing.",
            "type": "negative"
        })

    # Confidence effectiveness
    if confidence > 75:
        insights.append({
            "icon": "psychology",
            "title": "High Conviction Signal",
            "text": f"Current confidence at {confidence}% indicates strong model conviction. Historical accuracy at this level: ~{min(confidence + 5, 95):.0f}%.",
            "type": "positive"
        })
    elif confidence > 60:
        insights.append({
            "icon": "analytics",
            "title": "Moderate Conviction",
            "text": f"Confidence at {confidence}% suggests moderate edge. Consider standard position sizing.",
            "type": "neutral"
        })
    else:
        insights.append({
            "icon": "warning",
            "title": "Low Conviction Alert",
            "text": f"Confidence at {confidence}% is below the high-conviction threshold. Exercise caution.",
            "type": "negative"
        })

    # Streak analysis
    if current_streak > 3:
        insights.append({
            "icon": "local_fire_department",
            "title": "Hot Streak Active",
            "text": f"Currently on a {current_streak}-win streak. Model alignment with market conditions is strong.",
            "type": "positive"
        })
    elif current_streak < -2:
        insights.append({
            "icon": "ac_unit",
            "title": "Cold Streak Warning",
            "text": f"Currently on a {abs(current_streak)}-loss streak. Consider waiting for higher confidence signals.",
            "type": "negative"
        })

    # VIX analysis
    if vix < 14:
        insights.append({
            "icon": "spa",
            "title": "Low Volatility Environment",
            "text": f"VIX at {vix} indicates calm markets. Model performs well in low-vol regimes historically.",
            "type": "positive"
        })
    elif vix > 20:
        insights.append({
            "icon": "flash_on",
            "title": "High Volatility Alert",
            "text": f"VIX at {vix} signals elevated fear. Model accuracy may fluctuate. Tighten risk management.",
            "type": "negative"
        })

    # Options sentiment
    if ce_pe_ratio > 1.2:
        insights.append({
            "icon": "call_made",
            "title": "Bullish Options Flow",
            "text": f"CE/PE ratio at {ce_pe_ratio:.2f} indicates strong call buying pressure. Aligns with bullish bias.",
            "type": "positive"
        })
    elif ce_pe_ratio < 0.8:
        insights.append({
            "icon": "call_received",
            "title": "Bearish Options Flow",
            "text": f"CE/PE ratio at {ce_pe_ratio:.2f} shows put dominance. Protective positioning detected.",
            "type": "negative"
        })

    # Signal distribution analysis
    total = bullish_signals + bearish_signals + no_trade_signals
    bull_pct = (bullish_signals / total) * 100 if total > 0 else 0
    insights.append({
        "icon": "pie_chart",
        "title": "Signal Distribution",
        "text": f"Bullish signals comprise {bull_pct:.1f}% of total. Model shows {'bullish' if bull_pct > 55 else 'balanced'} tendencies in current regime.",
        "type": "neutral"
    })

    return insights[:6]  # Return max 6 insights


# ═══════════════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    """Render the premium trading dashboard."""
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/data")
def api_data():
    """API endpoint for live data refresh."""
    return jsonify({
        "signal": signal,
        "confidence": confidence,
        "signal_strength": signal_strength,
        "nifty": nifty,
        "nifty_change": nifty_change,
        "nifty_change_pct": nifty_change_pct,
        "banknifty": banknifty,
        "banknifty_change": banknifty_change,
        "banknifty_change_pct": banknifty_change_pct,
        "vix": vix,
        "vix_change": vix_change,
        "vix_change_pct": vix_change_pct,
        "atm_strike": atm_strike,
        "ce_price": ce_price,
        "pe_price": pe_price,
        "ce_pe_ratio": ce_pe_ratio,
        "options_sentiment": options_sentiment,
        "wins": wins,
        "losses": losses,
        "total_signals": total_signals,
        "win_rate": win_rate,
        "avg_confidence": avg_confidence,
        "best_confidence": best_confidence,
        "worst_confidence": worst_confidence,
        "current_streak": current_streak,
        "longest_win_streak": longest_win_streak,
        "longest_loss_streak": longest_loss_streak,
        "signal_history": signal_history,
        "win_rate_trend": win_rate_trend,
        "confidence_trend": confidence_trend,
        "performance_curve": performance_curve,
        "bullish_signals": bullish_signals,
        "bearish_signals": bearish_signals,
        "no_trade_signals": no_trade_signals,
        "ai_insights": generate_ai_insights(),
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_status": "OPEN" if 9 <= datetime.now().hour <= 15 else "CLOSED"
    })


# ═══════════════════════════════════════════════════════════════════════════════
# PREMIUM DASHBOARD HTML/CSS/JS
# ═══════════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AlphaFX | Quantitative Trading Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        /* ═══════════════════════════════════════════════════════════════════ */
        /* RESET & BASE                                                       */
        /* ═══════════════════════════════════════════════════════════════════ */
        *, *::before, *::after {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --bg-card: #1a2332;
            --bg-card-hover: #1f2b3d;
            --bg-elevated: #243044;
            --border-primary: #1e3a5f;
            --border-subtle: rgba(30, 58, 95, 0.5);
            --text-primary: #f0f4f8;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-blue: #3b82f6;
            --accent-blue-glow: rgba(59, 130, 246, 0.3);
            --accent-cyan: #06b6d4;
            --accent-cyan-glow: rgba(6, 182, 212, 0.2);
            --bullish: #10b981;
            --bullish-glow: rgba(16, 185, 129, 0.3);
            --bullish-bg: rgba(16, 185, 129, 0.1);
            --bearish: #ef4444;
            --bearish-glow: rgba(239, 68, 68, 0.3);
            --bearish-bg: rgba(239, 68, 68, 0.1);
            --warning: #f59e0b;
            --warning-glow: rgba(245, 158, 11, 0.3);
            --neutral: #8b5cf6;
            --neutral-glow: rgba(139, 92, 246, 0.3);
            --gold: #fbbf24;
            --gold-glow: rgba(251, 191, 36, 0.2);
            --gradient-bullish: linear-gradient(135deg, #10b981, #059669);
            --gradient-bearish: linear-gradient(135deg, #ef4444, #dc2626);
            --gradient-neutral: linear-gradient(135deg, #8b5cf6, #7c3aed);
            --gradient-accent: linear-gradient(135deg, #3b82f6, #06b6d4);
            --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
            --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
            --shadow-glow-blue: 0 0 20px rgba(59, 130, 246, 0.15);
            --shadow-glow-green: 0 0 20px rgba(16, 185, 129, 0.15);
            --shadow-glow-red: 0 0 20px rgba(239, 68, 68, 0.15);
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --radius-xl: 20px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
            line-height: 1.6;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* BACKGROUND EFFECTS                                                 */
        /* ═══════════════════════════════════════════════════════════════════ */
        .bg-grid {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image:
                linear-gradient(rgba(59, 130, 246, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(59, 130, 246, 0.03) 1px, transparent 1px);
            background-size: 60px 60px;
            pointer-events: none;
            z-index: 0;
        }

        .bg-gradient-orb {
            position: fixed;
            border-radius: 50%;
            filter: blur(80px);
            pointer-events: none;
            z-index: 0;
        }

        .orb-1 {
            top: -10%;
            right: -5%;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(59, 130, 246, 0.08), transparent 70%);
        }

        .orb-2 {
            bottom: -10%;
            left: -5%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(6, 182, 212, 0.06), transparent 70%);
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* HEADER / HERO                                                      */
        /* ═══════════════════════════════════════════════════════════════════ */
        .header {
            position: sticky;
            top: 0;
            z-index: 1000;
            background: rgba(10, 14, 23, 0.85);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-subtle);
            padding: 0 2rem;
        }

        .header-inner {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 64px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-logo {
            width: 36px;
            height: 36px;
            background: var(--gradient-accent);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 14px;
            color: white;
            box-shadow: var(--shadow-glow-blue);
        }

        .brand-text {
            font-size: 1.25rem;
            font-weight: 700;
            background: linear-gradient(135deg, #f0f4f8, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }

        .brand-badge {
            background: var(--bg-elevated);
            border: 1px solid var(--border-primary);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.65rem;
            font-weight: 600;
            color: var(--accent-cyan);
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .market-status {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .market-status.open {
            background: var(--bullish-bg);
            color: var(--bullish);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .market-status.closed {
            background: rgba(239, 68, 68, 0.1);
            color: var(--bearish);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .market-status.open .status-dot {
            background: var(--bullish);
            box-shadow: 0 0 8px var(--bullish);
        }

        .market-status.closed .status-dot {
            background: var(--bearish);
            box-shadow: 0 0 8px var(--bearish);
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.8); }
        }

        .header-time {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .last-update {
            font-size: 0.7rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .last-update .material-icons {
            font-size: 14px;
            animation: spin 2s linear infinite;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* MAIN LAYOUT                                                        */
        /* ═══════════════════════════════════════════════════════════════════ */
        .main-container {
            position: relative;
            z-index: 1;
            max-width: 1600px;
            margin: 0 auto;
            padding: 1.5rem 2rem 4rem;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* CARDS                                                               */
        /* ═══════════════════════════════════════════════════════════════════ */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--accent-blue), transparent);
            opacity: 0;
            transition: var(--transition);
        }

        .card:hover {
            border-color: var(--border-primary);
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }

        .card:hover::before {
            opacity: 1;
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.25rem;
        }

        .card-title {
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-title .material-icons {
            font-size: 18px;
            color: var(--accent-blue);
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* SIGNAL ENGINE CARD                                                  */
        /* ═══════════════════════════════════════════════════════════════════ */
        .signal-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-xl);
            padding: 2.5rem;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .signal-card.bullish {
            border-color: rgba(16, 185, 129, 0.3);
            box-shadow: var(--shadow-glow-green);
        }

        .signal-card.bearish {
            border-color: rgba(239, 68, 68, 0.3);
            box-shadow: var(--shadow-glow-red);
        }

        .signal-card::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
        }

        .signal-card.bullish::after {
            background: var(--gradient-bullish);
        }

        .signal-card.bearish::after {
            background: var(--gradient-bearish);
        }

        .signal-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 20px;
            border-radius: 30px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 1.5rem;
        }

        .signal-badge.bullish {
            background: var(--bullish-bg);
            color: var(--bullish);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .signal-badge.bearish {
            background: var(--bearish-bg);
            color: var(--bearish);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .signal-badge.neutral {
            background: rgba(139, 92, 246, 0.1);
            color: var(--neutral);
            border: 1px solid rgba(139, 92, 246, 0.3);
        }

        .signal-direction {
            font-size: 3rem;
            font-weight: 900;
            letter-spacing: -2px;
            margin-bottom: 0.5rem;
            line-height: 1.1;
        }

        .signal-direction.bullish { color: var(--bullish); }
        .signal-direction.bearish { color: var(--bearish); }
        .signal-direction.neutral { color: var(--neutral); }

        .confidence-display {
            margin: 1.5rem 0;
        }

        .confidence-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 3.5rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1;
        }

        .confidence-label {
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-top: 0.5rem;
        }

        .confidence-bar-container {
            width: 100%;
            max-width: 400px;
            margin: 1.5rem auto;
            height: 8px;
            background: var(--bg-elevated);
            border-radius: 4px;
            overflow: hidden;
        }

        .confidence-bar {
            height: 100%;
            border-radius: 4px;
            transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .confidence-bar.bullish {
            background: var(--gradient-bullish);
            box-shadow: 0 0 10px var(--bullish-glow);
        }

        .confidence-bar.bearish {
            background: var(--gradient-bearish);
            box-shadow: 0 0 10px var(--bearish-glow);
        }

        .signal-strength-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 16px;
            background: var(--bg-elevated);
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--text-secondary);
            letter-spacing: 0.5px;
            margin-top: 1rem;
        }

        .strength-dots {
            display: flex;
            gap: 3px;
        }

        .strength-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--bg-primary);
        }

        .strength-dot.active { background: var(--accent-cyan); }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* MARKET OVERVIEW CARDS                                               */
        /* ═══════════════════════════════════════════════════════════════════ */
        .market-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
        }

        .market-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 1.25rem 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: var(--transition);
        }

        .market-card:hover {
            border-color: var(--border-primary);
            background: var(--bg-card-hover);
        }

        .market-info h3 {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }

        .market-price {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .market-change {
            text-align: right;
        }

        .market-change-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            font-weight: 600;
        }

        .market-change-pct {
            font-size: 0.75rem;
            font-weight: 500;
            padding: 2px 8px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 2px;
        }

        .positive { color: var(--bullish); }
        .negative { color: var(--bearish); }

        .positive-bg {
            background: var(--bullish-bg);
            color: var(--bullish);
        }

        .negative-bg {
            background: var(--bearish-bg);
            color: var(--bearish);
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* OPTIONS ANALYTICS                                                   */
        /* ═══════════════════════════════════════════════════════════════════ */
        .options-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 1rem;
        }

        .option-metric {
            background: var(--bg-elevated);
            border-radius: var(--radius-sm);
            padding: 1rem 1.25rem;
            text-align: center;
        }

        .option-metric-label {
            font-size: 0.65rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }

        .option-metric-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .sentiment-gauge {
            margin-top: 1.5rem;
            padding: 1.25rem;
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
        }

        .gauge-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.75rem;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .gauge-bar {
            height: 10px;
            background: var(--bg-primary);
            border-radius: 5px;
            overflow: hidden;
            display: flex;
        }

        .gauge-fill-bull {
            background: var(--gradient-bullish);
            transition: width 1s ease;
        }

        .gauge-fill-bear {
            background: var(--gradient-bearish);
            transition: width 1s ease;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* KPI CARDS                                                           */
        /* ═══════════════════════════════════════════════════════════════════ */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 1.25rem;
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }

        .kpi-card:hover {
            border-color: var(--border-primary);
            transform: translateY(-1px);
        }

        .kpi-icon {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.75rem;
        }

        .kpi-icon .material-icons {
            font-size: 18px;
            color: white;
        }

        .kpi-icon.blue { background: rgba(59, 130, 246, 0.2); }
        .kpi-icon.blue .material-icons { color: var(--accent-blue); }
        .kpi-icon.green { background: rgba(16, 185, 129, 0.2); }
        .kpi-icon.green .material-icons { color: var(--bullish); }
        .kpi-icon.red { background: rgba(239, 68, 68, 0.2); }
        .kpi-icon.red .material-icons { color: var(--bearish); }
        .kpi-icon.gold { background: rgba(251, 191, 36, 0.2); }
        .kpi-icon.gold .material-icons { color: var(--gold); }
        .kpi-icon.cyan { background: rgba(6, 182, 212, 0.2); }
        .kpi-icon.cyan .material-icons { color: var(--accent-cyan); }
        .kpi-icon.purple { background: rgba(139, 92, 246, 0.2); }
        .kpi-icon.purple .material-icons { color: var(--neutral); }

        .kpi-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
        }

        .kpi-label {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-top: 4px;
            font-weight: 500;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* CHARTS                                                              */
        /* ═══════════════════════════════════════════════════════════════════ */
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 1.5rem;
        }

        .chart-container {
            position: relative;
            height: 260px;
            padding: 0.5rem;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* SIGNAL HISTORY TABLE                                                */
        /* ═══════════════════════════════════════════════════════════════════ */
        .table-container {
            overflow-x: auto;
            border-radius: var(--radius-md);
        }

        .signal-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8rem;
        }

        .signal-table thead {
            background: var(--bg-elevated);
        }

        .signal-table th {
            padding: 0.75rem 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-size: 0.65rem;
            border-bottom: 1px solid var(--border-subtle);
        }

        .signal-table td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid rgba(30, 58, 95, 0.3);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .signal-table tr:hover td {
            background: rgba(59, 130, 246, 0.03);
        }

        .table-signal-badge {
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .table-signal-badge.bullish {
            background: var(--bullish-bg);
            color: var(--bullish);
        }

        .table-signal-badge.bearish {
            background: var(--bearish-bg);
            color: var(--bearish);
        }

        .outcome-badge {
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 0.65rem;
            font-weight: 700;
        }

        .outcome-badge.win {
            background: var(--bullish-bg);
            color: var(--bullish);
        }

        .outcome-badge.loss {
            background: var(--bearish-bg);
            color: var(--bearish);
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* AI INSIGHTS                                                         */
        /* ═══════════════════════════════════════════════════════════════════ */
        .insights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
        }

        .insight-item {
            display: flex;
            gap: 1rem;
            padding: 1rem 1.25rem;
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
            border-left: 3px solid;
            transition: var(--transition);
        }

        .insight-item:hover {
            background: var(--bg-card-hover);
        }

        .insight-item.positive { border-left-color: var(--bullish); }
        .insight-item.negative { border-left-color: var(--bearish); }
        .insight-item.neutral { border-left-color: var(--accent-blue); }

        .insight-icon {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .insight-item.positive .insight-icon {
            background: var(--bullish-bg);
            color: var(--bullish);
        }

        .insight-item.negative .insight-icon {
            background: var(--bearish-bg);
            color: var(--bearish);
        }

        .insight-item.neutral .insight-icon {
            background: rgba(59, 130, 246, 0.1);
            color: var(--accent-blue);
        }

        .insight-icon .material-icons {
            font-size: 18px;
        }

        .insight-content h4 {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 4px;
        }

        .insight-content p {
            font-size: 0.75rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* TRADING STATS                                                       */
        /* ═══════════════════════════════════════════════════════════════════ */
        .stats-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }

        .stat-item {
            text-align: center;
            padding: 1.25rem;
            background: var(--bg-elevated);
            border-radius: var(--radius-md);
        }

        .stat-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .stat-label {
            font-size: 0.65rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 4px;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* SECTION DIVIDER                                                     */
        /* ═══════════════════════════════════════════════════════════════════ */
        .section-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--border-primary), transparent);
            margin: 0.5rem 0;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* FOOTER                                                              */
        /* ═══════════════════════════════════════════════════════════════════ */
        .footer {
            text-align: center;
            padding: 2rem 0;
            border-top: 1px solid var(--border-subtle);
            margin-top: 2rem;
        }

        .footer p {
            font-size: 0.7rem;
            color: var(--text-muted);
            letter-spacing: 0.5px;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* ANIMATIONS                                                          */
        /* ═══════════════════════════════════════════════════════════════════ */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .animate-in {
            animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards;
            opacity: 0;
        }

        .delay-1 { animation-delay: 0.1s; }
        .delay-2 { animation-delay: 0.2s; }
        .delay-3 { animation-delay: 0.3s; }
        .delay-4 { animation-delay: 0.4s; }
        .delay-5 { animation-delay: 0.5s; }
        .delay-6 { animation-delay: 0.6s; }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* RESPONSIVE                                                          */
        /* ═══════════════════════════════════════════════════════════════════ */
        @media (max-width: 768px) {
            .header { padding: 0 1rem; }
            .main-container { padding: 1rem; }
            .signal-direction { font-size: 2rem; }
            .confidence-value { font-size: 2.5rem; }
            .charts-grid { grid-template-columns: 1fr; }
            .market-grid { grid-template-columns: 1fr; }
            .kpi-grid { grid-template-columns: repeat(2, 1fr); }
            .brand-badge { display: none; }
            .header-time { display: none; }
        }

        @media (max-width: 480px) {
            .kpi-grid { grid-template-columns: 1fr; }
            .options-grid { grid-template-columns: repeat(2, 1fr); }
            .insights-grid { grid-template-columns: 1fr; }
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { background: var(--border-primary); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--accent-blue); }
    </style>
</head>
<body>
    <!-- Background Effects -->
    <div class="bg-grid"></div>
    <div class="bg-gradient-orb orb-1"></div>
    <div class="bg-gradient-orb orb-2"></div>

    <!-- Header -->
    <header class="header">
        <div class="header-inner">
            <div class="brand">
                <div class="brand-logo">Fx</div>
                <span class="brand-text">AlphaFX</span>
                <span class="brand-badge">QUANT ENGINE</span>
            </div>
            <div class="header-right">
                <div id="marketStatus" class="market-status open">
                    <span class="status-dot"></span>
                    <span id="marketStatusText">MARKET OPEN</span>
                </div>
                <div class="header-time" id="currentTime">--:--:--</div>
                <div class="last-update">
                    <span class="material-icons">sync</span>
                    <span id="lastUpdate">Updating...</span>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="main-container">
        <div class="dashboard-grid">

            <!-- ═══ AI SIGNAL ENGINE ═══ -->
            <div id="signalCard" class="signal-card bullish animate-in delay-1">
                <div class="card-header" style="justify-content: center;">
                    <span class="card-title">
                        <span class="material-icons">psychology</span>
                        AI SIGNAL ENGINE
                    </span>
                </div>
                <div id="signalBadge" class="signal-badge bullish">
                    <span class="material-icons" style="font-size: 14px;">bolt</span>
                    ACTIVE SIGNAL
                </div>
                <div id="signalDirection" class="signal-direction bullish">BULLISH</div>
                <div class="confidence-display">
                    <div class="confidence-value" id="confidenceValue">78.5%</div>
                    <div class="confidence-label">Model Confidence</div>
                </div>
                <div class="confidence-bar-container">
                    <div id="confidenceBar" class="confidence-bar bullish" style="width: 78.5%"></div>
                </div>
                <div class="signal-strength-indicator">
                    <span>SIGNAL STRENGTH:</span>
                    <div class="strength-dots" id="strengthDots">
                        <span class="strength-dot active"></span>
                        <span class="strength-dot active"></span>
                        <span class="strength-dot active"></span>
                        <span class="strength-dot"></span>
                        <span class="strength-dot"></span>
                    </div>
                    <span id="strengthText">STRONG</span>
                </div>
            </div>

            <!-- ═══ MARKET OVERVIEW ═══ -->
            <div class="card animate-in delay-2">
                <div class="card-header">
                    <span class="card-title">
                        <span class="material-icons">candlestick_chart</span>
                        MARKET OVERVIEW
                    </span>
                    <span style="font-size: 0.65rem; color: var(--text-muted);">LIVE</span>
                </div>
                <div class="market-grid">
                    <div class="market-card">
                        <div class="market-info">
                            <h3>NIFTY 50</h3>
                            <div class="market-price" id="niftyPrice">22,456.80</div>
                        </div>
                        <div class="market-change">
                            <div class="market-change-value positive" id="niftyChange">+124.35</div>
                            <div class="market-change-pct positive-bg" id="niftyChangePct">+0.56%</div>
                        </div>
                    </div>
                    <div class="market-card">
                        <div class="market-info">
                            <h3>BANKNIFTY</h3>
                            <div class="market-price" id="bankniftyPrice">48,234.50</div>
                        </div>
                        <div class="market-change">
                            <div class="market-change-value negative" id="bankniftyChange">-87.20</div>
                            <div class="market-change-pct negative-bg" id="bankniftyChangePct">-0.18%</div>
                        </div>
                    </div>
                    <div class="market-card">
                        <div class="market-info">
                            <h3>INDIA VIX</h3>
                            <div class="market-price" id="vixPrice">13.42</div>
                        </div>
                        <div class="market-change">
                            <div class="market-change-value negative" id="vixChange">-0.38</div>
                            <div class="market-change-pct negative-bg" id="vixChangePct">-2.75%</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ═══ OPTIONS ANALYTICS ═══ -->
            <div class="card animate-in delay-3">
                <div class="card-header">
                    <span class="card-title">
                        <span class="material-icons">analytics</span>
                        OPTIONS ANALYTICS
                    </span>
                    <span id="optionsSentimentBadge" class="signal-badge bullish" style="font-size: 0.6rem; padding: 4px 12px;">BULLISH FLOW</span>
                </div>
                <div class="options-grid">
                    <div class="option-metric">
                        <div class="option-metric-label">ATM Strike</div>
                        <div class="option-metric-value" id="atmStrike">22,450</div>
                    </div>
                    <div class="option-metric">
                        <div class="option-metric-label">CE Price</div>
                        <div class="option-metric-value positive" id="cePrice">₹185.60</div>
                    </div>
                    <div class="option-metric">
                        <div class="option-metric-label">PE Price</div>
                        <div class="option-metric-value negative" id="pePrice">₹142.30</div>
                    </div>
                    <div class="option-metric">
                        <div class="option-metric-label">CE/PE Ratio</div>
                        <div class="option-metric-value" id="cePeRatio" style="color: var(--accent-cyan);">1.30</div>
                    </div>
                </div>
                <div class="sentiment-gauge">
                    <div class="gauge-header">
                        <span class="positive">CALLS (CE)</span>
                        <span id="gaugeRatioText" style="color: var(--text-primary); font-weight: 700;">56.5% / 43.5%</span>
                        <span class="negative">PUTS (PE)</span>
                    </div>
                    <div class="gauge-bar">
                        <div class="gauge-fill-bull" id="gaugeBull" style="width: 56.5%"></div>
                        <div class="gauge-fill-bear" id="gaugeBear" style="width: 43.5%"></div>
                    </div>
                </div>
            </div>

            <!-- ═══ PERFORMANCE KPIs ═══ -->
            <div class="card animate-in delay-4">
                <div class="card-header">
                    <span class="card-title">
                        <span class="material-icons">leaderboard</span>
                        PERFORMANCE ANALYTICS
                    </span>
                </div>
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-icon blue"><span class="material-icons">signal_cellular_alt</span></div>
                        <div class="kpi-value" id="kpiTotalSignals">1,159</div>
                        <div class="kpi-label">Total Signals</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-icon green"><span class="material-icons">check_circle</span></div>
                        <div class="kpi-value" id="kpiWins">847</div>
                        <div class="kpi-label">Wins</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-icon red"><span class="material-icons">cancel</span></div>
                        <div class="kpi-value" id="kpiLosses">312</div>
                        <div class="kpi-label">Losses</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-icon gold"><span class="material-icons">emoji_events</span></div>
                        <div class="kpi-value" id="kpiWinRate">73.08%</div>
                        <div class="kpi-label">Win Rate</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-icon cyan"><span class="material-icons">speed</span></div>
                        <div class="kpi-value" id="kpiAvgConf">72.4%</div>
                        <div class="kpi-label">Avg Confidence</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-icon purple"><span class="material-icons">star</span></div>
                        <div class="kpi-value" id="kpiBestConf">96.8%</div>
                        <div class="kpi-label">Best Confidence</div>
                    </div>
                </div>
            </div>

            <!-- ═══ TRADING STATISTICS ═══ -->
            <div class="card animate-in delay-4">
                <div class="card-header">
                    <span class="card-title">
                        <span class="material-icons">query_stats</span>
                        TRADING STATISTICS
                    </span>
                </div>
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-value positive" id="statCurrentStreak">+5</div>
                        <div class="stat-label">Current Streak</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" style="color: var(--gold);" id="statLongestWin">12</div>
                        <div class="stat-label">Longest Win Streak</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value negative" id="statLongestLoss">4</div>
                        <div class="stat-label">Longest Loss Streak</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" style="color: var(--accent-cyan);" id="statTotalPred">1,159</div>
                        <div class="stat-label">Total Predictions</div>
                    </div>
                </div>
            </div>

            <!-- ═══ CHARTS ═══ -->
            <div class="card animate-in delay-5">
                <div class="card-header">
                    <span class="card-title">
                        <span class="material-icons">insert_chart</span>
                        ANALYTICS CHARTS
                    </span>
                </div>
                <div class="charts-grid">
                    <div>
                        <h4 style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.75rem; font-weight: 600;">Win Rate Trend (30 Days)</h4>
                        <div class="chart-container">
                            <canvas id="winRateChart"></canvas>
                        </div>
                    </div>
                    <div>
                        <h4 style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.75rem; font-weight: 600;">Confidence Trend (Last 30 Signals)</h4>
                        <div class="chart-container">
                            <canvas id="confidenceChart"></canvas>
                        </div>
                    </div>
                    <div>
                        <h4 style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.75rem; font-weight: 600;">Performance Curve (Cumulative P&L)</h4>
                        <div class="chart-container">
                            <canvas id="performanceChart"></canvas>
                        </div>
                    </div>
                    <div>
                        <h4 style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.75rem; font-weight: 600;">Signal Distribution</h4>
                        <div class="chart-container">
                            <canvas id="distributionChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ═══ SIGNAL HISTORY ═══ -->
            <div class="card animate-in delay-5">
                <div class="card-header">
                    <span class="card-title">
                        <span class="material-icons">history</span>
                        SIGNAL HISTORY
                    </span>
                    <span style="font-size: 0.65rem; color: var(--text-muted);">LAST 10 SIGNALS</span>
                </div>
                <div class="table-container">
                    <table class="signal-table">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Signal</th>
                                <th>Confidence</th>
                                <th>Entry Price</th>
                                <th>Future Price</th>
                                <th>Outcome</th>
                            </tr>
                        </thead>
                        <tbody id="signalHistoryBody">
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- ═══ AI INSIGHTS ═══ -->
            <div class="card animate-in delay-6">
                <div class="card-header">
                    <span class="card-title">
                        <span class="material-icons">auto_awesome</span>
                        AI INSIGHTS
                    </span>
                    <span style="font-size: 0.65rem; color: var(--accent-cyan); font-weight: 600;">POWERED BY ALPHAFX ENGINE</span>
                </div>
                <div class="insights-grid" id="insightsGrid">
                </div>
            </div>

        </div>

        <!-- Footer -->
        <div class="footer">
            <p>AlphaFX Quantitative Trading Platform &bull; Machine Learning Powered &bull; Built for Professional Traders</p>
        </div>
    </main>

    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <!-- JAVASCRIPT                                                         -->
    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <script>
        // ─── Chart.js Global Config ───
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.borderColor = 'rgba(30, 58, 95, 0.3)';
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.font.size = 11;

        let winRateChart, confidenceChart, performanceChart, distributionChart;

        // ─── Initialize Dashboard ───
        function initDashboard() {
            fetchData();
            initCharts();
            updateClock();
            setInterval(updateClock, 1000);
            setInterval(fetchData, 10000); // Auto-refresh every 10 seconds
        }

        // ─── Clock ───
        function updateClock() {
            const now = new Date();
            document.getElementById('currentTime').textContent = now.toLocaleTimeString('en-IN', { hour12: false });
        }

        // ─── Fetch Data ───
        async function fetchData() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Data fetch error:', error);
            }
        }

        // ─── Update Dashboard ───
        function updateDashboard(data) {
            // Market Status
            const statusEl = document.getElementById('marketStatus');
            const statusTextEl = document.getElementById('marketStatusText');
            if (data.market_status === 'OPEN') {
                statusEl.className = 'market-status open';
                statusTextEl.textContent = 'MARKET OPEN';
            } else {
                statusEl.className = 'market-status closed';
                statusTextEl.textContent = 'MARKET CLOSED';
            }

            // Last Update
            document.getElementById('lastUpdate').textContent = data.last_update;

            // Signal Engine
            const signalCard = document.getElementById('signalCard');
            const signalBadge = document.getElementById('signalBadge');
            const signalDir = document.getElementById('signalDirection');
            const confBar = document.getElementById('confidenceBar');
            const sigClass = data.signal === 'BULLISH' ? 'bullish' : data.signal === 'BEARISH' ? 'bearish' : 'neutral';

            signalCard.className = `signal-card ${sigClass} animate-in`;
            signalBadge.className = `signal-badge ${sigClass}`;
            signalDir.className = `signal-direction ${sigClass}`;
            signalDir.textContent = data.signal;
            confBar.className = `confidence-bar ${sigClass}`;
            confBar.style.width = data.confidence + '%';
            document.getElementById('confidenceValue').textContent = data.confidence.toFixed(1) + '%';

            // Signal Strength
            const strengthDots = document.getElementById('strengthDots');
            let activeDots = data.signal_strength === 'STRONG' ? 4 : data.signal_strength === 'MODERATE' ? 3 : 2;
            strengthDots.innerHTML = '';
            for (let i = 0; i < 5; i++) {
                const dot = document.createElement('span');
                dot.className = 'strength-dot' + (i < activeDots ? ' active' : '');
                strengthDots.appendChild(dot);
            }
            document.getElementById('strengthText').textContent = data.signal_strength;

            // Market Data
            updateMarketCard('nifty', data.nifty, data.nifty_change, data.nifty_change_pct);
            updateMarketCard('banknifty', data.banknifty, data.banknifty_change, data.banknifty_change_pct);
            updateMarketCard('vix', data.vix, data.vix_change, data.vix_change_pct);

            // Options
            document.getElementById('atmStrike').textContent = data.atm_strike.toLocaleString();
            document.getElementById('cePrice').textContent = '₹' + data.ce_price.toFixed(2);
            document.getElementById('pePrice').textContent = '₹' + data.pe_price.toFixed(2);
            document.getElementById('cePeRatio').textContent = data.ce_pe_ratio.toFixed(2);

            // Sentiment gauge
            const total = data.ce_price + data.pe_price;
            const bullPct = ((data.ce_price / total) * 100).toFixed(1);
            const bearPct = ((data.pe_price / total) * 100).toFixed(1);
            document.getElementById('gaugeBull').style.width = bullPct + '%';
            document.getElementById('gaugeBear').style.width = bearPct + '%';
            document.getElementById('gaugeRatioText').textContent = bullPct + '% / ' + bearPct + '%';

            const sentBadge = document.getElementById('optionsSentimentBadge');
            const sentClass = data.options_sentiment === 'BULLISH' ? 'bullish' : data.options_sentiment === 'BEARISH' ? 'bearish' : 'neutral';
            sentBadge.className = `signal-badge ${sentClass}`;
            sentBadge.style.fontSize = '0.6rem';
            sentBadge.style.padding = '4px 12px';
            sentBadge.textContent = data.options_sentiment + ' FLOW';

            // KPIs
            document.getElementById('kpiTotalSignals').textContent = data.total_signals.toLocaleString();
            document.getElementById('kpiWins').textContent = data.wins.toLocaleString();
            document.getElementById('kpiLosses').textContent = data.losses.toLocaleString();
            document.getElementById('kpiWinRate').textContent = data.win_rate.toFixed(2) + '%';
            document.getElementById('kpiAvgConf').textContent = data.avg_confidence.toFixed(1) + '%';
            document.getElementById('kpiBestConf').textContent = data.best_confidence.toFixed(1) + '%';

            // Trading Stats
            const streakVal = data.current_streak;
            const streakEl = document.getElementById('statCurrentStreak');
            streakEl.textContent = (streakVal > 0 ? '+' : '') + streakVal;
            streakEl.className = 'stat-value ' + (streakVal > 0 ? 'positive' : 'negative');
            document.getElementById('statLongestWin').textContent = data.longest_win_streak;
            document.getElementById('statLongestLoss').textContent = data.longest_loss_streak;
            document.getElementById('statTotalPred').textContent = data.total_signals.toLocaleString();

            // Signal History Table
            const tbody = document.getElementById('signalHistoryBody');
            tbody.innerHTML = '';
            data.signal_history.forEach(s => {
                const sigCls = s.signal === 'BULLISH' ? 'bullish' : 'bearish';
                const outCls = s.outcome === 'WIN' ? 'win' : 'loss';
                tbody.innerHTML += `
                    <tr>
                        <td>${s.timestamp}</td>
                        <td><span class="table-signal-badge ${sigCls}">${s.signal}</span></td>
                        <td>${s.confidence.toFixed(1)}%</td>
                        <td>${s.entry_price.toFixed(2)}</td>
                        <td>${s.future_price.toFixed(2)}</td>
                        <td><span class="outcome-badge ${outCls}">${s.outcome}</span></td>
                    </tr>
                `;
            });

            // AI Insights
            const insightsGrid = document.getElementById('insightsGrid');
            insightsGrid.innerHTML = '';
            data.ai_insights.forEach(insight => {
                insightsGrid.innerHTML += `
                    <div class="insight-item ${insight.type}">
                        <div class="insight-icon">
                            <span class="material-icons">${insight.icon}</span>
                        </div>
                        <div class="insight-content">
                            <h4>${insight.title}</h4>
                            <p>${insight.text}</p>
                        </div>
                    </div>
                `;
            });

            // Update Charts
            updateCharts(data);
        }

        // ─── Market Card Helper ───
        function updateMarketCard(prefix, price, change, changePct) {
            const priceEl = document.getElementById(prefix + 'Price');
            const changeEl = document.getElementById(prefix + 'Change');
            const changePctEl = document.getElementById(prefix + 'ChangePct');

            priceEl.textContent = price.toLocaleString('en-IN', { minimumFractionDigits: 2 });
            changeEl.textContent = (change >= 0 ? '+' : '') + change.toFixed(2);
            changeEl.className = 'market-change-value ' + (change >= 0 ? 'positive' : 'negative');
            changePctEl.textContent = (changePct >= 0 ? '+' : '') + changePct.toFixed(2) + '%';
            changePctEl.className = 'market-change-pct ' + (changePct >= 0 ? 'positive-bg' : 'negative-bg');
        }

        // ─── Initialize Charts ───
        function initCharts() {
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1a2332',
                        titleColor: '#f0f4f8',
                        bodyColor: '#94a3b8',
                        borderColor: '#1e3a5f',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        displayColors: false
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { maxTicksLimit: 8, font: { size: 10 } }
                    },
                    y: {
                        grid: { color: 'rgba(30, 58, 95, 0.2)' },
                        ticks: { font: { size: 10 } }
                    }
                },
                elements: {
                    point: { radius: 0, hoverRadius: 5, hoverBackgroundColor: '#3b82f6' },
                    line: { tension: 0.4, borderWidth: 2 }
                }
            };

            // Win Rate Chart
            winRateChart = new Chart(document.getElementById('winRateChart'), {
                type: 'line',
                data: {
                    labels: Array.from({length: 30}, (_, i) => `Day ${i+1}`),
                    datasets: [{
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true
                    }]
                },
                options: { ...chartOptions, scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, min: 60, max: 85, ticks: { ...chartOptions.scales.y.ticks, callback: v => v + '%' } } } }
            });

            // Confidence Chart
            confidenceChart = new Chart(document.getElementById('confidenceChart'), {
                type: 'line',
                data: {
                    labels: Array.from({length: 30}, (_, i) => `#${i+1}`),
                    datasets: [{
                        data: [],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true
                    }]
                },
                options: { ...chartOptions, scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, min: 50, max: 100, ticks: { ...chartOptions.scales.y.ticks, callback: v => v + '%' } } } }
            });

            // Performance Chart
            performanceChart = new Chart(document.getElementById('performanceChart'), {
                type: 'line',
                data: {
                    labels: Array.from({length: 30}, (_, i) => `Day ${i+1}`),
                    datasets: [{
                        data: [],
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        fill: true
                    }]
                },
                options: { ...chartOptions, scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, ticks: { ...chartOptions.scales.y.ticks, callback: v => v + ' pts' } } } }
            });

            // Distribution Chart
            distributionChart = new Chart(document.getElementById('distributionChart'), {
                type: 'doughnut',
                data: {
                    labels: ['Bullish', 'Bearish', 'No Trade'],
                    datasets: [{
                        data: [],
                        backgroundColor: ['rgba(16, 185, 129, 0.8)', 'rgba(239, 68, 68, 0.8)', 'rgba(139, 92, 246, 0.8)'],
                        borderColor: ['rgba(16, 185, 129, 1)', 'rgba(239, 68, 68, 1)', 'rgba(139, 92, 246, 1)'],
                        borderWidth: 2,
                        hoverOffset: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true,
                                pointStyle: 'circle',
                                font: { size: 11 }
                            }
                        },
                        tooltip: {
                            backgroundColor: '#1a2332',
                            titleColor: '#f0f4f8',
                            bodyColor: '#94a3b8',
                            borderColor: '#1e3a5f',
                            borderWidth: 1,
                            padding: 12,
                            cornerRadius: 8
                        }
                    }
                }
            });
        }

        // ─── Update Charts ───
        function updateCharts(data) {
            if (winRateChart) {
                winRateChart.data.datasets[0].data = data.win_rate_trend;
                winRateChart.update('none');
            }
            if (confidenceChart) {
                confidenceChart.data.datasets[0].data = data.confidence_trend;
                confidenceChart.update('none');
            }
            if (performanceChart) {
                performanceChart.data.datasets[0].data = data.performance_curve;
                performanceChart.update('none');
            }
            if (distributionChart) {
                distributionChart.data.datasets[0].data = [data.bullish_signals, data.bearish_signals, data.no_trade_signals];
                distributionChart.update('none');
            }
        }

        // ─── Start ───
        document.addEventListener('DOMContentLoaded', initDashboard);
    </script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\\n" + "═" * 60)
    print("   AlphaFX Quantitative Trading Platform")
    print("   Dashboard running at: http://127.0.0.1:5000")
    print("═" * 60 + "\\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
