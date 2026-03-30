import sqlite3
from datetime import datetime
from pinglog.config import DATABASE_PATH
import logging

logger = logging.getLogger(__name__)


def insert_log(chat_id, activity, xp_earned):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        now = datetime.now()  # TODO support timezone-aware timestamps
        cur.execute(
            "INSERT INTO logs (timestamp, chat_id, activity, xp_earned) VALUES (?, ?, ?, ?);",
            (now, chat_id, activity, xp_earned),
        )
        row_id = cur.lastrowid
        logger.debug(
            f"Inserted log: chat_id={chat_id}, activity='{activity}', xp_earned={xp_earned}, timestamp={now}"
        )
        logger.debug(f"Database row_id: {row_id}")
    return row_id


def get_streak():
    pass


def get_day():
    pass


def get_next_ping():
    pass


def set_next_ping():
    pass


def set_silent_next():
    pass


def unset_silent_next():
    pass


def is_silent_next():
    pass


def get_total_xp(chat_id):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT SUM(xp_earned) FROM logs WHERE chat_id=?;", (chat_id,))
        result = cur.fetchone()
        total_xp = result[0] if result[0] is not None else 0
        logger.debug(f"Total XP calculated: {total_xp}")
        return total_xp
