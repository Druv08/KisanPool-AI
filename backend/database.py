import sqlite3
from pathlib import Path

DATABASE_NAME = Path(__file__).with_name("kisanpool.db")


def get_db_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection
