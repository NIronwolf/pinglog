import sqlite3


def init_db():
    con = sqlite3.connect("data/pinglog.db")

    cur = con.cursor()

    cur.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,   -- ISO 8601: '2025-03-23T14:32:00'
                    chat_id     INTEGER NOT NULL,   -- Telegram chat ID
                    activity    TEXT    NOT NULL,   -- what you typed
                    xp_earned   INTEGER DEFAULT 10
                );
    """)

    cur.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    id              INTEGER PRIMARY KEY CHECK (id = 1),
                    next_ping_at    TEXT,              -- ISO 8601 datetime of scheduled ping
                    silent_next     INTEGER DEFAULT 0  -- 1 = silent follow-up (sleeping)
                );
    """)

    con.commit()
    con.close()


if __name__ == "__main__":
    init_db()
