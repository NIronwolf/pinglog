import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from pinglog.config import TELEGRAM_BOT_TOKEN
from pinglog.bot.handlers import (
    handle_start,
    handle_log_message,
    handle_status,
    handle_today,
    handle_yesterday,
    handle_date,
    handle_delete,
    handle_edit,
)

logging.basicConfig(level="DEBUG")


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
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

    application.run_polling()


if __name__ == "__main__":
    main()
