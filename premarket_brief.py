"""
JPTrades - Pre-Market Intelligence System
Generates a professional morning briefing at 08:45 AM IST.
Uses Marketaux API for news + free data for global markets.

CRITICAL: News NEVER overrides model signals. Advisory only.
"""

import os
import json
import sqlite3
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = str(BASE_DIR / "alphafx.db")
CACHE_FILE = BASE_DIR / "models" / "premarket_cache.json"

# Marketaux API
MARKETAUX_KEY = "WnIcx8XIhrTD3Hm3pW8XeG6Dlq0Uf9YJKHLPbV3i"
MARKETAUX_URL = "https://api.marketaux.com/v1/news/all"

# Keywords for classification
BULLISH_WORDS = ["rally", "surge", "gain", "bull", "rise", "high", "record", "positive", "growth", "recovery", "buying", "upgrade"]
BEARISH_WORDS = ["crash", "fall", "drop", "bear", "down", "low", "selloff", "fear", "weak", "decline", "correction", "downgrade"]
SECTORS = ["banking", "bank", "it", "tech", "auto", "pharma", "energy", "oil", "metal", "fmcg", "realty", "infra", "financial"]


def init_brief_db():
    """Create pre-market tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premarket_briefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            generated_at TEXT,
            market_bias TEXT,
            bias_reasons TEXT,
            risk_level TEXT,
            risk_reasons TEXT,
            sentiment_bull REAL,
            sentiment_neutral REAL,
            sentiment_bear REAL,
            regime TEXT,
            guidance TEXT,
            watchlist TEXT,
            events TEXT,
            headlines TEXT,
            raw_data TEXT
        )
    """)
    conn.commit()
    conn.close()


def fetch_marketaux_news(limit=10):
    """Fetch latest Indian market news from Marketaux API."""
    try:
        params = {
            "api_token": MARKETAUX_KEY,
            "countries": "in",
            "filter_entities": "true",
            "language": "en",
            "limit": limit,
        }
        resp = requests.get(MARKETAUX_URL, params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"Marketaux API returned {resp.status_code}")
            return []

        data = resp.json()
        articles = data.get("data", [])

        news = []
        for article in articles:
            title = article.get("title", "")
            description = article.get("description", "")
            source = article.get("source", "")
            published = article.get("published_at", "")[:16]
            url = article.get("url", "")

            # Sentiment classification
            text = (title + " " + description).lower()
            bull = sum(1 for w in BULLISH_WORDS if w in text)
            bear = sum(1 for w in BEARISH_WORDS if w in text)

            if bull > bear + 1:
                sentiment = "BULLISH"
            elif bear > bull + 1:
                sentiment = "BEARISH"
            else:
                sentiment = "NEUTRAL"

            news.append({
                "title": title,
                "source": source,
                "published": published,
                "sentiment": sentiment,
                "url": url,
            })

        return news

    except Exception as e:
        logger.warning(f"Marketaux fetch failed: {e}")
        return []


def get_global_context():
    """Get global market context from yfinance (quick check)."""
    try:
        import yfinance as yf

        tickers = {
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "Nikkei": "^N225",
            "Hang Seng": "^HSI",
            "Crude Oil": "CL=F",
            "USD/INR": "INR=X",
        }

        context = []
        for name, symbol in tickers.items():
            try:
                data = yf.download(symbol, period="2d", interval="1d", progress=False, auto_adjust=True)
                if len(data) >= 2:
                    import pandas as pd
                    if isinstance(data.columns, pd.MultiIndex):
                        data.columns = data.columns.get_level_values(0)
                    prev = float(data["Close"].iloc[-2])
                    curr = float(data["Close"].iloc[-1])
                    change_pct = round(((curr - prev) / prev) * 100, 2)
                    context.append({"name": name, "change_pct": change_pct, "price": round(curr, 2)})
            except Exception:
                continue

        return context
    except Exception as e:
        logger.warning(f"Global context failed: {e}")
        return []


def get_economic_events_today():
    """Get today's known economic events."""
    from market_intelligence import get_economic_calendar
    calendar = get_economic_calendar()
    today_events = [e for e in calendar if e.get("countdown") in ("TODAY", "TOMORROW")]
    return today_events


def generate_premarket_brief(vix: float = 15.0):
    """
    Generate the full pre-market intelligence report.
    Called at 08:45 AM or on demand.
    """
    init_brief_db()
    today = datetime.now().strftime("%Y-%m-%d")

    logger.info("Generating pre-market brief...")

    # 1. Fetch news
    news = fetch_marketaux_news(10)

    # 2. Global context
    global_ctx = get_global_context()

    # 3. Economic events
    events = get_economic_events_today()

    # 4. Calculate sentiment scores
    if news:
        bull_count = sum(1 for n in news if n["sentiment"] == "BULLISH")
        bear_count = sum(1 for n in news if n["sentiment"] == "BEARISH")
        neutral_count = sum(1 for n in news if n["sentiment"] == "NEUTRAL")
        total = len(news)
        sentiment_bull = round((bull_count / total) * 100, 1)
        sentiment_bear = round((bear_count / total) * 100, 1)
        sentiment_neutral = round((neutral_count / total) * 100, 1)
    else:
        sentiment_bull = sentiment_bear = sentiment_neutral = 33.3

    # 5. Determine market bias
    bias_reasons = []

    # Global markets influence
    us_markets = [g for g in global_ctx if g["name"] in ("S&P 500", "NASDAQ")]
    us_positive = sum(1 for m in us_markets if m["change_pct"] > 0.3)
    us_negative = sum(1 for m in us_markets if m["change_pct"] < -0.3)

    if us_positive > 0:
        us_pos_str = ", ".join(f"{m['name']} {m['change_pct']:+.1f}%" for m in us_markets if m["change_pct"] > 0)
        bias_reasons.append(f"US markets closed positive ({us_pos_str})")
    elif us_negative > 0:
        us_neg_str = ", ".join(f"{m['name']} {m['change_pct']:+.1f}%" for m in us_markets if m["change_pct"] < 0)
        bias_reasons.append(f"US markets closed negative ({us_neg_str})")

    # News sentiment influence
    if sentiment_bull > 50:
        bias_reasons.append("Positive news sentiment dominant")
    elif sentiment_bear > 50:
        bias_reasons.append("Negative news flow today")

    # VIX influence
    if vix < 14:
        bias_reasons.append(f"VIX low ({vix:.1f}) — stable conditions")
    elif vix > 20:
        bias_reasons.append(f"VIX elevated ({vix:.1f}) — caution warranted")

    # Events influence
    high_events = [e for e in events if e.get("impact") == "HIGH"]
    if high_events:
        bias_reasons.append(f"{len(high_events)} high-impact event(s): {', '.join(e['event'] for e in high_events[:2])}")

    # Final bias
    bull_signals = (sentiment_bull > 40) + (us_positive > 0) + (vix < 15)
    bear_signals = (sentiment_bear > 40) + (us_negative > 0) + (vix > 20)

    if bull_signals > bear_signals + 1:
        market_bias = "BULLISH"
    elif bear_signals > bull_signals + 1:
        market_bias = "BEARISH"
    else:
        market_bias = "NEUTRAL"

    if not bias_reasons:
        bias_reasons = ["No strong directional cues today"]

    # 6. Risk level
    risk_score = 0
    risk_reasons = []

    if vix >= 20:
        risk_score += 3
        risk_reasons.append(f"Elevated VIX ({vix:.1f})")
    elif vix >= 16:
        risk_score += 1

    if high_events:
        risk_score += 2 * len(high_events)
        risk_reasons.append(f"{len(high_events)} major event(s) today")

    if datetime.now().weekday() == 3:
        risk_score += 2
        risk_reasons.append("Options expiry day")

    if abs(sum(m["change_pct"] for m in us_markets)) > 2:
        risk_score += 2
        risk_reasons.append("Large global market moves overnight")

    if risk_score >= 6:
        risk_level = "EXTREME"
    elif risk_score >= 4:
        risk_level = "HIGH"
    elif risk_score >= 2:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    if not risk_reasons:
        risk_reasons = ["Normal conditions"]

    # 7. Market regime
    if vix >= 20:
        regime = "High Volatility"
    elif vix <= 13:
        regime = "Low Volatility"
    elif market_bias == "BULLISH":
        regime = "Trending Bullish"
    elif market_bias == "BEARISH":
        regime = "Trending Bearish"
    else:
        regime = "Range Bound"

    # 8. Watchlist (sectors in news)
    watchlist = []
    all_text = " ".join(n["title"].lower() for n in news)
    for sector in SECTORS:
        if sector in all_text:
            watchlist.append(sector.capitalize())
    if not watchlist:
        watchlist = ["Broad Market"]

    # 9. Trading guidance
    if risk_level in ("HIGH", "EXTREME"):
        guidance = "High risk day. Use smaller position sizes. Avoid overtrading. Watch event timings closely. Consider waiting for post-event clarity."
    elif regime == "High Volatility":
        guidance = "Volatile conditions expected. Wide stops recommended. Quick targets. Don't hold positions through major events."
    elif regime == "Range Bound":
        guidance = "Rangebound market expected. Look for mean-reversion setups. Avoid chasing breakouts. Patience is key."
    elif market_bias == "BULLISH":
        guidance = "Positive bias today. Look for dips to buy. Calls preferred. Maintain trailing stops on longs."
    elif market_bias == "BEARISH":
        guidance = "Negative bias today. Rally sell setups. Puts preferred. Protect existing long positions."
    else:
        guidance = "Mixed signals. Wait for clear setups. Don't force trades. Let the model guide entry timing."

    # 10. Build report
    report = {
        "date": today,
        "generated_at": datetime.now().strftime("%H:%M:%S"),
        "market_bias": market_bias,
        "bias_reasons": bias_reasons,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "sentiment": {"bull": sentiment_bull, "neutral": sentiment_neutral, "bear": sentiment_bear},
        "regime": regime,
        "guidance": guidance,
        "watchlist": watchlist[:5],
        "events": events[:5],
        "headlines": news[:5],
        "global_context": global_ctx,
    }

    # Store in database
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO premarket_briefs
            (date, generated_at, market_bias, bias_reasons, risk_level, risk_reasons,
             sentiment_bull, sentiment_neutral, sentiment_bear, regime, guidance,
             watchlist, events, headlines, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            today,
            report["generated_at"],
            market_bias,
            json.dumps(bias_reasons),
            risk_level,
            json.dumps(risk_reasons),
            sentiment_bull,
            sentiment_neutral,
            sentiment_bear,
            regime,
            guidance,
            json.dumps(watchlist),
            json.dumps(events[:5]),
            json.dumps([{"title": n["title"], "source": n["source"], "sentiment": n["sentiment"]} for n in news[:5]]),
            json.dumps(report),
        ))
        conn.commit()
        conn.close()
        logger.info(f"Pre-market brief saved: {market_bias} | Risk: {risk_level}")
    except Exception as e:
        logger.warning(f"Failed to save brief: {e}")

    # Cache locally
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(report, f, indent=2, default=str)
    except Exception:
        pass

    return report


def get_latest_brief():
    """Get the most recent pre-market brief (from cache or DB)."""
    # Try cache first
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                cached = json.load(f)
            if cached.get("date") == datetime.now().strftime("%Y-%m-%d"):
                return cached
        except Exception:
            pass

    # Fall back to DB
    try:
        init_brief_db()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT raw_data FROM premarket_briefs ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception:
        pass

    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    report = generate_premarket_brief(vix=15.8)

    print("\n" + "=" * 60)
    print("  JP.TRADES PRE-MARKET BRIEF")
    print("=" * 60)
    print(f"\n  Date: {report['date']} | Generated: {report['generated_at']}")
    print(f"\n  MARKET BIAS: {report['market_bias']}")
    for r in report['bias_reasons']:
        print(f"    - {r}")
    print(f"\n  RISK LEVEL: {report['risk_level']}")
    for r in report['risk_reasons']:
        print(f"    - {r}")
    print(f"\n  SENTIMENT: Bull {report['sentiment']['bull']:.0f}% | Neutral {report['sentiment']['neutral']:.0f}% | Bear {report['sentiment']['bear']:.0f}%")
    print(f"  REGIME: {report['regime']}")
    print(f"  WATCHLIST: {', '.join(report['watchlist'])}")
    print(f"\n  GUIDANCE: {report['guidance']}")
    print(f"\n  HEADLINES:")
    for h in report['headlines'][:3]:
        print(f"    [{h['sentiment']}] {h['title'][:70]}")
    print(f"\n  GLOBAL:")
    for g in report['global_context']:
        print(f"    {g['name']:12} {g['change_pct']:+.2f}%")
