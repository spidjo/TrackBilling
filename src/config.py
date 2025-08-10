import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME = "SaaS Billing Platform"
    APP_URL = os.getenv("APP_URL", "http://localhost:8501")
    DB_FILE = os.getenv("DB_FILE", "src/db/billing.db")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "billing_db")
    DB_USER = os.getenv("DB_USER", "billing_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "billing_pass")
    SENDER_EMAIL = os.getenv("EMAIL_SENDER")
    SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")
    SMTP_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("EMAIL_PORT", 587))
    SMTP_USER = os.getenv("EMAIL_USER")
    SMTP_PASSWORD = os.getenv("EMAIL_PASSWORD")

settings = Settings()