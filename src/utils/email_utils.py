# utils/email_utils.py

from datetime import datetime    
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
import base64
from dotenv import load_dotenv
import os
from db.database import get_db_connection
from utils.report_utils import generate_tenant_billing_report_pdf
import logging

# Set up logging
logger = logging.getLogger(__name__)

load_dotenv()

# SendGrid configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("EMAIL_HOST_USER", "admin@sgltrack.com")
APP_URL = os.getenv("APP_URL", "https://app.sgltrack.com")
APP_NAME = os.getenv("APP_NAME", "SglTrack")

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
        year=datetime.now().year,  # This should work fine
        app_url=APP_URL,
        app_name=APP_NAME
    )

def send_email(to_email, subject, body_text, body_html=None):
    """
    Send an email using SendGrid API
    """
    if not SENDGRID_API_KEY:
        logger.error("SendGrid API key not configured")
        return False

    try:
        message = Mail(
            from_email=Email(SENDER_EMAIL),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", body_text)
        )
        
        if body_html:
            message.add_content(Content("text/html", body_html))
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            logger.info(f"✅ Email sent successfully to {to_email}")
            return True
        else:
            logger.error(f"❌ SendGrid API error: {response.status_code} - {response.body}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending email to {to_email}: {e}")
        return False

def send_email_with_attachment(to_email, subject, body_text, filename, file_bytes, body_html=None):
    """Send an email with an attachment using SendGrid"""
    if not SENDGRID_API_KEY:
        logger.error("SendGrid API key not configured")
        return False

    try:
        message = Mail(
            from_email=Email(SENDER_EMAIL),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", body_text)
        )
        
        if body_html:
            message.add_content(Content("text/html", body_html))
        
        # Create attachment
        encoded_file = base64.b64encode(file_bytes).decode()
        attachment = Attachment()
        attachment.file_content = FileContent(encoded_file)
        attachment.file_type = FileType('application/pdf')
        attachment.file_name = FileName(filename)
        attachment.disposition = Disposition('attachment')
        message.attachment = attachment
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            logger.info(f"✅ Email with attachment sent successfully to {to_email}")
            return True
        else:
            logger.error(f"❌ SendGrid API error: {response.status_code} - {response.body}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending email with attachment to {to_email}: {e}")
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
    logger.info(f"Sending payment verification email to {to_email} for invoice {invoice_id}")
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
    
    logger.info(f"Sending usage alert email to {to_email} for {metric_name} usage")
    html_body = render_email_template(
        "usage_alert.html",
        username=username,
        metric_name=metric_name,
        usage=usage,
        limit=limit,
        percent_used=percent_used,
        plan_limit=limit,
        current_usage=usage,
        app_name=APP_NAME
    )
    
    text_body = (
        f"Hi {username},\n\n"
        f"Your usage for {metric_name} has reached {usage}, "
        f"which exceeds your limit of {limit}.\n\n"
        "Please consider upgrading your plan."
    )

    logger.info(f'About to send email to {to_email} for {metric_name} usage')
    result = send_email(to_email, subject, text_body, html_body)
    if result:
        logger.info(f"✅ Usage alert email sent to {to_email} for {metric_name} usage")
    else:
        logger.error(f"❌ Failed to send usage alert email to {to_email} for {metric_name} usage")
    return result

def send_verification_email(to_email, username, token):
    """Send account verification email"""
    subject = "✅ Verify Your Account"
    verification_url = f"{APP_URL}/verify-email?token={token}"
    
    html_body = render_email_template(
        "verification_email.html",
        username=username,
        verification_url=verification_url
    )
    
    text_body = (
        f"Hi {username},\n\n"
        f"Welcome to {APP_NAME}! Please verify your email address by clicking this link:\n"
        f"{verification_url}\n\n"
        "This link will expire in 24 hours."
    )
    
    return send_email(to_email, subject, text_body, html_body)