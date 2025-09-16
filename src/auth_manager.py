# src/auth_manager.py
import bcrypt
import psycopg2
import psycopg2.extras
import secrets
import socket
import logging
from datetime import datetime, timedelta
from dateutil import parser
from email_validator import validate_email, EmailNotValidError
from functools import lru_cache
from db.database import get_db_connection
from utils.email_service import send_verification_email

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_hashed_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')

def is_strong_password(password: str) -> bool:
    """Check if password meets strength requirements"""
    return (
        len(password) >= 8 and
        any(c.islower() for c in password) and
        any(c.isupper() for c in password) and
        any(c.isdigit() for c in password) and
        any(c in "!@#$%^&*()-_=+[{]};:'\",<.>/\\|" for c in password)
    )

def register_user(username, password, email, first_name, last_name, company, tenant_id):
    try:
        logger.info(f"Attempting to register user: {username}, email: {email}")
        # Validate email format
        validated_email = validate_email(email).email.lower()
        
        # Validate password strength
        if not is_strong_password(password):
            logger.warning(f"Password strength validation failed for user: {username}")
            return False, "Password must be at least 8 characters with uppercase, lowercase, number and special character"
            
        # Hash password
        hashed_pw = get_hashed_password(password)
        
        # Generate verification token
        token = secrets.token_urlsafe(32)
        logger.debug(f"Generated verification token for {username}")
        
        # Database operation
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users 
                (username, password, first_name, last_name, company_name, email, verification_token, tenant_id, token_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (username, hashed_pw, first_name, last_name, company, validated_email, token, tenant_id))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"User {username} registered successfully with ID: {user_id}")
            
            # Send verification email
            logger.info(f"Sending verification email to {validated_email}")
            send_verification_email(
                to_email=validated_email,
                username=first_name,
                token=token
            )
            logger.info(f"Verification email sent to {validated_email}")
            
            return True, "Registration successful"
            
        except psycopg2.IntegrityError as e:
            conn.rollback()
            logger.error(f"Integrity error during registration for {username}: {str(e)}")
            if "users_username_key" in str(e):
                return False, "Username already exists"
            elif "users_email_key" in str(e):
                return False, "Email already registered"
            return False, "Registration failed"
            
        finally:
            if conn: conn.close()
            
    except EmailNotValidError as e:
        logger.error(f"Email validation failed for {email}: {str(e)}")
        return False, f"Invalid email: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during registration for {username}: {str(e)}")
        return False, f"Registration failed: {str(e)}"

def authenticate_user(username: str, password: str) -> tuple:
    """Authenticate user with username and password"""
    logger.info(f"Attempting authentication for user: {username}")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user with minimal fields
        cursor.execute("""
            SELECT id, password, role, is_verified, tenant_id 
            FROM users 
            WHERE username = %s
        """, (username,))
        
        user = cursor.fetchone()
        if not user:
            logger.warning(f"User not found: {username}")
            return False, None, None, None

        user_id, stored_pw, role, is_verified, tenant_id = user
        logger.debug(f"User found: ID={user_id}, verified={is_verified}")
        
        # Check password
        if not bcrypt.checkpw(password.encode(), stored_pw.encode()):
            logger.warning(f"Invalid password for user: {username}")
            return False, None, None, None
            
        # Check verification status
        if not is_verified:
            logger.warning(f"User {username} is not verified")
            return "unverified", None, None, None
            
        logger.info(f"User {username} authenticated successfully")
        return True, role, tenant_id, user_id
        
    except Exception as e:
        logger.error(f"Authentication error for {username}: {str(e)}")
        return False, None, None, None
    finally:
        if conn: conn.close()

def verify_token(token: str) -> dict:
    """Verify email verification token"""
    logger.info(f"Attempting to verify token: {token}")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find user with this token
        cursor.execute("""
            SELECT id FROM users 
            WHERE verification_token = %s
                AND is_verified = 0
                AND token_timestamp > NOW() - INTERVAL '1 hour'
        """, (token,))
        
        user = cursor.fetchone()
        if not user:
            logger.warning(f"Invalid or expired token: {token}")
            return {"success": False, "error": "Invalid or expired token"}
            
        user_id = user[0]
        logger.info(f"Token valid for user ID: {user_id}")
        
        # Mark user as verified
        cursor.execute("""
            UPDATE users 
            SET is_verified = 1, 
                verification_token = NULL
            WHERE id = %s
        """, (user_id,))
        
        conn.commit()
        logger.info(f"User {user_id} verified successfully")
        return {"success": True}
        
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Token verification error: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        if conn: conn.close()

def resend_verification_email(username: str) -> dict:
    """Resend verification email to user"""
    logger.info(f"Attempting to resend verification email for user: {username}")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user details
        cursor.execute("""
            SELECT id, email, first_name, is_verified, last_verification_sent::timestamptz AS last_verification_sent 
            FROM users 
            WHERE username = %s
        """, (username,))
        
        user = cursor.fetchone()
        if not user:
            logger.warning(f"User not found: {username}")
            return {"success": False, "error": "User not found"}
            
        user_id, email, first_name, is_verified, last_sent = user
        logger.debug(f"User details: ID={user_id}, email={email}, verified={is_verified}, last_sent={last_sent}")
        
        # Check if already verified
        if is_verified:
            logger.warning(f"User {username} is already verified")
            return {"success": False, "error": "User is already verified"}
        
        # Check resend cooldown (15 minutes)
        if last_sent:
            if isinstance(last_sent, str):
                last_sent = parser.isoparse(last_sent)  # convert ISO string to datetime
            # now safe to subtract
            if (datetime.utcnow() - last_sent) < timedelta(minutes=15):
                remaining = timedelta(minutes=15) - (datetime.utcnow() - last_sent)
                return {
                    "success": False,
                    "error": "Please wait 15 minutes before requesting another verification email"
                }
        
        # Generate new token
        new_token = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        logger.debug(f"Generated new token for {username}")
        
        # Update user record
        cursor.execute("""
            UPDATE users 
            SET verification_token = %s,
                last_verification_sent = %s
            WHERE id = %s
        """, (new_token, now, user_id))
        
        # Send verification email
        logger.info(f"Sending verification email to {email}")
        send_verification_email(
            to_email=email,
            username=first_name,
            token=new_token
        )
        logger.info(f"Verification email sent to {email}")
        
        conn.commit()
        logger.info(f"Verification email resent successfully for {username}")
        return {"success": True}
        
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error resending verification email for {username}: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if conn: conn.close()

def get_client_ip() -> str:
    """Get client IP address"""
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "unknown"