
import bcrypt
import sqlite3
import secrets
import datetime
from email_validator import validate_email, EmailNotValidError

from database import get_db_connection
from config import settings
from email_service import send_verification_email

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
    reg_date = datetime.date.today().isoformat()
    token = secrets.token_urlsafe(32)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (username, password, first_name, last_name, company_name, email, registration_date, verification_token, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, hashed_pw, first_name, last_name, company, validated_email, reg_date, token, tenant_id))
        conn.commit()
        send_verification_email(to_email=validated_email, token=token, first_name=first_name)

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