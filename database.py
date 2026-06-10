import sqlite3
from config import DATABASE_PATH


class DatabaseManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.initialize_database()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def initialize_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # =====================================
        # Predictions Table
        # =====================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            prediction TEXT NOT NULL,
            confidence REAL NOT NULL
        )
        """)

        # =====================================
        # Results Table
        # =====================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER,
            actual_direction TEXT,
            correct INTEGER,
            FOREIGN KEY(prediction_id)
            REFERENCES predictions(id)
        )
        """)

        conn.commit()
        conn.close()

    # =====================================
    # Prediction Methods
    # =====================================

    def save_prediction(
        self,
        timestamp,
        symbol,
        price,
        prediction,
        confidence
    ):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO predictions
        (
            timestamp,
            symbol,
            price,
            prediction,
            confidence
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp,
            symbol,
            price,
            prediction,
            confidence
        ))

        prediction_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return prediction_id

    # =====================================
    # Result Methods
    # =====================================

    def save_result(
        self,
        prediction_id,
        actual_direction,
        correct
    ):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO results
        (
            prediction_id,
            actual_direction,
            correct
        )
        VALUES (?, ?, ?)
        """, (
            prediction_id,
            actual_direction,
            int(correct)
        ))

        conn.commit()
        conn.close()

    # =====================================
    # Statistics
    # =====================================

    def get_accuracy(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT
            COUNT(*),
            SUM(correct)
        FROM results
        """)

        row = cursor.fetchone()

        conn.close()

        total = row[0] or 0
        correct = row[1] or 0

        if total == 0:
            return 0.0

        return round((correct / total) * 100, 2)


if __name__ == "__main__":
    db = DatabaseManager()

    print("Database created successfully.")
    print(f"Database location: {DATABASE_PATH}")