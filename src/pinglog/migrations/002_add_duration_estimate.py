# migrations/002_add_duration_estimate.py
import sqlite3
from pinglog.config import DATABASE_PATH


def migrate():
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        # Check if column already exists so it's safe to run twice
        cur.execute("PRAGMA table_info(logs);")
        columns = [row[1] for row in cur.fetchall()]
        if "duration_estimate" not in columns:
            cur.execute(
                "ALTER TABLE logs ADD COLUMN duration_estimate INTEGER NOT NULL DEFAULT 0;"
            )
            print("Added duration_estimate column to logs table.")
        else:
            print("duration_estimate column already exists, skipping.")


if __name__ == "__main__":
    migrate()
