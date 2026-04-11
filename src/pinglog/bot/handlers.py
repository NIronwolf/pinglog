from pinglog.db.queries import create_or_update_state, get_timezone
from datetime import datetime, timezone


async def handle_start(update, context):
    user_timezone = get_timezone(update.effective_chat.id)
    now = int(datetime.now(timezone.utc).timestamp())
    next_ping_time = now + 15 * 60  # 15 minutes in seconds
    create_or_update_state(update.effective_user.id, user_timezone, next_ping_time)

    await update.message.reply_text(
        "Hello! I'm your PingLog bot.  You can send a message any time and I'll log it as your activity."
    )
    await update.message.reply_text(
        "I'll ping you every 15 minutes to check in. You can also snooze the pings for a certain amount of time if you need a break."
    )


def handle_log_message(update, context):
    pass


def handle_snooze_message(update, context):
    pass


def handle_status(update, context):
    pass


def handle_silent(update, context):
    pass
