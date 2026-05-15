import logging
import asyncio
from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from pinglog.config import TELEGRAM_BOT_TOKEN
from pinglog.bot.handlers import (
    handle_start,
    handle_log_message,
    handle_status,
    handle_today,
    handle_yesterday,
    handle_date,
    handle_delete,
    handle_delete_callback,
    handle_edit,
    handle_edit_callback,
    handle_clearedits,
    handle_recent,
    handle_cancel_callback,
)

logging.basicConfig(level="DEBUG")


async def post_init(application: Application):
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Set up your PingLog account"),
            BotCommand("status", "View your current streak and XP"),
            BotCommand("today", "View today's log entries"),
            BotCommand("yesterday", "View yesterday's log entries"),
            BotCommand("date", "View log entries for a specific date"),
            BotCommand("recent", "View recent log entries"),
            BotCommand("edit", "Edit a recent log entry"),
            BotCommand("delete", "Delete a recent log entry"),
            BotCommand("clearedits", "Clear all pending edits"),
        ]
    )


def main():
    application = (
        Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    )
    application.add_handler(CommandHandler("start", handle_start))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_log_message)
    )
    application.add_handler(CommandHandler("status", handle_status))

    application.add_handler(CommandHandler("today", handle_today))
    application.add_handler(CommandHandler("yesterday", handle_yesterday))
    application.add_handler(CommandHandler("date", handle_date))

    application.add_handler(CommandHandler("delete", handle_delete))
    application.add_handler(CommandHandler("edit", handle_edit))
    application.add_handler(CommandHandler("clearedits", handle_clearedits))
    application.add_handler(CommandHandler("recent", handle_recent))

    application.add_handler(
        CallbackQueryHandler(handle_delete_callback, pattern=r"^delete:\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_edit_callback, pattern=r"^edit:\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_cancel_callback, pattern=r"^cancel(:\d+)?$")
    )

    application.run_polling()


if __name__ == "__main__":
    main()
