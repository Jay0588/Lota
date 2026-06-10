from market_data import MarketData
from config import PREDICTION_HORIZON

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

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
    "ATM_STRIKE",
    "CE_LTP",
    "PE_LTP",
    "CE_PE_RATIO",
    "HOUR",
    "MINUTE"
]

print("Loading data...")

md = MarketData()
data = md.get_processed_data()

future_close = data["Close"].shift(-PREDICTION_HORIZON)

data["TARGET"] = (
    future_close > data["Close"]
).astype(int)

data = data.dropna()

X = data[FEATURES]
y = data["TARGET"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    shuffle=False
)

model = GradientBoostingClassifier(
    n_estimators=200,
    random_state=42
)

print("Training model...")

model.fit(X_train, y_train)

predictions = model.predict(X_test)
probabilities = model.predict_proba(X_test)

overall_accuracy = accuracy_score(
    y_test,
    predictions
)

print("\n===== RESULTS =====")
print(f"Overall Accuracy: {overall_accuracy*100:.2f}%")
print(f"Total Signals: {len(y_test)}")

thresholds = [0.60, 0.65, 0.70]

for threshold in thresholds:

    filtered_actual = []
    filtered_pred = []

    for actual, pred, prob in zip(
        y_test,
        predictions,
        probabilities
    ):

        confidence = max(prob)

        if confidence >= threshold:
            filtered_actual.append(actual)
            filtered_pred.append(pred)

    if len(filtered_actual) == 0:
        print(f"\n{int(threshold*100)}%+ Confidence")
        print("Signals: 0")
        continue

    acc = accuracy_score(
        filtered_actual,
        filtered_pred
    )

    print(f"\n{int(threshold*100)}%+ Confidence")
    print(f"Signals: {len(filtered_actual)}")
    print(f"Accuracy: {acc*100:.2f}%")