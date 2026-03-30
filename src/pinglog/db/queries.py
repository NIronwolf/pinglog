import sqlite3
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pinglog.config import DATABASE_PATH, USER_TIMEZONE
import logging

logger = logging.getLogger(__name__)


def insert_log(chat_id, activity, xp_earned):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        now = datetime.now(timezone.utc)  # TODO: support timezone-aware timestamps
        cur.execute(
            "INSERT INTO logs (timestamp, chat_id, activity, xp_earned) "
            "VALUES (?, ?, ?, ?);",
            (now, chat_id, activity, xp_earned),
        )
        row_id = cur.lastrowid
        logger.debug(
            f"Inserted log: chat_id={chat_id}, activity='{activity}', "
            f"xp_earned={xp_earned}, timestamp={now}"
        )
        logger.debug(f"Database row_id: {row_id}")
    return row_id


# get_streak calculate how many continuous days of entries exist for a given
# chat_id starting from now.  A missed day breaks the streak.  For example,
# if there are entries for today, yesterday, and the day before yesterday,
# but not three days ago, the streak is 3.  If there are entries for today
# and the day before yesterday, but not yesterday, the streak is 1.
def get_streak(chat_id):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        streak = 0
        check_date = today = datetime.now().date()
        for row in cur.execute(
            "SELECT timestamp FROM logs WHERE chat_id=? "
            "GROUP BY DATE(timestamp) ORDER BY timestamp DESC;",
            (chat_id,),
        ):
            logger.debug(f"Processing log entry: {row[0]} for chat_id={chat_id}")
            log_date = (
                datetime.fromisoformat(row[0])
                .astimezone(ZoneInfo(USER_TIMEZONE))
                .date()
            )
            logger.debug(
                f"Checking log entry date: {log_date} against check_date: {check_date}"
            )
            if log_date < check_date:
                break
            if check_date == log_date:
                check_date = check_date - timedelta(days=1)
            streak = (today - check_date).days
        logger.debug(f"Calculated streak for chat_id={chat_id}: {streak}")
    return streak


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
