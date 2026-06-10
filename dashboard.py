from market_data import MarketData
from option_features import get_option_features
from signal_logger import log_signal

import joblib
import pandas as pd

from config import MODEL_FILE

FEATURES = [
    "RSI",
    "EMA20",
    "EMA50",
    "EMA200",
    "EMA_DIFF",
    "PRICE_EMA20",
    "MACD",
    "MACD_SIGNAL",
    "MACD_HIST",
    "ATR",
    "BB_UPPER",
    "BB_LOWER",
    "BB_WIDTH",
    "RETURN_1",
    "RETURN_3",
    "RETURN_6",
    "BANK_CLOSE",
    "BANK_RETURN_1",
    "BANK_RETURN_3",
    "VIX_CLOSE",
    "VIX_RETURN_1",
    "VIX_RETURN_3",
    "HOUR",
    "MINUTE"
]


def main():

    print("Loading model...")

    model = joblib.load(MODEL_FILE)

    md = MarketData()

    data = md.get_processed_data()

    latest = data.iloc[-1]

    X = pd.DataFrame(
        [latest[FEATURES]],
        columns=FEATURES
    )

    prediction = model.predict(X)[0]

    probabilities = (
        model.predict_proba(X)[0]
    )

    confidence = (
        max(probabilities) * 100
    )

    signal = (
        "BULLISH"
        if prediction == 1
        else "BEARISH"
    )

    option_data = (
        get_option_features()
    )

    print("\n========================")
    print("JPTrades LIVE")
    print("========================")

    print(
        f"NIFTY       : {latest['Close']:.2f}"
    )

    print(
        f"BANKNIFTY   : {latest['BANK_CLOSE']:.2f}"
    )

    print(
        f"VIX         : {latest['VIX_CLOSE']:.2f}"
    )

    print("\nMODEL")

    print(
        f"Signal      : {signal}"
    )

    print(
        f"Confidence  : {confidence:.2f}%"
    )

    print("\nOPTIONS")

    print(
        f"ATM STRIKE  : {option_data['ATM_STRIKE']}"
    )

    print(
        f"CE PRICE    : {option_data['CE_LTP']}"
    )

    print(
        f"PE PRICE    : {option_data['PE_LTP']}"
    )

    print(
        f"CE/PE RATIO : {option_data['CE_PE_RATIO']:.2f}"
    )

    # SAVE SIGNAL

    try:

        log_signal(
            float(latest["Close"]),
            signal,
            float(confidence),
            float(option_data["CE_LTP"]),
            float(option_data["PE_LTP"])
        )

        print("\nSignal saved.")

    except Exception as e:

        print(
            "\nFailed to save signal:"
        )

        print(e)


if __name__ == "__main__":
    main()