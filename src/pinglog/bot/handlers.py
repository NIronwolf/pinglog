from pinglog.db.queries import (
    create_or_update_state,
    get_timezone,
    insert_log,
    get_next_ping,
    set_next_ping,
    set_silent_next,
    get_ping_interval,
    is_silent_next,
    get_total_xp,
    get_streak,
    get_day,
)
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pinglog.util import parse_reply
from telegram.helpers import escape_markdown


async def handle_start(update, context):
    user_timezone = get_timezone(update.effective_user.id)
    now = int(datetime.now(timezone.utc).timestamp())
    next_ping_time = now + 60 * 60  # 60 minutes in seconds
    create_or_update_state(update.effective_user.id, user_timezone, next_ping_time)

    await update.message.reply_text(
        "Hello! I'm your PingLog bot.  You can send a message any time and I'll log it as your activity."
    )
    await update.message.reply_text(
        "I'll ping you every hour to check in. You can also snooze the pings for a certain amount of time if you need a break."
        "Just add snooze or silent and a duration as XhYm at the end.  For example: 'Went for a run snooze 2h' or 'Feeling tired silent 8h'"
    )


async def handle_log_message(update, context):
    if not await check_registered(update, context):
        return

    if not update.message or not update.message.text or not update.effective_user:
        return

    log = parse_reply(update.message.text, update.effective_user.id)

    insert_log(update.effective_user.id, log["timestamp"], log["entry"], log["xp"])

    snooze = (
        log["snooze"]
        if log["snooze"] > 0
        else get_ping_interval(update.effective_user.id)
    )
    set_next_ping(
        update.effective_user.id,
        log["timestamp"] + snooze,
    )
    set_silent_next(update.effective_user.id, log["silent"])

    safe_entry = escape_markdown(log["entry"], version=2)
    safe_total = escape_markdown(str(log["xp"]["total_xp"]), version=2)

    parts = [
        f"Logged: *{safe_entry}*",
        f"XP Earned: *{safe_total} XP*",
        f"  Base: \\+{log['xp']['base_xp']} XP",
    ]
    if log["xp"]["first_log_bonus"]:
        parts.append(f"  First Log Bonus: \\+{log['xp']['first_log_bonus']} XP")
    if log["xp"]["comeback_bonus"]:
        parts.append(f"  Comeback Bonus: \\+{log['xp']['comeback_bonus']} XP")
    if log["xp"]["early_morning_bonus"]:
        parts.append(f"  Early Morning Bonus: \\+{log['xp']['early_morning_bonus']} XP")
    if log["xp"]["late_night_bonus"]:
        parts.append(f"  Late Night Bonus: \\+{log['xp']['late_night_bonus']} XP")
    if log["xp"]["accuracy_bonus"]:
        parts.append(f"  Accuracy Bonus: \\+{log['xp']['accuracy_bonus']} XP")
    if log["xp"]["streak_bonus"]:
        parts.append(f"  Streak Bonus: \\+{log['xp']['streak_bonus']} XP")

    message = "\n".join(parts)

    await update.message.reply_markdown_v2(message)


async def handle_status(update, context):
    """Replys with the current status of the user.
    Streak: X days
    Total XP: Y XP
    Today: Z entries, W XP

    Next ping: HH:MM (in N minutes) [Silent]"""
    user_timezone = get_timezone(update.effective_user.id)
    next_ping_time = get_next_ping(update.effective_user.id)
    next_ping_local = (
        datetime.fromtimestamp(next_ping_time, tz=timezone.utc).astimezone(
            ZoneInfo(user_timezone)
        )
        if next_ping_time
        else None
    )
    next_ping_silent = is_silent_next(update.effective_user.id)
    streak_days = get_streak(update.effective_user.id)
    total_xp = get_total_xp(update.effective_user.id)
    activity_today = get_day(
        update.effective_user.id,
        datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date(),
    )
    entries_today = len(activity_today)
    xp_today = sum(entry["xp_earned"] for entry in activity_today)

    parts = [
        f"Streak: *{streak_days} days*",
        f"Total XP: *{total_xp} XP*",
        f"Today: *{entries_today} entries*, *{xp_today} XP*",
        "",
        f"Next ping: *{next_ping_local.strftime('%H:%M') if next_ping_local else 'N/A'}*"
        + (" \\[Silent\\]" if next_ping_silent else ""),
    ]

    message = "\n".join(parts)

    await update.message.reply_markdown_v2(message)


async def handle_today(update, context):
    """Replys with today's entries in the format:
    Today - *Month D* (Y endtries, W XP)

    *HH:MM* _+X XP_
    Entry text

    *HH:MM* _+X XP_
    Entry text
    """
    user_timezone = get_timezone(update.effective_user.id)
    activity_today = get_day(
        update.effective_user.id,
        datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date(),
    )
    entries_today = len(activity_today)
    xp_today = sum(entry["xp_earned"] for entry in activity_today)

    parts = [
        f"Today \\- *{datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).strftime('%B %-d')}*"
        + f" \\({entries_today} entries, {xp_today} XP\\)",
    ]
    for entry in activity_today:
        entry_time = (
            datetime.fromtimestamp(entry["timestamp"], tz=timezone.utc)
            .astimezone(ZoneInfo(user_timezone))
            .strftime("%H:%M")
        )
        parts.append(
            f"\n*{entry_time}* _\\+{entry['xp_earned']} XP_\n{escape_markdown(entry['activity'], version=2)}"
        )

    message = "\n".join(parts)

    await update.message.reply_markdown_v2(message)


async def check_registered(update, context) -> bool:
    if get_next_ping(update.effective_user.id) is None:
        await update.message.reply_text(
            "Please send /start first to set up your account!"
        )
        return False
    return True
