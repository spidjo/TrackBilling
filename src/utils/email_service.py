# src/utils/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.email_utils import send_email
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
APP_URL = os.getenv("APP_URL", "http://localhost:8501")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "templates")
# Setup Jinja2 template environment
templates_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)
def send_verification_email(to_email, username, token):
    verify_url = f"{APP_URL}?verify={token}"

    # Render HTML content from template
    template = templates_env.get_template("email_verification.html")
    html_content = template.render(username=username, verification_link=verify_url)

    text_content = f"Hi {username},\n\nPlease verify your email using the link below:\n{verify_url}"

    send_email(to_email, "Verify Your Account", text_content, html_content)