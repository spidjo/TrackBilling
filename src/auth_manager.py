import bcrypt
import psycopg2
import psycopg2.extras
import secrets
import socket
from datetime import datetime, timedelta
from email_validator import validate_email, EmailNotValidError
from functools import lru_cache
from db.database import get_db_connection
from utils.email_service import send_verification_email

# Cache password hashing to prevent timing attacks
@lru_cache(maxsize=128)
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
        # Validate email format
        validated_email = validate_email(email).email
        
        # Validate password strength
        if not is_strong_password(password):
            return False, "Password must be at least 8 characters with uppercase, lowercase, number and special character"
            
        # Hash password
        hashed_pw = get_hashed_password(password)
        
        # Generate verification token
        token = secrets.token_urlsafe(32)
        
        # Database operation
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users 
                (username, password, first_name, last_name, company_name, email, verification_token, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (username, hashed_pw, first_name, last_name, company, validated_email, token, tenant_id))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            
            # Send verification email
            send_verification_email(
                to_email=validated_email,
                username=first_name,
                token=token
            )
            
            return True, "Registration successful"
            
        except psycopg2.IntegrityError as e:
            conn.rollback()
            if "users_username_key" in str(e):
                return False, "Username already exists"
            elif "users_email_key" in str(e):
                return False, "Email already registered"
            return False, "Registration failed"
            
        finally:
            if conn: conn.close()
            
    except EmailNotValidError as e:
        return False, f"Invalid email: {str(e)}"

def authenticate_user(username: str, password: str) -> tuple:
    """Authenticate user with username and password"""
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
            return False, None, None
            
        user_id, stored_pw, role, is_verified, tenant_id = user
        
        # Check password
        if not bcrypt.checkpw(password.encode(), stored_pw.encode()):
            return False, None, None
            
        # Check verification status
        if not is_verified:
            return "unverified", None, None
            
        return True, role, tenant_id
        
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return False, None, None
    finally:
        if conn: conn.close()

def verify_token(token: str) -> dict:
    """Verify email verification token"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find user with this token
        cursor.execute("""
            SELECT id FROM users 
            WHERE verification_token = %s
        """, (token,))
        
        user = cursor.fetchone()
        if not user:
            return {"success": False, "error": "Invalid or expired token"}
            
        user_id = user[0]
        
        # Mark user as verified
        cursor.execute("""
            UPDATE users 
            SET is_verified = 1, 
                verification_token = NULL
            WHERE id = %s
        """, (user_id,))
        
        conn.commit()
        return {"success": True}
        
    except Exception as e:
        if conn: conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn: conn.close()

def resend_verification_email(username: str) -> dict:
    """Resend verification email to user"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user details
        cursor.execute("""
            SELECT id, email, first_name, is_verified, last_verification_sent 
            FROM users 
            WHERE username = %s
        """, (username,))
        
        user = cursor.fetchone()
        if not user:
            return {"success": False, "error": "User not found"}
            
        user_id, email, first_name, is_verified, last_sent = user
        
        # Check if already verified
        if is_verified:
            return {"success": False, "error": "User is already verified"}
        
        # Check resend cooldown (15 minutes)
        if last_sent and (datetime.utcnow() - last_sent) < timedelta(minutes=15):
            return {
                "success": False,
                "error": "Please wait 15 minutes before requesting another verification email"
            }
        
        # Generate new token
        new_token = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        
        # Update user record
        cursor.execute("""
            UPDATE users 
            SET verification_token = %s,
                last_verification_sent = %s
            WHERE id = %s
        """, (new_token, now, user_id))
        
        # Send verification email
        send_verification_email(
            to_email=email,
            username=first_name,
            token=new_token
        )
        
        conn.commit()
        return {"success": True}
        
    except Exception as e:
        if conn: conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn: conn.close()

def get_client_ip() -> str:
    """Get client IP address"""
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "unknown"