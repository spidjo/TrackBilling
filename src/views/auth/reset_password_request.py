# src/views/auth/reset_password_request.py
import streamlit as st
import secrets
from datetime import datetime, timedelta, timezone
from db.database import get_db_connection
from utils.email_utils import send_password_reset_email
from utils.ui_helpers import show_toast, loading_spinner

def reset_password_request():
    st.title("🔑 Password Recovery")
    
    with st.form("reset_request_form"):
        st.markdown("Enter your email address to receive a password reset link!")
        email = st.text_input("Email Address", placeholder="your@email.com")
        
        if st.form_submit_button("Send Reset Link"):
            handle_reset_request(email)

def handle_reset_request(email: str) -> None:
    email: str = email.strip().lower()
    if not email:
        show_toast("Please enter your email", "error")
        return
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("""
            SELECT id, username FROM users WHERE email = %s
        """, (str(email),))
        user = cursor.fetchone()
        
        if not user:
            show_toast("Email not found", "error")
            return
        
        user_id, username = user
        
        # Remove existing password reset tokens for this user (clean slate)
        cursor.execute("DELETE FROM password_resets WHERE user_id = %s", (int(user_id),))
        
        # Generate new token and expiry (1 hour validity)
        token: str = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Insert new password reset token
        cursor.execute("""
            INSERT INTO password_resets (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (int(user_id), str(token), expires_at))
        
        conn.commit()
        
        # Send reset email
        with loading_spinner("Sending reset email..."):
            send_password_reset_email(
                to_email=str(email),
                username=str(username),
                token=str(token)
            )
        
        st.success("✅ Password reset link sent. Please check your email.")
    
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Error sending reset link: {str(e)}")
    finally:
        if conn:
            conn.close()