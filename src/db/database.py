import sqlite3
from config import settings

def get_db_connection():
    return sqlite3.connect(settings.DB_FILE)