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
    next_ping_time = now + 15 * 60  # 15 minutes in seconds
    create_or_update_state(update.effective_user.id, user_timezone, next_ping_time)

    await update.message.reply_text(
        "Hello! I'm your PingLog bot.  You can send a message any time and I'll log it as your activity."
    )
    await update.message.reply_text(
        "I'll ping you every 15 minutes to check in. You can also snooze the pings for a certain amount of time if you need a break."
    )


async def handle_log_message(update, context):
    log = parse_reply(update.message.text, update.effective_user.id)
    insert_log(update.effective_user.id, log["entry"], log["xp"])
    if log["snooze"] > 0:
        set_next_ping(
            update.effective_user.id,
            int(datetime.now(timezone.utc).timestamp()) + log["snooze"],
        )
        set_silent_next(update.effective_user.id, log["silent"])
    message = escape_markdown(
        f"Logged: {log['entry']} (+{log['xp']} XP){' [Silent]' if log['silent'] else ''}",
        version=2,
    )
    await update.message.reply_markdown_v2(message)


def handle_status(update, context):
    pass
