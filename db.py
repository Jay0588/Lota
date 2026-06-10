"""
JPTrades - Database Abstraction Layer
Currently uses SQLite. Designed for future PostgreSQL migration.
All DB access should go through this module.
"""

import sqlite3
import os
import logging
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # "sqlite" or "postgresql" in future
DB_FILE = str(Path(__file__).resolve().parent / "alphafx.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_FILE}")


@contextmanager
def get_connection():
    """
    Get a database connection. Use as context manager:

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)

    Currently SQLite. Will be swapped to psycopg2 for PostgreSQL.
    """
    if DB_TYPE == "sqlite":
        conn = sqlite3.connect(DB_FILE, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        conn.execute("PRAGMA busy_timeout=5000")  # Wait up to 5s if locked
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        # Future: PostgreSQL via psycopg2
        raise NotImplementedError("PostgreSQL support not yet implemented")


def execute(query: str, params: tuple = ()):
    """Execute a query and return the cursor (for INSERT/UPDATE/DELETE)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor


def fetch_one(query: str, params: tuple = ()):
    """Execute a query and return one row."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()


def fetch_all(query: str, params: tuple = ()):
    """Execute a query and return all rows."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    row = fetch_one(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return row[0] > 0 if row else False


if __name__ == "__main__":
    print(f"DB Type: {DB_TYPE}")
    print(f"DB File: {DB_FILE}")
    print(f"Tables: ", end="")
    rows = fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
    print([r[0] for r in rows])
