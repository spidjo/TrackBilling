# utils/email_utils.py

import smtplib
from datetime import datetime    
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from venv import logger
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os
from db.database import get_db_connection
from utils.report_utils import generate_tenant_billing_report_pdf

load_dotenv()

# Email configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "mail.privateemail.com")
EMAIL_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_HOST_USER","admin@sgltrack.com")
EMAIL_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_SENDER = os.getenv("EMAIL_HOST_USER", EMAIL_USER)
APP_URL = os.getenv("APP_URL", "https://sgltrack.com")

# Jinja2 template environment
templates_env = Environment(
    loader=FileSystemLoader('assets/templates'),
    autoescape=select_autoescape(["html", "xml"])
)

def render_email_template(template_name, **context):
    """Render an email template with the given context"""
    template = templates_env.get_template(template_name)
    return template.render(
        **context,
        year=datetime.now().year,
        app_url=APP_URL
    )

def send_email(to_email, subject, body_text, body_html=None):
    """
    Send an email with optional HTML content
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email

    # Attach plain text version
    msg.attach(MIMEText(body_text, "plain"))

    # Attach HTML version if provided
    if body_html:
        msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Error sending email to {to_email}: {e}")
        return False

def send_email_with_attachment(to_email, subject, body_text, filename, file_bytes, body_html=None):
    """Send an email with an attachment"""
    msg = MIMEMultipart("mixed")
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = subject

    # Create alternative part for text/HTML
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(body_text, "plain"))
    if body_html:
        alternative.attach(MIMEText(body_html, "html"))
    msg.attach(alternative)

    # Attach file
    attachment = MIMEApplication(file_bytes, Name=filename)
    attachment["Content-Disposition"] = f'attachment; filename="{filename}"'
    msg.attach(attachment)

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Error sending email with attachment to {to_email}: {e}")
        return False

def email_billing_report_to_admin(tenant_id, start_date, end_date):
    """Generate and email a billing report PDF to the tenant admin"""
    logger.info(f"Generating billing report for tenant {tenant_id} ({start_date} to {end_date})")
    
    try:
        # Generate PDF report first
        # Convert date objects to datetime objects
        report_start_dt = datetime.combine(start_date, datetime.min.time())
        report_end_dt = datetime.combine(end_date, datetime.max.time())

        pdf_bytes = generate_tenant_billing_report_pdf(tenant_id, report_start_dt, report_end_dt)
        if not pdf_bytes:
            logger.error(f"Failed to generate PDF for tenant {tenant_id}")
            return False

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get admin email and company name
        cursor.execute("""
            SELECT email, company_name FROM users
            WHERE tenant_id = %s AND role = 'admin'
            ORDER BY id LIMIT 1
        """, (tenant_id,))
        result = cursor.fetchone()
        
        if not result:
            logger.error(f"No admin found for tenant {tenant_id}")
            return False

        admin_email, company_name = result
        
        filename = f"{company_name}_Billing_Report_{start_date}_to_{end_date}.pdf"
        
        # Prepare email content
        subject = f"📊 {company_name} Billing Report - {start_date} to {end_date}"
        
        # Plain text version
        plain_body = (
            f"Hello {company_name},\n\n"
            f"Attached is your billing report for {start_date} to {end_date}.\n\n"
            "You can also view this report in your billing portal.\n\n"
            "Regards,\nBilling Team"
        )
        
        # HTML version
        html_body = render_email_template(
            "billing_report.html",
            company_name=company_name,
            start_date=start_date,
            end_date=end_date,
            report_period=f"{start_date} to {end_date}"
        )
        
        # Send email with attachment
        success = send_email_with_attachment(
            to_email=admin_email,
            subject=subject,
            body_text=plain_body,
            filename=filename,
            file_bytes=pdf_bytes,
            body_html=html_body
        )
        
        if success:
            logger.info(f"✅ Billing report sent to {admin_email}")
        else:
            logger.error(f"❌ Failed to send billing report to {admin_email}")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error in billing report process for tenant {tenant_id}: {str(e)}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def send_payment_verified_email(to_email, username, amount, invoice_id, invoice_date, tenant_name):
    """Send payment verification confirmation email"""
    print(f"Sending payment verification email to {to_email} for invoice {invoice_id}")
    subject = f"💰 Payment Verified for Invoice #{invoice_id}"
    
    html_body = render_email_template(
        "payment_verified.html",
        username=username,
        amount=amount,
        invoice_id=invoice_id,
        invoice_date=invoice_date,
        tenant_name=tenant_name
    )
    
    text_body = (
        f"Hello {username},\n\n"
        f"✅ Your payment of R{amount:.2f} for Invoice #{invoice_id} "
        f"dated {invoice_date} has been verified and marked as paid.\n\n"
        f"Thank you for your payment!\n\n"
        f"Regards,\n{tenant_name} Billing Team"
    )
    
    return send_email(to_email, subject, text_body, html_body)

def send_password_reset_email(to_email, username, token):
    """Send password reset email"""
    subject = "🔑 Reset Your Password"
    reset_url = f"{APP_URL}/reset-password?token={token}"
    
    html_body = render_email_template(
        "password_reset.html",
        username=username,
        reset_url=reset_url
    )
    
    text_body = (
        f"Hi {username},\n\n"
        f"You requested a password reset. Use this link:\n{reset_url}\n\n"
        "This link will expire in 24 hours."
    )
    
    return send_email(to_email, subject, text_body, html_body)

def send_usage_alert_email(to_email, username, metric_name, usage, limit):
    """Send usage alert email"""
    subject = f"⚠️ Usage Alert: {metric_name}"
    
    # Calculate the percentage used
    percent_used = min(100, (usage / limit) * 100) if limit else 0
    
    print(f"Sending usage alert email to {to_email} for {metric_name} usage")
    html_body = render_email_template(
        "usage_alert.html",
        username=username,
        metric_name=metric_name,
        usage=usage,
        limit=limit,
        percent_used=percent_used,  # Add this
        plan_limit=limit,           # Add this if needed
        current_usage=usage,       # Add this if needed
        app_name="Your App Name"   # Add your app name here
    )
    
    text_body = (
        f"Hi {username},\n\n"
        f"Your usage for {metric_name} has reached {usage}, "
        f"which exceeds your limit of {limit}.\n\n"
        "Please consider upgrading your plan."
    )

    print(f'about to send email to {to_email} for {metric_name} usage')
    result = send_email(to_email, subject, text_body, html_body)
    if result:
        print(f"✅ Usage alert email sent to {to_email} for {metric_name} usage")
    else:
        print(f"❌ Failed to send usage alert email to {to_email} for {metric_name} usage")