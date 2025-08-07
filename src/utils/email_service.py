# src/utils/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.email_utils import send_email, send_email_with_attachment
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
APP_URL = os.getenv("APP_URL", "http://localhost:8501")

# Setup Jinja2 template environment
templates_env = Environment(
    loader=FileSystemLoader('assets/templates'),
    autoescape=select_autoescape(["html", "xml"])
)
def send_verification_email(to_email, username, token): 
    verify_url = f"{APP_URL}?verify={token}"
    app_name = os.getenv("APP_NAME", "TrackBilling")
    # Render HTML content from template
    template = templates_env.get_template("email_verification.html")
    html_content = template.render(username=username, verify_url=verify_url, app_name=app_name)

    text_content = f"Hi {username},\n\nPlease verify your email using the link below:\n{verify_url}"

    send_email(to_email, "Verify Your Account", text_content, html_content)
    
def send_invoce_email(to_email, subject, client_name, invoice_id, invoice_date, invoice_amount, pdf_bytes, is_paid, tenant_name):
    template = templates_env.get_template("email_invoice.html")
    html_content = template.render(client_name=client_name, invoice_id=invoice_id,
                                   invoice_date=invoice_date, invoice_amount=invoice_amount,
                                   is_paid=is_paid,tenant_name=tenant_name)
    
    text_content = f"Hi {client_name}, \n\nAttached is your invoice"
    

    send_email_with_attachment(to_email, subject,text_content,f"invoice_{invoice_id}.pdf", pdf_bytes,html_content)