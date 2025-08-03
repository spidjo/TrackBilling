import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME = "SaaS Billing Platform"
    APP_URL = os.getenv("APP_URL", "http://localhost:8501")
    DB_FILE = os.getenv("DB_FILE", "data/billing.db")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

settings = Settings()