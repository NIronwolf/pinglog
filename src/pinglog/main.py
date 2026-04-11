import logging
from telegram import Update
from telegram.ext import Application, CommandHandler
from pinglog.config import TELEGRAM_BOT_TOKEN
from pinglog.bot.handlers import handle_start

logging.basicConfig(level="DEBUG")


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", handle_start))
    application.run_polling()


if __name__ == "__main__":
    main()
