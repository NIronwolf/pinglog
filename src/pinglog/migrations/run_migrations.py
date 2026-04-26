import sqlite3
from pinglog.config import DATABASE_PATH
from pathlib import Path
import importlib


def run_migrations():
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                applied_at INTEGER NOT NULL
            );
        """)

        # Scan for migration scipts in the migrations directory
        scripts = sorted(Path(__file__).parent.glob("[0-9]*.py"))
        for script in scripts:
            if not cur.execute(
                "SELECT 1 FROM migrations WHERE filename = ?", (script.name,)
            ).fetchone():
                module = importlib.import_module(f"pinglog.migrations.{script.stem}")
                module.migrate()
                cur.execute(
                    "INSERT INTO migrations (filename, applied_at) VALUES (?, strftime('%s', 'now'))",
                    (script.name,),
                )


if __name__ == "__main__":
    run_migrations()
