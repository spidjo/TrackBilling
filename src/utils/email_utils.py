import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import os

def send_invoice_email(to_email, subject, body, pdf_bytes, filename, smtp_settings):
    if smtp_settings is None or not isinstance(smtp_settings, dict):
        print("❌ Invalid SMTP settings passed to send_invoice_email.")
        return

    # Access settings safely
    smtp_host = smtp_settings.get("host")
    smtp_port = smtp_settings.get("port")
    smtp_username = smtp_settings.get("username")
    smtp_password = smtp_settings.get("password")
    sender_email = smtp_settings.get("sender")

    if not all([smtp_host, smtp_port, smtp_username, smtp_password, sender_email]):
        print("❌ Missing SMTP configuration values.")
        return
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Attach body text
    msg.attach(MIMEText(body, "plain"))

    # Attach PDF
    part = MIMEApplication(pdf_bytes.read(), Name=filename)
    part["Content-Disposition"] = f'attachment; filename="{filename}"'
    msg.attach(part)

    # Send email
    with smtplib.SMTP_SSL(smtp_settings["host"], smtp_settings["port"]) as server:
        server.login(smtp_settings["username"], smtp_settings["password"])
        server.send_message(msg)
