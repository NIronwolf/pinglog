import logging
import re
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
from pinglog.datatypes import ParsedReply, XPBreakdown

from pinglog.db.queries import (
    get_day,
    get_next_ping,
    is_silent_next,
    get_streak,
    get_timezone,
)

logger = logging.getLogger(__name__)


def parse_reply(text: str, chat_id: int) -> ParsedReply:
    result: ParsedReply = {
        "entry": text,
        "xp": {
            "base_xp": 0,
            "first_log_bonus": 0,
            "comeback_bonus": 0,
            "early_morning_bonus": 0,
            "late_night_bonus": 0,
            "accuracy_bonus": 0,
            "streak_bonus": 0,
            "total_xp": 0,
        },
        "snooze": 0,
        "silent": False,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    }
    if text:
        text = text.strip()

        # Look for HH:MM format at the start of the message to allow backdating entries
        time_prefix = re.match(r"^(\d{1,2}):(\d{2})\s+", text)
        if time_prefix:
            date = datetime.now(timezone.utc).date()
            parsed_time = time(int(time_prefix.group(1)), int(time_prefix.group(2)))
            now_local = datetime.now(timezone.utc).astimezone(
                ZoneInfo(get_timezone(chat_id))
            )
            if parsed_time > now_local.time():
                date -= timedelta(days=1)
            result["timestamp"] = int(
                datetime.combine(
                    date, parsed_time, tzinfo=ZoneInfo(get_timezone(chat_id))
                )
                .astimezone(timezone.utc)
                .timestamp()
            )
            text = text[time_prefix.end() :]
        result["entry"] = text

        # Look for Xd Xh Xm Xs format at the end of the message for snooze duration
        duration_suffix = re.search(r"\s+((?:\d+\s*[smhd]\s*)+)$", text, re.IGNORECASE)
        if duration_suffix:
            snooze_time_text = duration_suffix.group(1).lower()
            result["snooze"] = time_string_to_seconds(snooze_time_text)
            if result["snooze"] != 0:
                text = text[: duration_suffix.start()].strip()
                result["entry"] = text

            # Also look for s | sil | silent keyword at the end of the message for silent snooze
            silent_suffix = re.search(r"\s+(s|sil|silent)\s*$", text, re.IGNORECASE)
            if silent_suffix:
                result["silent"] = True
                text = text[: silent_suffix.start()].strip()
                result["entry"] = text

        result["xp"] = calculate_xp(result["entry"], chat_id, result["timestamp"])
    return result


def calculate_xp(entry: str, chat_id: int, timestamp: int) -> XPBreakdown:
    xp: XPBreakdown = {
        "base_xp": 0,
        "first_log_bonus": 0,
        "comeback_bonus": 0,
        "early_morning_bonus": 0,
        "late_night_bonus": 0,
        "accuracy_bonus": 0,
        "streak_bonus": 0,
        "total_xp": 0,
    }
    now_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    user_timezone = get_timezone(chat_id)
    now_local = now_utc.astimezone(ZoneInfo(user_timezone))

    # Base XP for logging an entry
    entry_length = len(entry)
    if entry_length <= 10:
        xp["base_xp"] = 50
    elif entry_length <= 30:
        xp["base_xp"] = 100
    else:
        xp["base_xp"] = 150

    # Bonus XP
    # First log of the day bonus
    day_entries = get_day(chat_id, now_local.date())
    if len(day_entries) == 0:
        xp["first_log_bonus"] = 200

    # Comeback bonus - First log after a silent/sleep period
    if is_silent_next(chat_id):
        xp["comeback_bonus"] = 150

    # Early morning bonus - Logs before 7 AM local time
    if now_local.hour < 7:
        xp["early_morning_bonus"] = 100

    # Late night bonus - Logs after 11 PM local time
    if now_local.hour >= 23:
        xp["late_night_bonus"] = 50

    # Accuracy bonus - Timing relative to schedule ping
    target_ping_time = get_next_ping(chat_id)
    logger.debug(
        f"Target ping time: {datetime.fromtimestamp(target_ping_time) if target_ping_time else 'None'}"
    )
    accuracy_seconds = now_utc.timestamp() - target_ping_time if target_ping_time else 0
    logger.debug(f"Current time (UTC): {now_utc}, Accuracy seconds: {accuracy_seconds}")
    if accuracy_seconds < -15 * 60:  # More than 15 minutes before target ping (early)
        xp["accuracy_bonus"] = 0
    elif accuracy_seconds < -10 * 60:  # Up to 10 minutes before target ping (early)
        xp["accuracy_bonus"] = 100
    elif accuracy_seconds < -5 * 60:  # Up to 5 minutes before target ping (early)
        xp["accuracy_bonus"] = 150
    elif accuracy_seconds < -2 * 60:  # Up to 2 minutes before target ping (early)
        xp["accuracy_bonus"] = 200
    elif accuracy_seconds <= 0:  # Within 0 - 2 minutes of target ping (on time)
        xp["accuracy_bonus"] = 250
    elif accuracy_seconds <= 5 * 60:  # Within 5 minutes of target (late)
        xp["accuracy_bonus"] = 150
    elif accuracy_seconds <= 10 * 60:  # Within 10 minutes of target ping (late)
        xp["accuracy_bonus"] = 100
    elif accuracy_seconds <= 15 * 60:  # Within 15 minutes of target ping (late)
        xp["accuracy_bonus"] = 50

    # Streak bonus - X% per day up to 25 days
    streak_multiplier = min(25, get_streak(chat_id)) / 100
    subtotal_xp = (
        xp["base_xp"]
        + xp["first_log_bonus"]
        + xp["comeback_bonus"]
        + xp["early_morning_bonus"]
        + xp["late_night_bonus"]
        + xp["accuracy_bonus"]
    )
    xp["streak_bonus"] = int(subtotal_xp * streak_multiplier)

    xp["total_xp"] = subtotal_xp + xp["streak_bonus"]

    return xp


def time_string_to_seconds(timestring: str) -> int:
    """Converts a time string like '1d 2h 30m' into total seconds.
    Supports days (d), hours (h), minutes (m), and seconds (s).

    Returns 0 if no valid time components are found.
    Caller should treat 0 as invalid and use a default value.
    """

    timegroups = re.split(r"(\d+) *([smhd]) *", timestring.lower())

    days = int(timegroups[timegroups.index("d") - 1]) if "d" in timegroups else 0
    hours = int(timegroups[timegroups.index("h") - 1]) if "h" in timegroups else 0
    minutes = int(timegroups[timegroups.index("m") - 1]) if "m" in timegroups else 0
    seconds = int(timegroups[timegroups.index("s") - 1]) if "s" in timegroups else 0

    offset_seconds = (days * 24 * 3600) + (hours * 3600) + (minutes * 60) + seconds

    logger.debug(f"timegroups: {timegroups}")
    logger.debug(f"offset_seconds: {offset_seconds}")

    return offset_seconds
