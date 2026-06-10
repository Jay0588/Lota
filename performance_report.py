import sqlite3
import pandas as pd

conn = sqlite3.connect(
    "alphafx.db"
)

df = pd.read_sql(
    """
    SELECT *
    FROM signals
    """,
    conn
)

conn.close()

print("\n========================")
print("ALPHAFX PERFORMANCE")
print("========================")

if len(df) == 0:

    print("No signals found.")
    quit()

completed = df[
    df["outcome"].notna()
]

total_signals = len(df)

wins = len(
    completed[
        completed["outcome"] == "WIN"
    ]
)

losses = len(
    completed[
        completed["outcome"] == "LOSS"
    ]
)

evaluated = wins + losses

win_rate = (
    wins / evaluated * 100
    if evaluated > 0
    else 0
)

avg_confidence = (
    df["confidence"]
    .mean()
)

bullish = len(
    df[
        df["signal"] == "BULLISH"
    ]
)

bearish = len(
    df[
        df["signal"] == "BEARISH"
    ]
)

print(
    f"Total Signals     : {total_signals}"
)

print(
    f"Evaluated Signals : {evaluated}"
)

print(
    f"Wins              : {wins}"
)

print(
    f"Losses            : {losses}"
)

print(
    f"Win Rate          : {win_rate:.2f}%"
)

print(
    f"Avg Confidence    : {avg_confidence:.2f}%"
)

print(
    f"Bullish Signals   : {bullish}"
)

print(
    f"Bearish Signals   : {bearish}"
)
