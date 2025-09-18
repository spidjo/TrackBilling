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

def send_admin_invitation_email(to_email, username, token, tenant_name, subject=None, message=None):
    """Send tenant admin invitation email using SendGrid"""
    verification_link = f"{APP_URL}/verify?token={token}"
    
    # Use custom subject/message if provided, otherwise use default
    if not subject:
        subject = f"👑 Invitation to join {tenant_name} as Tenant Administrator"
    
    if not message:
        # Render HTML content from template if available
        try:
            template = templates_env.get_template("admin_invitation.html")
            html_content = template.render(
                username=username,
                tenant_name=tenant_name,
                verification_link=verification_link,
                app_name=APP_NAME,
                app_url=APP_URL
            )
        except:
            # Fallback to basic HTML if template not found
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .button {{ display: inline-block; padding: 12px 24px; background-color: #4CAF50; 
                              color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                    .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Tenant Administrator Invitation</h1>
                    </div>
                    <div class="content">
                        <p>Dear {username},</p>
                        <p>You have been invited to become the <strong>Tenant Administrator</strong> for <strong>{tenant_name}</strong>.</p>
                        <p>As a Tenant Administrator, you will have full access to manage users, subscriptions, and configurations for your organization.</p>
                        <p style="text-align: center;">
                            <a href="{verification_link}" class="button">Accept Invitation & Set Password</a>
                        </p>
                        <p>This invitation link will expire in <strong>24 hours</strong>.</p>
                        <p>If you did not request this invitation or believe this was sent in error, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated message from {APP_NAME}. Please do not reply to this email.</p>
                        <p>© {datetime.now().year} {APP_NAME}. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        
        text_content = f"""Dear {username},

You have been invited to become the Tenant Administrator for {tenant_name}.

As a Tenant Administrator, you will have full access to manage users, subscriptions, and configurations for your organization.

Please click the link below to set your password and verify your account:
{verification_link}

This invitation link will expire in 24 hours.

If you did not request this invitation or believe this was sent in error, please ignore this email.

Best regards,
The {APP_NAME} Team
"""
    else:
        # Use the provided custom message
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center;">
                    <h1>Tenant Administrator Invitation</h1>
                </div>
                <div style="padding: 20px; background-color: #f9f9f9;">
                    {message.replace('\n', '<br>')}
                </div>
                <div style="padding: 20px; text-align: center; color: #666; font-size: 12px;">
                    <p>This is an automated message from {APP_NAME}. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        text_content = message
    
    return send_email_via_sendgrid(
        to_email=to_email,
        subject=subject,
        body_text=text_content,
        body_html=html_content
    )