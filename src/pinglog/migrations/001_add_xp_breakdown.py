# migrations/001_add_xp_breakdown.py
import sqlite3
from pinglog.config import DATABASE_PATH


def migrate():
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        # Check if column already exists so it's safe to run twice
        cur.execute("PRAGMA table_info(logs);")
        columns = [row[1] for row in cur.fetchall()]
        if "xp_breakdown" not in columns:
            cur.execute("ALTER TABLE logs ADD COLUMN xp_breakdown TEXT;")
            print("Added xp_breakdown column to logs table.")
        else:
            print("xp_breakdown column already exists, skipping.")


if __name__ == "__main__":
    migrate()
