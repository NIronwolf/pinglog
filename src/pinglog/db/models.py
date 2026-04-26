import sqlite3
from pinglog.config import DATABASE_PATH


def init_db():
    con = sqlite3.connect(DATABASE_PATH)

    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    INTEGER NOT NULL,   -- Unix timestamp of when the activity was logged
            chat_id      INTEGER NOT NULL,   -- Telegram chat ID
            activity     TEXT    NOT NULL,   -- what you typed
            xp_earned    INTEGER,            -- total XP earned for this entry (base + bonuses)
            xp_breakdown TEXT                -- JSON string with breakdown of XP components (base, streak bonus, etc.)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS state (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id         INTEGER NOT NULL UNIQUE,  -- Telegram chat ID,
            timezone        TEXT NOT NULL,            -- IANA timezone string (e.g., "America/New_York"),
            ping_interval   INTEGER DEFAULT 3600,     -- seconds between pings (default: 1 hour)
            next_ping_at    INTEGER DEFAULT 0,        -- ISO 8601 datetime of scheduled ping
            silent_next     INTEGER DEFAULT 0         -- 1 = silent follow-up (sleeping)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
        id InTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL UNIQUE,
        applied_at INTEGER NOT NULL
        );
    """)

    con.commit()

    con.close()


if __name__ == "__main__":
    init_db()
