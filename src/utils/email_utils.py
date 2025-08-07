import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
from io import BytesIO
from db.database import get_db_connection
from utils.report_utils import generate_tenant_billing_report_pdf

load_dotenv()

APP_URL = os.getenv("APP_URL", "http://localhost:8501")

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))  # TLS = 587
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", EMAIL_USER)

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Setup Jinja2 template environment
templates_env = Environment(
    loader=FileSystemLoader('assets/templates'),
    autoescape=select_autoescape(["html", "xml"])
)


def render_html_email(subject, title, body):
    template = templates_env.get_template("email_base.html")
    return template.render(subject=subject, title=title, body=body, year=datetime.now().year)

def send_email(to_email, subject, body_text, body_html=None):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to_email

    # Plain text fallback
    part1 = MIMEText(body_text, "plain")
    msg.attach(part1)

    # HTML content if available
    if body_html:
        part2 = MIMEText(body_html, "html")
        msg.attach(part2)

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Error sending email to {to_email}: {e}")



def send_email_with_attachment(to_email, subject, body_text, filename, pdf_bytes, body_html=None):
    msg = MIMEMultipart("mixed")
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = subject

    # Attach text/HTML body
    alternative_part = MIMEMultipart("alternative")
    alternative_part.attach(MIMEText(body_text, "plain"))
    if body_html:
        alternative_part.attach(MIMEText(body_html, "html"))
    msg.attach(alternative_part)

    # Attach PDF
    part = MIMEApplication(pdf_bytes, Name=filename)
    part["Content-Disposition"] = f'attachment; filename="{filename}"'
    msg.attach(part)

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email with attachment sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")



def email_billing_report_to_admin(tenant_id, start_date, end_date):
    print(f"Generating billing report for tenant_id {tenant_id} from {start_date} to {end_date}")
    conn = get_db_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT email, company_name FROM users
        WHERE tenant_id = ? AND role = 'admin'
        ORDER BY id LIMIT 1
    """, (tenant_id,))
    result = cursor.fetchone()
    if not result:
        print(f"No admin found for tenant_id {tenant_id}")
        return 

    admin_email, company_name = result
    pdf_bytes = generate_tenant_billing_report_pdf(tenant_id, start_date, end_date)
    filename = f"Tenant_Billing_Report_{start_date}_to_{end_date}.pdf"

    subject = "📊 Your Monthly Billing Report"
    plain_body = (
        f"Hello {company_name},\n\n"
        f"Attached is your billing report for {start_date} to {end_date}.\n\n"
        "Regards,\nBilling Team"
    )

    html_template = templates_env.get_template("billing_report.html")
    html_body = html_template.render(
        company_name=company_name,
        period=f"{start_date} to {end_date}"
    )

    send_email_with_attachment(admin_email, subject, plain_body, filename, pdf_bytes, html_body)


def send_password_reset_email(to_email, username, token):
    reset_url = f"{APP_URL}/reset-password?token={token}"

    # HTML and plain versions
    html_template = templates_env.get_template("password_reset.html")
    app_name = os.getenv("APP_NAME", "TrackBilling")
    
    html_content = html_template.render(username=username, reset_url=reset_url,app_name=app_name)

    text_content = f"Hi {username},\n\nYou requested a password reset. Use the link below:\n{reset_url}"

    send_email(to_email=to_email, subject="Reset Your Password", body_text=text_content, body_html=html_content)

def send_usage_alert_email(to_email, username, metric_name, usage, limit):
    # HTML and plain versions
    html_template = templates_env.get_template("usage_alert.html")
    html_content = html_template.render(
        username=username,
        metric_name=metric_name,
        usage=usage,
        limit=limit
    )

    text_content = (
        f"Hi {username},\n\n"
        f"Your usage for {metric_name} has reached {usage}, "
        f"which exceeds your limit of {limit}.\n\n"
        "Please consider upgrading your plan."
    )

    send_email(to_email, f"⚠️ Usage Alert: {metric_name}", text_content, html_content)


