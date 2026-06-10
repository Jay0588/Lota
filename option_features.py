"""
JPTrades - Option Features via Angel One SmartAPI
Fetches live ATM CE/PE prices for NIFTY options.
Returns None gracefully if API is unavailable.
"""

import os
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


def get_option_features():
    """
    Fetch live NIFTY ATM option data from Angel One SmartAPI.
    Returns dict with ATM_STRIKE, CE_LTP, PE_LTP, CE_PE_RATIO or None on failure.
    """
    try:
        import pyotp
        from dotenv import load_dotenv
        from SmartApi import SmartConnect

        load_dotenv()

        api_key = os.getenv("ANGEL_API_KEY")
        client_code = os.getenv("ANGEL_CLIENT_CODE")
        pin = os.getenv("ANGEL_PIN")
        totp_secret = os.getenv("ANGEL_TOTP_SECRET")

        if not all([api_key, client_code, pin, totp_secret]):
            logger.warning("Angel One credentials missing in .env")
            return None

        smart = SmartConnect(api_key=api_key)
        session = smart.generateSession(client_code, pin, pyotp.TOTP(totp_secret).now())

        if not session or session.get("status") is False:
            logger.warning(f"Angel One login failed: {session}")
            return None

        # Get live NIFTY price
        nifty_resp = smart.ltpData("NSE", "NIFTY", "99926000")
        if not nifty_resp or not nifty_resp.get("data"):
            logger.warning("Could not fetch NIFTY LTP from Angel One")
            return None

        nifty_price = nifty_resp["data"]["ltp"]
        atm = round(nifty_price / 50) * 50

        # Load instruments
        instruments_path = BASE_DIR / "instruments.csv"
        if not instruments_path.exists():
            logger.warning("instruments.csv not found, skipping options")
            return None

        df = pd.read_csv(str(instruments_path), low_memory=False)

        options = df[
            (df["name"] == "NIFTY") &
            (df["instrumenttype"].astype(str).str.contains("OPT"))
        ].copy()

        if options.empty:
            logger.warning("No NIFTY options found in instruments.csv")
            return None

        options["strike"] = pd.to_numeric(options["strike"], errors="coerce") / 100

        atm_options = options[options["strike"] == atm].copy()
        if atm_options.empty:
            logger.warning(f"No ATM options found for strike {atm}")
            return None

        atm_options["expiry"] = pd.to_datetime(
            atm_options["expiry"], format="%d%b%Y", errors="coerce"
        )
        atm_options = atm_options.dropna(subset=["expiry"])
        atm_options = atm_options.sort_values("expiry")

        nearest_expiry = atm_options.iloc[0]["expiry"]
        atm_options = atm_options[atm_options["expiry"] == nearest_expiry]

        ce_rows = atm_options[atm_options["symbol"].str.endswith("CE")]
        pe_rows = atm_options[atm_options["symbol"].str.endswith("PE")]

        if ce_rows.empty or pe_rows.empty:
            logger.warning("CE or PE contract not found for ATM strike")
            return None

        ce = ce_rows.iloc[0]
        pe = pe_rows.iloc[0]

        ce_ltp = smart.ltpData("NFO", ce["symbol"], str(ce["token"]))
        pe_ltp = smart.ltpData("NFO", pe["symbol"], str(pe["token"]))

        if not ce_ltp.get("data") or not pe_ltp.get("data"):
            logger.warning("Could not fetch CE/PE LTP from Angel One")
            return None

        ce_price = ce_ltp["data"]["ltp"]
        pe_price = pe_ltp["data"]["ltp"]

        return {
            "ATM_STRIKE": atm,
            "CE_LTP": ce_price,
            "PE_LTP": pe_price,
            "CE_PE_RATIO": ce_price / pe_price if pe_price > 0 else 1.0
        }

    except ImportError as e:
        logger.warning(f"Missing package for options: {e}")
        return None
    except Exception as e:
        logger.warning(f"Option features failed: {e}")
        return None


def get_multi_strike_prices(direction: str, atm_strike: int):
    """
    Fetch ITM, ATM, and OTM option prices for 3-tier trade recommendations.
    NIFTY strike gap = 50 points. Lot size = 25.

    For BULLISH (CE):
        ITM = ATM - 200 (Low Risk, expensive, high delta)
        ATM = ATM strike (Medium Risk)
        OTM = ATM + 300 (High Risk, cheap, low delta)

    For BEARISH (PE):
        ITM = ATM + 200 (Low Risk, expensive, high delta)
        ATM = ATM strike (Medium Risk)
        OTM = ATM - 300 (High Risk, cheap, low delta)

    Returns list of dicts with full trade setup or empty list on failure.
    """
    try:
        import pyotp
        from dotenv import load_dotenv
        from SmartApi import SmartConnect

        load_dotenv()

        api_key = os.getenv("ANGEL_API_KEY")
        client_code = os.getenv("ANGEL_CLIENT_CODE")
        pin = os.getenv("ANGEL_PIN")
        totp_secret = os.getenv("ANGEL_TOTP_SECRET")

        if not all([api_key, client_code, pin, totp_secret]):
            return []

        smart = SmartConnect(api_key=api_key)
        smart.generateSession(client_code, pin, pyotp.TOTP(totp_secret).now())

        instruments_path = BASE_DIR / "instruments.csv"
        if not instruments_path.exists():
            return []

        df = pd.read_csv(str(instruments_path), low_memory=False)
        options = df[
            (df["name"] == "NIFTY") &
            (df["instrumenttype"].astype(str).str.contains("OPT"))
        ].copy()

        if options.empty:
            return []

        options["strike"] = pd.to_numeric(options["strike"], errors="coerce") / 100

        suffix = "CE" if direction == "CE" else "PE"

        # ITM / ATM / OTM strikes
        if direction == "CE":
            strikes_config = [
                {"strike": atm_strike - 200, "label": "ITM", "risk": "LOW RISK", "tier": "low"},
                {"strike": atm_strike, "label": "ATM", "risk": "MEDIUM RISK", "tier": "medium"},
                {"strike": atm_strike + 300, "label": "OTM", "risk": "HIGH RISK", "tier": "high"},
            ]
        else:
            strikes_config = [
                {"strike": atm_strike + 200, "label": "ITM", "risk": "LOW RISK", "tier": "low"},
                {"strike": atm_strike, "label": "ATM", "risk": "MEDIUM RISK", "tier": "medium"},
                {"strike": atm_strike - 300, "label": "OTM", "risk": "HIGH RISK", "tier": "high"},
            ]

        results = []
        lot_size = 25  # NIFTY lot size

        for config in strikes_config:
            strike = config["strike"]
            strike_opts = options[options["strike"] == strike].copy()
            if strike_opts.empty:
                continue

            strike_opts["expiry"] = pd.to_datetime(
                strike_opts["expiry"], format="%d%b%Y", errors="coerce"
            )
            strike_opts = strike_opts.dropna(subset=["expiry"]).sort_values("expiry")
            if strike_opts.empty:
                continue

            nearest_expiry = strike_opts.iloc[0]["expiry"]
            strike_opts = strike_opts[strike_opts["expiry"] == nearest_expiry]

            contract_rows = strike_opts[strike_opts["symbol"].str.endswith(suffix)]
            if contract_rows.empty:
                continue

            contract = contract_rows.iloc[0]
            try:
                ltp_resp = smart.ltpData("NFO", contract["symbol"], str(contract["token"]))
                if not ltp_resp or not ltp_resp.get("data"):
                    continue
                price = ltp_resp["data"]["ltp"]
                if price <= 0:
                    continue
            except Exception:
                continue

            # Calculate trade parameters
            capital_required = round(price * lot_size, 2)

            # SL and targets — realistic for 15-30 min holds
            if config["tier"] == "low":
                sl_pct = 0.05       # 5% SL (tight for ITM)
                tgt1_pct = 0.06     # 6% target 1 (achievable in 15 min)
                tgt2_pct = 0.10     # 10% target 2 (stretch)
            elif config["tier"] == "medium":
                sl_pct = 0.07       # 7% SL
                tgt1_pct = 0.08     # 8% target 1
                tgt2_pct = 0.12     # 12% target 2
            else:  # high (OTM moves faster in %)
                sl_pct = 0.10       # 10% SL
                tgt1_pct = 0.12     # 12% target 1
                tgt2_pct = 0.20     # 20% target 2

            sl_price = round(price * (1 - sl_pct), 2)
            target1 = round(price * (1 + tgt1_pct), 2)
            target2 = round(price * (1 + tgt2_pct), 2)
            risk_amount = round((price - sl_price) * lot_size, 2)
            reward_amount = round((target1 - price) * lot_size, 2)
            rr_ratio = round(reward_amount / risk_amount, 2) if risk_amount > 0 else 0

            # Budget category
            if capital_required <= 5000:
                budget = "2k-5k"
            elif capital_required <= 10000:
                budget = "5k-10k"
            else:
                budget = "10k+"

            results.append({
                "strike": int(strike),
                "price": price,
                "label": config["label"],
                "risk_level": config["risk"],
                "tier": config["tier"],
                "contract": f"{int(strike)}{suffix}",
                "symbol": contract["symbol"],
                "capital_required": capital_required,
                "budget": budget,
                "sl_price": sl_price,
                "target1": target1,
                "target2": target2,
                "entry_low": round(price * 0.98, 2),
                "entry_high": round(price * 1.02, 2),
                "risk_amount": risk_amount,
                "reward_amount": reward_amount,
                "rr_ratio": rr_ratio,
                "lot_size": lot_size,
            })

        return results

    except Exception as e:
        logger.warning(f"Multi-strike fetch failed: {e}")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    features = get_option_features()

    if features:
        print("\n=== OPTION FEATURES ===\n")
        for key, value in features.items():
            print(f"{key}: {value}")
    else:
        print("Option features unavailable.")
