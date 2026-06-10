"""
JPTrades - Single Prediction
Run this to get a one-shot prediction without the web dashboard.
"""

import joblib
import pandas as pd

from market_data import MarketData
from config import MODEL_FILE
from signal_engine import classify_signal
from trade_generator import generate_trade
from option_features import get_option_features

FEATURES_WITH_OPTIONS = [
    "RETURN_6", "EMA_DIFF", "MACD_SIGNAL", "VIX_RETURN_3", "MINUTE",
    "EMA50", "BB_UPPER", "BANK_RETURN_1", "EMA20", "RETURN_3", "MACD",
    "ATM_STRIKE", "CE_LTP", "PE_LTP", "CE_PE_RATIO",
]

FEATURES_WITHOUT_OPTIONS = [
    "RETURN_6", "EMA_DIFF", "MACD_SIGNAL", "VIX_RETURN_3", "MINUTE",
    "EMA50", "BB_UPPER", "BANK_RETURN_1", "EMA20", "RETURN_3", "MACD",
]


def main():
    print("=" * 50)
    print("  JPTrades - NIFTY Signal Prediction")
    print("=" * 50)

    # Load model
    print("\nLoading model...")
    if not MODEL_FILE.exists():
        print("ERROR: Model not found! Run train_model.py first.")
        return

    model = joblib.load(MODEL_FILE)

    # Load market data
    print("Fetching market data...")
    md = MarketData()
    data = md.get_processed_data()
    latest = data.iloc[-1]
    latest_dict = latest.to_dict()

    # Try options
    print("Fetching option features...")
    option_data = get_option_features()
    has_options = option_data is not None

    if has_options:
        latest_dict["ATM_STRIKE"] = option_data["ATM_STRIKE"]
        latest_dict["CE_LTP"] = option_data["CE_LTP"]
        latest_dict["PE_LTP"] = option_data["PE_LTP"]
        latest_dict["CE_PE_RATIO"] = option_data["CE_PE_RATIO"]
        print("  Options loaded successfully")
    else:
        print("  Options unavailable, using base features")

    # Determine features
    model_n_features = model.n_features_in_ if hasattr(model, 'n_features_in_') else None
    if model_n_features == len(FEATURES_WITH_OPTIONS) and has_options:
        features = FEATURES_WITH_OPTIONS
    elif model_n_features == len(FEATURES_WITHOUT_OPTIONS):
        features = FEATURES_WITHOUT_OPTIONS
    else:
        features = FEATURES_WITH_OPTIONS if has_options else FEATURES_WITHOUT_OPTIONS

    # Predict
    X = pd.DataFrame([{f: latest_dict.get(f, 0) for f in features}], columns=features)
    prediction = model.predict(X)[0]
    probabilities = model.predict_proba(X)[0]
    up_probability = float(probabilities[1]) if len(probabilities) > 1 else float(probabilities[0])
    down_probability = 1.0 - up_probability

    # Classify
    signal = classify_signal(up_probability)
    trade = generate_trade(signal["signal"], signal["confidence"])

    # Display
    print("\n" + "=" * 50)
    print(f"  NIFTY:      {latest['Close']:.2f}")
    print(f"  BANKNIFTY:  {latest['BANK_CLOSE']:.2f}")
    print(f"  VIX:        {latest['VIX_CLOSE']:.2f}")
    print(f"  RSI:        {latest['RSI']:.2f}")
    print("=" * 50)
    print(f"\n  SIGNAL:     {signal['signal']}")
    print(f"  CONFIDENCE: {signal['confidence']}%")
    print(f"  UP Prob:    {up_probability*100:.2f}%")
    print(f"  DOWN Prob:  {down_probability*100:.2f}%")
    print("\n" + "-" * 50)
    print(f"  TRADE:      {trade['trade']}")
    print(f"  RISK:       {trade['risk']}")
    print(f"  STOP LOSS:  {trade['sl']}")
    print(f"  TARGET:     {trade['target']}")

    if has_options:
        print(f"\n  ATM STRIKE: {option_data['ATM_STRIKE']}")
        print(f"  CE PRICE:   {option_data['CE_LTP']}")
        print(f"  PE PRICE:   {option_data['PE_LTP']}")
        print(f"  CE/PE:      {option_data['CE_PE_RATIO']:.2f}")

    print("=" * 50)


if __name__ == "__main__":
    main()
