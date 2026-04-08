from dotenv import load_dotenv
import os

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
USER_TIMEZONE = os.getenv("USER_TIMEZONE", "America/Phoenix")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/pinglog.db")
PING_INTERVAL_MIUTES = int(os.getenv("PING_INTERVAL_MINUTES", "60"))
