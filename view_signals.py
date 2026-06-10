import sqlite3
import pandas as pd

conn = sqlite3.connect(
    "alphafx.db"
)

df = pd.read_sql(
    """
    SELECT *
    FROM signals
    ORDER BY id DESC
    """,
    conn
)

print("\n===== SIGNAL HISTORY =====\n")

print(df.head(20))

conn.close()