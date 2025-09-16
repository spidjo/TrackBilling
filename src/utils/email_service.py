# src/utils/email_service.py

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
import base64
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from dotenv import load_dotenv
import logging

# Set up logging
logger = logging.getLogger(__name__)

load_dotenv()

# SendGrid configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("EMAIL_HOST_USER", "admin@sgltrack.com")
APP_URL = os.getenv("APP_URL", "https://app.sgltrack.com")
APP_NAME = os.getenv("APP_NAME", "SglTrack")

# Setup Jinja2 template environment
templates_env = Environment(
    loader=FileSystemLoader('assets/templates'),
    autoescape=select_autoescape(["html", "xml"])
)

def send_email_via_sendgrid(to_email, subject, body_text, body_html=None, attachment_bytes=None, attachment_filename=None):
    """
    Send email using SendGrid API with optional attachment
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
        
        # Add attachment if provided
        if attachment_bytes and attachment_filename:
            encoded_file = base64.b64encode(attachment_bytes).decode()
            attachment = Attachment()
            attachment.file_content = FileContent(encoded_file)
            attachment.file_type = FileType('application/pdf')
            attachment.file_name = FileName(attachment_filename)
            attachment.disposition = Disposition('attachment')
            message.attachment = attachment
        
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

def send_verification_email(to_email, username, token): 
    """Send account verification email using SendGrid"""
    verify_url = f"{APP_URL}/verify_email?token={token}"
    
    # Render HTML content from template
    template = templates_env.get_template("email_verification.html")
    html_content = template.render(
        username=username, 
        verify_url=verify_url, 
        app_name=APP_NAME,
        app_url=APP_URL
    )

    text_content = f"""Hi {username},

Welcome to {APP_NAME}! Please verify your email address by clicking the link below:

{verify_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Regards,
The {APP_NAME} Team
"""

    subject = "✅ Verify Your Account"
    
    return send_email_via_sendgrid(
        to_email=to_email,
        subject=subject,
        body_text=text_content,
        body_html=html_content
    )
    
def send_invoice_email(to_email, subject, client_name, invoice_id, invoice_date, invoice_amount, pdf_bytes, is_paid, tenant_name):
    """Send invoice email with attachment using SendGrid"""
    # Render HTML content from template
    template = templates_env.get_template("email_invoice.html")
    html_content = template.render(
        client_name=client_name, 
        invoice_id=invoice_id,
        invoice_date=invoice_date, 
        invoice_amount=invoice_amount,
        is_paid=is_paid,
        tenant_name=tenant_name,
        app_name=APP_NAME
    )
    
    status_text = "PAID" if is_paid else "PENDING"
    
    text_content = f"""Hi {client_name},

Attached is your invoice #{invoice_id} dated {invoice_date} for R{invoice_amount:.2f}.

Status: {status_text}

You can also view and manage your invoices in your account portal.

Regards,
{tenant_name} Billing Team
"""

    filename = f"invoice_{invoice_id}.pdf"
    
    return send_email_via_sendgrid(
        to_email=to_email,
        subject=subject,
        body_text=text_content,
        body_html=html_content,
        attachment_bytes=pdf_bytes,
        attachment_filename=filename
    )

def send_password_reset_email(to_email, username, token):
    """Send password reset email using SendGrid"""
    reset_url = f"{APP_URL}/reset-password?token={token}"
    
    template = templates_env.get_template("password_reset.html")
    html_content = template.render(
        username=username,
        reset_url=reset_url,
        app_name=APP_NAME
    )
    
    text_content = f"""Hi {username},

You requested a password reset for your {APP_NAME} account.

Please use the following link to reset your password:

{reset_url}

This link will expire in 24 hours.

If you didn't request this reset, please ignore this email.

Regards,
The {APP_NAME} Team
"""

    subject = "🔑 Reset Your Password"
    
    return send_email_via_sendgrid(
        to_email=to_email,
        subject=subject,
        body_text=text_content,
        body_html=html_content
    )