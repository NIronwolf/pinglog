from pinglog.db.queries import (
    create_or_update_state,
    get_timezone,
    insert_log,
    set_next_ping,
    set_silent_next,
)
from datetime import datetime, timezone
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
    )


async def handle_log_message(update, context):
    log = parse_reply(update.message.text, update.effective_user.id)
    insert_log(update.effective_user.id, log["entry"], log["xp"]["total_xp"])
    if log["snooze"] > 0:
        set_next_ping(
            update.effective_user.id,
            int(datetime.now(timezone.utc).timestamp()) + log["snooze"],
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


def handle_status(update, context):
    pass
