"""
JPTrades - Market Intelligence Module
Provides market news, economic calendar, risk assessment, and regime detection.
Uses free RSS feeds — no API keys required.

CRITICAL: News NEVER overrides model signals. It is informational only.
"""

import logging
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = str(BASE_DIR / "alphafx.db")

# ═══════════════════════════════════════════════════════════════════════════════
# NEWS FETCHING (RSS Feeds)
# ═══════════════════════════════════════════════════════════════════════════════

RSS_FEEDS = [
    {"url": "https://www.moneycontrol.com/rss/marketreports.xml", "source": "MoneyControl"},
    {"url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "source": "ET Markets"},
    {"url": "https://www.livemint.com/rss/markets", "source": "LiveMint"},
]

BULLISH_KEYWORDS = [
    "rally", "surge", "gain", "bull", "up", "rise", "high", "record",
    "positive", "growth", "recovery", "boom", "strong", "buying"
]
BEARISH_KEYWORDS = [
    "crash", "fall", "drop", "bear", "down", "low", "selloff", "sell-off",
    "negative", "recession", "fear", "weak", "decline", "correction", "plunge"
]
HIGH_IMPACT_KEYWORDS = [
    "rbi", "fed", "rate", "inflation", "cpi", "gdp", "crisis", "war",
    "election", "budget", "policy", "emergency", "crash", "circuit"
]


def fetch_market_news(max_items=10):
    """
    Fetch latest market news from RSS feeds.
    Returns list of news items with sentiment classification.
    """
    try:
        import feedparser
    except ImportError:
        logger.warning("feedparser not installed. Run: pip install feedparser")
        return []

    all_news = []

    for feed_config in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_config["url"])
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated", ""))
                summary = entry.get("summary", entry.get("description", ""))

                # Clean HTML from summary
                summary = re.sub(r"<[^>]+>", "", summary or "")[:200]

                # Classify sentiment
                text_lower = (title + " " + summary).lower()
                bull_score = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
                bear_score = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)

                if bull_score > bear_score + 1:
                    sentiment = "BULLISH"
                elif bear_score > bull_score + 1:
                    sentiment = "BEARISH"
                else:
                    sentiment = "NEUTRAL"

                # Impact level
                impact_score = sum(1 for kw in HIGH_IMPACT_KEYWORDS if kw in text_lower)
                if impact_score >= 2:
                    impact = "HIGH"
                elif impact_score >= 1:
                    impact = "MEDIUM"
                else:
                    impact = "LOW"

                all_news.append({
                    "title": title,
                    "source": feed_config["source"],
                    "published": published[:25] if published else "",
                    "summary": summary,
                    "sentiment": sentiment,
                    "impact": impact,
                    "link": link,
                })
        except Exception as e:
            logger.warning(f"Failed to fetch {feed_config['source']}: {e}")
            continue

    # Sort by most recent and limit
    return all_news[:max_items]


# ═══════════════════════════════════════════════════════════════════════════════
# ECONOMIC CALENDAR (Static + Dynamic)
# ═══════════════════════════════════════════════════════════════════════════════

def get_economic_calendar():
    """
    Returns upcoming economic events (static schedule + known dates).
    """
    now = datetime.now()
    today = now.date()

    # Known recurring events (approximate schedule)
    events = [
        {"event": "RBI MPC Decision", "date": "2026-06-18", "time": "10:00", "country": "IN", "impact": "HIGH", "category": "Interest Rate"},
        {"event": "India CPI Inflation", "date": "2026-06-12", "time": "17:30", "country": "IN", "impact": "HIGH", "category": "Inflation"},
        {"event": "India WPI Data", "date": "2026-06-16", "time": "14:00", "country": "IN", "impact": "MEDIUM", "category": "Inflation"},
        {"event": "US CPI Data", "date": "2026-06-11", "time": "18:00", "country": "US", "impact": "HIGH", "category": "Inflation"},
        {"event": "US Fed Rate Decision", "date": "2026-06-18", "time": "23:30", "country": "US", "impact": "HIGH", "category": "Interest Rate"},
        {"event": "India GDP Q4", "date": "2026-06-30", "time": "17:30", "country": "IN", "impact": "HIGH", "category": "GDP"},
        {"event": "India PMI Manufacturing", "date": "2026-07-01", "time": "10:30", "country": "IN", "impact": "MEDIUM", "category": "PMI"},
        {"event": "US Non-Farm Payrolls", "date": "2026-07-03", "time": "18:00", "country": "US", "impact": "HIGH", "category": "Employment"},
        {"event": "Weekly Options Expiry", "date": str(get_next_thursday(today)), "time": "15:30", "country": "IN", "impact": "MEDIUM", "category": "Expiry"},
        {"event": "Monthly F&O Expiry", "date": str(get_last_thursday_of_month(today)), "time": "15:30", "country": "IN", "impact": "HIGH", "category": "Expiry"},
    ]

    # Filter upcoming events (next 14 days)
    upcoming = []
    for evt in events:
        try:
            evt_date = datetime.strptime(evt["date"], "%Y-%m-%d").date()
            if today <= evt_date <= today + timedelta(days=14):
                days_away = (evt_date - today).days
                if days_away == 0:
                    countdown = "TODAY"
                elif days_away == 1:
                    countdown = "TOMORROW"
                else:
                    countdown = f"In {days_away} days"

                upcoming.append({**evt, "countdown": countdown, "days_away": days_away})
        except Exception:
            continue

    return sorted(upcoming, key=lambda x: x["days_away"])


def get_next_thursday(from_date):
    """Get the next Thursday from a given date."""
    days_ahead = 3 - from_date.weekday()  # Thursday = 3
    if days_ahead <= 0:
        days_ahead += 7
    return from_date + timedelta(days=days_ahead)


def get_last_thursday_of_month(from_date):
    """Get the last Thursday of the current month."""
    import calendar
    year, month = from_date.year, from_date.month
    last_day = calendar.monthrange(year, month)[1]
    last_date = from_date.replace(day=last_day)
    while last_date.weekday() != 3:  # Thursday
        last_date -= timedelta(days=1)
    return last_date


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET RISK ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_market_risk(vix: float, nifty_change_pct: float, calendar_events: list):
    """
    Calculate today's market risk level.

    Factors:
    - VIX level
    - Today's volatility
    - Upcoming high-impact events
    - Options expiry proximity

    Returns dict with level, score, reasons.
    """
    score = 0
    reasons = []

    # VIX factor
    if vix >= 25:
        score += 4
        reasons.append(f"VIX very high ({vix:.1f})")
    elif vix >= 20:
        score += 3
        reasons.append(f"VIX elevated ({vix:.1f})")
    elif vix >= 16:
        score += 1
        reasons.append(f"VIX moderate ({vix:.1f})")

    # Intraday volatility
    if abs(nifty_change_pct) > 1.5:
        score += 3
        reasons.append(f"High intraday move ({nifty_change_pct:+.2f}%)")
    elif abs(nifty_change_pct) > 0.8:
        score += 1
        reasons.append(f"Moderate move ({nifty_change_pct:+.2f}%)")

    # Upcoming events today
    today_events = [e for e in calendar_events if e.get("countdown") == "TODAY"]
    high_events_today = [e for e in today_events if e.get("impact") == "HIGH"]
    if high_events_today:
        score += 3
        reasons.append(f"{len(high_events_today)} high-impact event(s) today")
    elif today_events:
        score += 1
        reasons.append(f"{len(today_events)} event(s) today")

    # Events tomorrow
    tomorrow_events = [e for e in calendar_events if e.get("countdown") == "TOMORROW" and e.get("impact") == "HIGH"]
    if tomorrow_events:
        score += 1
        reasons.append("High-impact event tomorrow")

    # Expiry day
    if datetime.now().weekday() == 3:  # Thursday
        score += 2
        reasons.append("Options expiry day (high gamma)")

    # Determine level
    if score >= 7:
        level = "EXTREME"
    elif score >= 5:
        level = "HIGH"
    elif score >= 3:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "level": level,
        "score": score,
        "reasons": reasons,
        "factors": {
            "vix": vix,
            "volatility": abs(nifty_change_pct),
            "events_today": len(today_events),
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET REGIME DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

def detect_market_regime(vix: float, nifty_change_pct: float,
                         ema_diff: float = 0, rsi: float = 50):
    """
    Classify current market regime.
    Uses VIX, trend indicators, and momentum.
    """
    if vix >= 22:
        regime = "High Volatility"
        reasoning = f"VIX at {vix:.1f} indicates fear/uncertainty"
    elif vix <= 12:
        regime = "Low Volatility"
        reasoning = f"VIX at {vix:.1f} indicates calm/complacency"
    elif ema_diff > 30:
        regime = "Trending Bullish"
        reasoning = f"EMA20 above EMA50 by {ema_diff:.0f} pts, strong uptrend"
    elif ema_diff < -30:
        regime = "Trending Bearish"
        reasoning = f"EMA20 below EMA50 by {abs(ema_diff):.0f} pts, strong downtrend"
    elif abs(nifty_change_pct) < 0.3 and vix < 16:
        regime = "Range Bound"
        reasoning = f"Low volatility ({nifty_change_pct:+.2f}%) with VIX at {vix:.1f}"
    elif nifty_change_pct > 0.5:
        regime = "Trending Bullish"
        reasoning = f"Positive momentum ({nifty_change_pct:+.2f}%) with moderate VIX"
    elif nifty_change_pct < -0.5:
        regime = "Trending Bearish"
        reasoning = f"Negative momentum ({nifty_change_pct:+.2f}%)"
    else:
        regime = "Range Bound"
        reasoning = f"No clear direction, VIX={vix:.1f}"

    return {"regime": regime, "reasoning": reasoning}


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE QUALITY ASSESSMENT
# ═══════════════════════════════════════════════════════════════════════════════

def assess_trade_quality(signal: str, confidence: float, risk_level: str,
                         regime: str, vix: float):
    """
    Assess trade quality based on signal + market context.
    Score 1-10. Signal is NEVER changed — only quality assessment.
    """
    score = 5  # Base score

    # Confidence boost
    if confidence >= 70:
        score += 2
    elif confidence >= 65:
        score += 1

    # Risk penalty
    if risk_level == "EXTREME":
        score -= 3
    elif risk_level == "HIGH":
        score -= 2
    elif risk_level == "MEDIUM":
        score -= 1

    # Regime alignment
    if signal == "BULLISH" and regime == "Trending Bullish":
        score += 1
    elif signal == "BEARISH" and regime == "Trending Bearish":
        score += 1
    elif regime == "High Volatility":
        score -= 1

    # VIX bonus for put buying in high VIX
    if signal == "BEARISH" and vix >= 18:
        score += 1

    # Clamp
    score = max(1, min(10, score))

    # Reason
    reasons = []
    if confidence >= 70:
        reasons.append("High model confidence")
    if risk_level in ("HIGH", "EXTREME"):
        reasons.append(f"{risk_level} event risk today")
    if regime == "High Volatility":
        reasons.append("Volatile market conditions")
    if not reasons:
        reasons.append("Normal market conditions")

    return {"score": score, "reasons": reasons}


# ═══════════════════════════════════════════════════════════════════════════════
# FULL INTELLIGENCE REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def get_market_intelligence(vix: float = 15.0, nifty_change_pct: float = 0.0,
                            signal: str = "NO TRADE", confidence: float = 0.0,
                            ema_diff: float = 0.0):
    """
    Generate complete market intelligence report.
    Returns dict with all sections for dashboard display.
    """
    # News
    news = fetch_market_news(8)

    # Calendar
    calendar = get_economic_calendar()

    # Risk
    risk = calculate_market_risk(vix, nifty_change_pct, calendar)

    # Regime
    regime = detect_market_regime(vix, nifty_change_pct, ema_diff)

    # Trade quality
    quality = assess_trade_quality(signal, confidence, risk["level"], regime["regime"], vix)

    return {
        "news": news,
        "calendar": calendar[:6],
        "risk": risk,
        "regime": regime,
        "trade_quality": quality,
        "generated_at": datetime.now().strftime("%H:%M:%S"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DATA COLLECTION (for future research)
# ═══════════════════════════════════════════════════════════════════════════════

def store_intelligence_snapshot(intel: dict):
    """Store intelligence data for future correlation analysis."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intelligence_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                risk_level TEXT,
                risk_score INTEGER,
                regime TEXT,
                trade_quality INTEGER,
                news_sentiment TEXT,
                events_today INTEGER
            )
        """)

        # Aggregate news sentiment
        news = intel.get("news", [])
        bull_count = sum(1 for n in news if n["sentiment"] == "BULLISH")
        bear_count = sum(1 for n in news if n["sentiment"] == "BEARISH")
        if bull_count > bear_count:
            net_sentiment = "BULLISH"
        elif bear_count > bull_count:
            net_sentiment = "BEARISH"
        else:
            net_sentiment = "NEUTRAL"

        cursor.execute("""
            INSERT INTO intelligence_log (timestamp, risk_level, risk_score, regime,
                trade_quality, news_sentiment, events_today)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            intel["risk"]["level"],
            intel["risk"]["score"],
            intel["regime"]["regime"],
            intel["trade_quality"]["score"],
            net_sentiment,
            intel["risk"]["factors"]["events_today"],
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to store intelligence snapshot: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    intel = get_market_intelligence(vix=16.0, nifty_change_pct=-0.5, signal="BULLISH", confidence=68.0)

    print("\n=== MARKET INTELLIGENCE ===")
    print(f"\nRisk: {intel['risk']['level']} (score {intel['risk']['score']})")
    for r in intel['risk']['reasons']:
        print(f"  - {r}")

    print(f"\nRegime: {intel['regime']['regime']}")
    print(f"  {intel['regime']['reasoning']}")

    print(f"\nTrade Quality: {intel['trade_quality']['score']}/10")

    print(f"\nNews ({len(intel['news'])} items):")
    for n in intel['news'][:3]:
        print(f"  [{n['sentiment']}] {n['title'][:60]}... ({n['source']})")

    print(f"\nCalendar ({len(intel['calendar'])} events):")
    for e in intel['calendar'][:3]:
        print(f"  {e['countdown']:12} | {e['event']} [{e['impact']}]")
