import sqlite3

conn = sqlite3.connect("database/trading.db")

cursor = conn.cursor()

cursor.execute(
    "SELECT * FROM predictions"
)

rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()