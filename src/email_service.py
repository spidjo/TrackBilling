# src/utils/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
APP_URL = os.getenv("APP_URL", "http://localhost:8501")

def send_verification_email(to_email, token, first_name="User"):
    """Send email verification link with token."""
    subject = "Verify your email address"
    verify_url = f"{APP_URL}?verify={token}"

    html_content = f"""
    <html>
    <body>
        <p>Hi {first_name},</p>
        <p>Thank you for registering! Please click the link below to verify your email:</p>
        <p><a href="{verify_url}">Verify Email</a></p>
        <p>If you did not register, you can ignore this email.</p>
        <p>– Billing Platform Team</p>
    </body>
    </html>
    """

    send_email(to_email, subject, html_content)

def send_email(to_email, subject, html_body):
    """Generic email sender function with HTML support."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"[EMAIL SENT] To: {to_email}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email to {to_email}: {e}")
