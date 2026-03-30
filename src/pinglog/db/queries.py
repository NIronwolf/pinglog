import sqlite3
from pinglog.config import DATABASE_PATH
import logging

logger = logging.getLogger(__name__)


def get_cursor():
    con = sqlite3.connect(DATABASE_PATH)
    if con is None:
        logger.error("Failed to connect to the database.")
        raise ConnectionError("Could not connect to the database.")
    else:
        logger.debug("Successfully connected to the database.")
    cur = con.cursor()
    if cur is None:
        logger.error("Failed to create a cursor.")
        raise ConnectionError("Could not create a cursor.")
    else:
        logger.debug("Successfully created a cursor.")
    return cur


def insert_log():
    pass


def get_streak():
    pass


def get_day():
    pass


def get_next_ping():
    pass


def set_next_ping():
    pass


def set_silent_next():
    pass


def unset_silent_next():
    pass


def is_silent_next():
    pass


def get_total_xp():
    pass
