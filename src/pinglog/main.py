import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from pinglog.config import TELEGRAM_BOT_TOKEN
from pinglog.bot.handlers import handle_start, handle_log_message

logging.basicConfig(level="DEBUG")


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_log_message)
    )
    application.run_polling()


if __name__ == "__main__":
    main()
