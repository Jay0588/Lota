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

best_accuracy = 0
best_params = None

estimators_list = [100, 200, 300, 500]
learning_rates = [0.01, 0.05, 0.1]
depths = [2, 3, 4]

total_tests = (
    len(estimators_list)
    * len(learning_rates)
    * len(depths)
)

current_test = 0

for estimators in estimators_list:

    for lr in learning_rates:

        for depth in depths:

            current_test += 1

            print(
                f"\n[{current_test}/{total_tests}] "
                f"n_estimators={estimators} "
                f"learning_rate={lr} "
                f"max_depth={depth}"
            )

            model = GradientBoostingClassifier(
                n_estimators=estimators,
                learning_rate=lr,
                max_depth=depth,
                random_state=42
            )

            model.fit(
                X_train,
                y_train
            )

            predictions = model.predict(
                X_test
            )

            accuracy = accuracy_score(
                y_test,
                predictions
            )

            print(
                f"Accuracy: {accuracy*100:.2f}%"
            )

            if accuracy > best_accuracy:

                best_accuracy = accuracy

                best_params = {
                    "n_estimators": estimators,
                    "learning_rate": lr,
                    "max_depth": depth
                }

print("\n========================")
print("BEST PARAMETERS")
print("========================")

print(best_params)

print(
    f"\nBest Accuracy: "
    f"{best_accuracy*100:.2f}%"
)