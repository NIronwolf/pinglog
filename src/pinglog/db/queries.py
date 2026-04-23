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


def get_streak(chat_id):
    """get_streak calculates how many continuous days of entries exist for a given
    chat_id starting from yesterday.  A missed day breaks the streak.  For example,
    if there are entries for today, yesterday, and the day before yesterday,
    but not three days ago, the streak is 2.  If there are entries for today
    and the day before yesterday, but not yesterday, the streak is 0."""
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
    return max(0, streak - 1)


def get_day(chat_id, date):
    user_timezone = get_timezone(chat_id)
    result = []
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        beginning_of_day = int(
            datetime.combine(date, datetime.min.time(), tzinfo=ZoneInfo(user_timezone))
            .astimezone(timezone.utc)
            .timestamp()
        )
        end_of_day = int(
            datetime.combine(date, datetime.max.time(), tzinfo=ZoneInfo(user_timezone))
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


def set_ping_interval(chat_id, interval_seconds):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        logger.debug(
            f"Setting ping interval for chat_id={chat_id} to {interval_seconds} seconds"
        )
        cur.execute(
            "UPDATE state SET ping_interval=? WHERE chat_id=?;",
            (interval_seconds, chat_id),
        )


def get_ping_interval(chat_id) -> int:
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        logger.debug(f"Getting ping interval for chat_id={chat_id}")
        cur.execute("SELECT ping_interval FROM state WHERE chat_id=?;", (chat_id,))
        result = cur.fetchone()
        if result and result[0] is not None:
            ping_interval = result[0]
            logger.debug(
                f"Ping interval for chat_id={chat_id} is {ping_interval} seconds"
            )
            return ping_interval
        else:
            return 3600  # default to 1 hour if not set


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
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        logger.debug(f"Setting silent_next for chat_id={chat_id} to {value}")
        cur.execute(
            "UPDATE state SET silent_next=? WHERE chat_id=?;",
            (1 if value else 0, chat_id),
        )


def is_silent_next(chat_id):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT silent_next FROM state WHERE chat_id=?;", (chat_id,))
        result = cur.fetchone()
        if result and result[0] is not None:
            silent_next = bool(result[0])
            logger.debug(f"silent_next for chat_id={chat_id} is {silent_next}")
            return silent_next
        else:
            logger.debug(
                f"No silent_next set for chat_id={chat_id}, defaulting to False"
            )
            return False


def get_total_xp(chat_id):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT SUM(xp_earned) FROM logs WHERE chat_id=?;", (chat_id,))
        result = cur.fetchone()
        total_xp = result[0] if result[0] is not None else 0
        logger.debug(f"Total XP calculated: {total_xp}")
        return total_xp


def get_all_chat_ids():
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT DISTINCT chat_id FROM state;")
        result = cur.fetchall()
        chat_ids = [row[0] for row in result]
        logger.debug(f"Retrieved chat_ids: {chat_ids}")
        return chat_ids


def get_recent_logs(chat_id, limit=10):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT id, timestamp, activity, xp_earned FROM logs "
            "WHERE chat_id=? ORDER BY timestamp DESC LIMIT ?;",
            (chat_id, limit),
        )
        result = []
        for row in cur.fetchall():
            logger.debug(f"Retrieved log entry for chat_id={chat_id}: {row}")
            result.append(
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "activity": row[2],
                    "xp_earned": row[3],
                }
            )
        return result


def get_stats(chat_id):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*), SUM(xp_earned) FROM logs WHERE chat_id=?;",
            (chat_id,),
        )
        result = cur.fetchone()
        total_entries = result[0] if result[0] is not None else 0
        total_xp = result[1] if result[1] is not None else 0
        logger.debug(
            f"Stats for chat_id={chat_id}: total_entries={total_entries}, total_xp={total_xp}"
        )
        return {
            "total_entries": total_entries,
            "total_xp": total_xp,
        }


def edit_log_entry(log_id, new_activity=None, new_xp_earned=None):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        fields = []
        params = []
        if new_activity is not None:
            fields.append("activity=?")
            params.append(new_activity)
        if new_xp_earned is not None:
            fields.append("xp_earned=?")
            params.append(new_xp_earned)
        params.append(log_id)
        if not fields:
            logger.debug(f"No fields to update for log entry id={log_id}")
            return
        logger.debug(
            f"Editing log entry id={log_id} with fields: {fields}, params: {params}"
        )
        cur.execute(
            f"UPDATE logs SET {', '.join(fields)} WHERE id=?;",
            tuple(params),
        )


def delete_log_entry(log_id):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        logger.debug(f"Deleting log entry id={log_id}")
        cur.execute(
            "DELETE FROM logs WHERE id=?;",
            (log_id,),
        )


def get_all_logs(chat_id):
    with sqlite3.connect(DATABASE_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT id, timestamp, activity, xp_earned FROM logs "
            "WHERE chat_id=? ORDER BY timestamp ASC;",
            (chat_id,),
        )
        result = []
        for row in cur.fetchall():
            logger.debug(f"Retrieved log entry for chat_id={chat_id}: {row}")
            result.append(
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "activity": row[2],
                    "xp_earned": row[3],
                }
            )
        return result
