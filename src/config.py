import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME = "SaaS Billing Platform"
    APP_URL = os.getenv("APP_URL", "http://localhost:8501")
    DB_FILE = os.getenv("DB_FILE", "src/db/billing.db")
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_NAME = os.getenv("POSTGRES_DB", "billing_db")
    DB_USER = os.getenv("POSTGRES_USER", "billing_user")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "billing_pass")
    SENDER_EMAIL = os.getenv("SMTP_FROM")
    SENDER_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

settings = Settings()