import sqlite3
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pinglog.config import DATABASE_PATH, USER_TIMEZONE
import logging

logger = logging.getLogger(__name__)


def create_or_update_state(
    chat_id, timezone_str=USER_TIMEZONE, next_ping_at=None, silent_next=None
):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        fields = []
        params = []
        if chat_id is not None:
            fields.append("chat_id")
            params.append(chat_id)
        if timezone_str is not None:
            fields.append("timezone")
            params.append(timezone_str)
        if next_ping_at is not None:
            fields.append("next_ping_at")
            params.append(next_ping_at)
        if silent_next is not None:
            fields.append("silent_next")
            params.append(1 if silent_next else 0)
        logger.debug(f"Query fields: {fields}, params: {params}")
        logger.debug(
            f"INSERT OR REPLACE INTO state ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(params))});"
        )
        cur.execute(
            f"INSERT OR REPLACE INTO state ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(params))});",
            tuple(params),
        )


def get_timezone(chat_id):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT timezone FROM state WHERE chat_id=?;", (chat_id,))
        result = cur.fetchone()
        if result:
            timezone_str = result[0]
            logger.debug(f"Found timezone for chat_id={chat_id}: {timezone_str}")
            return timezone_str
        else:
            logger.debug(
                f"No timezone found for chat_id={chat_id}, using default: {USER_TIMEZONE}"
            )
            return USER_TIMEZONE


def insert_log(chat_id, activity, xp_earned):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        now = int(datetime.now(timezone.utc).timestamp())
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
    user_timezone = get_timezone(chat_id)
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        streak = 0
        check_date = today = datetime.now().date()
        for row in cur.execute(
            "SELECT timestamp FROM logs WHERE chat_id=? ORDER BY timestamp DESC;",
            (chat_id,),
        ):
            logger.debug(f"Processing log entry: {row[0]} for chat_id={chat_id}")
            log_date = (
                datetime.fromtimestamp(row[0], tz=timezone.utc)
                .astimezone(ZoneInfo(user_timezone))
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


def get_day(chat_id, date):
    result = []
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        beginning_of_day = int(
            datetime.combine(date, datetime.min.time())
            .astimezone(timezone.utc)
            .timestamp()
        )
        end_of_day = int(
            datetime.combine(date, datetime.max.time())
            .astimezone(timezone.utc)
            .timestamp()
        )
        logger.debug(
            f"Getting logs for chat_id={chat_id} on date={date}, "
            f"Searching between {beginning_of_day} and {end_of_day}"
        )
        for row in cur.execute(
            "SELECT timestamp, activity, xp_earned FROM logs "
            "WHERE chat_id=? AND timestamp BETWEEN ? AND ? "
            "ORDER BY timestamp ASC;",
            (chat_id, beginning_of_day, end_of_day),
        ):
            logger.debug(f"Found log entry for chat_id={chat_id} on date={date}: {row}")
            result.append(
                {
                    "timestamp": row[0],
                    "activity": row[1],
                    "xp_earned": row[2],
                }
            )
    return result


def set_next_ping(chat_id: int, next_ping_at: int):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        # next_ping_at = int(date.astimezone(timezone.utc).timestamp())
        logger.debug(f"Setting next ping for chat_id={chat_id} to {next_ping_at}")
        cur.execute(
            "UPDATE state SET next_ping_at=? WHERE chat_id=?;",
            (next_ping_at, chat_id),
        )


def get_next_ping(chat_id) -> int | None:
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT next_ping_at FROM state WHERE chat_id=?;", (chat_id,))
        result = cur.fetchone()
        if result and result[0] is not None:
            next_ping_at = result[0]
            logger.debug(f"Next ping for chat_id={chat_id} is {next_ping_at}")
            return next_ping_at
        else:
            logger.debug(f"No next ping set for chat_id={chat_id}")
            return None


def set_silent_next(chat_id, value=True):
    pass


def is_silent_next(chat_id):
    pass


def get_total_xp(chat_id):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT SUM(xp_earned) FROM logs WHERE chat_id=?;", (chat_id,))
        result = cur.fetchone()
        total_xp = result[0] if result[0] is not None else 0
        logger.debug(f"Total XP calculated: {total_xp}")
        return total_xp
