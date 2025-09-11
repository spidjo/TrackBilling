# src/db/database.py
# Database connection utility for the billing platform

import psycopg2
import psycopg2.extras
from config import settings

def get_db_connection():
    return psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        options="-c client_encoding=utf8 -c bytea_output=escape",
        cursor_factory=psycopg2.extras.DictCursor
    )
# def get_db_connection():
#     return psycopg2.connect(
#         host=settings.DB_HOST,
#         database=settings.DB_NAME,
#         user=settings.DB_USER,
#         password=settings.DB_PASSWORD,
#         # Add this to ensure raw data handling:
#         options="-c client_encoding=utf8 -c bytea_output=escape"
#     )