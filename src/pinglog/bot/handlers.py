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
    get_recent_logs,
)
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from pinglog.util import parse_reply, time_string_to_seconds
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
    user_timezone = get_timezone(update.effective_user.id)
    today = datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date()
    await _show_log(update, context, today)


async def handle_yesterday(update, context):
    user_timezone = get_timezone(update.effective_user.id)
    yesterday = datetime.now(timezone.utc).astimezone(
        ZoneInfo(user_timezone)
    ).date() - timedelta(days=1)
    await _show_log(update, context, yesterday)


async def handle_date(update, context):
    user_timezone = get_timezone(update.effective_user.id)

    if context.args:
        try:
            target_date = date.fromisoformat(context.args[0])
        except ValueError:
            relative_seconds = time_string_to_seconds(context.args[0])
            if relative_seconds is not None:
                target_date = datetime.now(timezone.utc).astimezone(
                    ZoneInfo(user_timezone)
                ).date() - timedelta(seconds=relative_seconds)
            else:
                await update.message.reply_markdown_v2(
                    "Invalid date entered\\.  Format 'YYYY\\-MM\\-DD' or '3d'\\."
                )
                return
    else:
        await update.message.reply_markdown_v2(
            "Invalid date entered\\.  Format 'YYYY\\-MM\\-DD' or '3d'\\."
        )
        return

    await _show_log(update, context, target_date)


async def handle_delete(update, context):
    await _show_recent(update, context)


async def handle_edit(update, context):
    await _show_recent(update, context)


async def _show_log(update, context, log_date: date):
    """Replys with date's entries in the format:
    Today/Yesterday/X days ago - *Month D* (Y endtries, W XP)

    *HH:MM* _+X XP_
    Entry text

    *HH:MM* _+X XP_
    Entry text
    """
    user_timezone = get_timezone(update.effective_user.id)
    activity_today = get_day(update.effective_user.id, log_date)

    entries_today = len(activity_today)
    xp_today = sum(entry["xp_earned"] for entry in activity_today)

    day_diff = (
        datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date() - log_date
    ).days
    day_str = (
        "Today"
        if day_diff == 0
        else "Yesterday"
        if day_diff == 1
        else f"{day_diff} days ago"
    )

    parts = [
        f"{day_str} \\- *{log_date.strftime('%B %-d')}*"
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


async def _show_recent(update, context):
    recent_logs = get_recent_logs(update.effective_user.id)
    if recent_logs is None or len(recent_logs) == 0:
        await update.message.reply_markdown_v2("No recent activity found\\.")
        return
    user_timezone = get_timezone(update.effective_user.id)

    formated_logs = []
    idx = 0
    current_day = entry_date = (
        datetime.fromtimestamp(recent_logs[0]["timestamp"], tz=timezone.utc)
        .astimezone(ZoneInfo(user_timezone))
        .date()
    )
    for log in recent_logs:
        entry_date = (
            datetime.fromtimestamp(log["timestamp"], tz=timezone.utc).astimezone(
                ZoneInfo(user_timezone)
            )
        ).date()
        if entry_date != current_day:
            day_diff = (
                datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date()
                - current_day
            ).days  # - 1
            day_str = (
                "Today"
                if day_diff == 0
                else "Yesterday"
                if day_diff == 1
                else f"{day_diff} days ago"
            )
            formated_logs.append(
                f"\n*{day_str}* \\- {current_day.strftime('%B %-d')}\n"
            )
            current_day = entry_date
        formated_logs.append(
            f"*{idx}* \\- "
            f"{datetime.fromtimestamp(log['timestamp'], tz=timezone.utc).astimezone(ZoneInfo(user_timezone)).strftime('%H:%M')} "
            f"{escape_markdown(log['activity'], version=2)}\n"
        )
        idx += 1

    day_diff = (
        datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date()
        - entry_date
    ).days
    day_str = (
        "Today"
        if day_diff == 0
        else "Yesterday"
        if day_diff == 1
        else f"{day_diff} days ago"
    )
    formated_logs.append(f"\n*{day_str}* \\- {entry_date.strftime('%B %-d')}\n")

    formated_logs = list(reversed(formated_logs))

    parts = ["Recent activity:"]
    for log in formated_logs:
        parts.append(log)

    await update.message.reply_markdown_v2("\n".join(parts))


async def check_registered(update, context) -> bool:
    if get_next_ping(update.effective_user.id) is None:
        await update.message.reply_text(
            "Please send /start first to set up your account!"
        )
        return False
    return True
