
import bcrypt
import sqlite3
import secrets
import socket
from datetime import datetime, timedelta
from email_validator import validate_email, EmailNotValidError

from db.database import get_db_connection
from config import settings
from utils.email_service import send_verification_email

# Checks if a password meets strength requirements
def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 8 and
        any(c.islower() for c in password) and
        any(c.isupper() for c in password) and
        any(c.isdigit() for c in password) and
        any(c in "!@#$%^&*()-_=+[{]};:'\",<.>/?\\|" for c in password)
    )

# Registers a new user, validates email and password, hashes password, and sends verification email
def register_user(username, password, first_name, last_name, company, email, tenant_id):
    try:
        validated_email = validate_email(email).email
    except EmailNotValidError as e:
        return {"success": False, "error": f"Invalid email: {str(e)}"}

    if not is_strong_password(password):
        return {"success": False, "error": "Weak password."}

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    reg_date = datetime.utcnow().isoformat()
    token = secrets.token_urlsafe(32)

    conn = get_db_connection()
    cursor = conn.cursor()
    
    #get id from the tenants where name matches tenant_id
    cursor.execute("SELECT id FROM tenants WHERE name = ?", (tenant_id,))
    tenant = cursor.fetchone()
    if not tenant:
        return {"success": False, "error": "Invalid tenant."}
    tenant_id = tenant[0]

    try:
        cursor.execute("""
            INSERT INTO users (username, password, first_name, last_name, company_name, email, registration_date, verification_token, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, hashed_pw, first_name, last_name, company, validated_email, reg_date, token, tenant_id))
        conn.commit()
        send_verification_email(to_email=validated_email, username=first_name, token=token)

        return {"success": True, "token": token}
    except sqlite3.IntegrityError as e:
        # Handles duplicate username or email
        return {"success": False, "error": "Username or email already exists."}
    finally:
        conn.close()

# Authenticates a user by username and password, checks verification status
def authenticate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password, role, is_verified, tenant_id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user:
        user_id, stored_pw, role, is_verified, tenant_id = user
        if not is_verified:
            return "unverified", None, None
        if bcrypt.checkpw(password.encode(), stored_pw):
            return True, role, tenant_id
    return False, None, None

# Verifies a user's email using a token, updates verification status in the database
def verify_token(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE verification_token = ?", (token,))
    user = cursor.fetchone()

    if user:
        cursor.execute("""
            UPDATE users SET is_verified = 1, verification_token = NULL WHERE id = ?
        """, (user[0],))
        conn.commit()
        result = {"success": True}
    else:
        result = {"success": False, "error": "Invalid or expired token"}

    conn.close()
    return result

# Initializes session state for authentication
def get_client_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "unknown"

# Logs the attempt to resend verification email, including user ID, timestamp, IP address, status, and reason
def log_resend_attempt(user_id, status, reason=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO verification_resend_log (user_id, timestamp, ip_address, status, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        datetime.utcnow().isoformat(),
        get_client_ip(),
        status,
        reason
    ))
    conn.commit()
    conn.close()


# Resends a verification email if user exists and is not verified
def resend_verification_email(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, email, first_name, is_verified, last_verification_sent FROM users WHERE username = ?
    """, (username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return {"success": False, "error": "User not found."}

    user_id, email, first_name, is_verified, last_sent = user

    if is_verified:
        log_resend_attempt(user_id, "blocked", "Already verified")
        conn.close()
        return {"success": False, "error": "User is already verified."}

    # Enforce 1-hour resend limit
    if last_sent:
        try:
            last_time = datetime.fromisoformat(last_sent)
            if datetime.utcnow() - last_time < timedelta(minutes=1):
                remaining = timedelta(minutes=1) - (datetime.utcnow() - last_time)
                minutes = int(remaining.total_seconds() // 60)
                log_resend_attempt(user_id, "blocked", f"Resend too soon. Wait {minutes} mins")
                return {
                    "success": False,
                    "error": f"Please wait {minutes} more minutes before resending."
                }
        except Exception as e:
            log_resend_attempt(user_id, "error", f"Timestamp parse failed: {str(e)}")
            # fallback in case parsing fails
            pass

    token = secrets.token_urlsafe(32)
    now_iso = datetime.utcnow().isoformat()

    try:
        cursor.execute("""
            UPDATE users 
            SET verification_token = ?, last_verification_sent = ? 
            WHERE id = ?
        """, (token, now_iso, user_id))
        conn.commit()
        send_verification_email(to_email=email, username=first_name, token=token)
        log_resend_attempt(user_id, "sent", "Verification email sent")
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

