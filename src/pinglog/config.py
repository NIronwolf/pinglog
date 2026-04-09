from dotenv import load_dotenv
import os

load_dotenv()

_token = os.getenv("TELEGRAM_BOT_TOKEN")
if not _token:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")
TELEGRAM_BOT_TOKEN: str = _token

USER_TIMEZONE = os.getenv("USER_TIMEZONE", "America/Phoenix")

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/pinglog.db")

PING_INTERVAL_MINUTES = int(os.getenv("PING_INTERVAL_MINUTES", "60"))
