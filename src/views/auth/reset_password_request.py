import streamlit as st
import secrets
from db.database import get_db_connection
from utils.email_utils import send_password_reset_email
from utils.ui_helpers import show_toast

def reset_password_request():
    st.title("🔑 Password Recovery")
    
    with st.form("reset_request_form"):
        st.markdown("Enter your email address to receive a password reset link")
        email = st.text_input("Email Address", placeholder="your@email.com")
        
        if st.form_submit_button("Send Reset Link"):
            handle_reset_request(email)

def handle_reset_request(email):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("""
            SELECT id, username FROM users 
            WHERE email = %s
        """, (email,))
        user = cursor.fetchone()
        
        if not user:
            show_toast("Email not found", "error")
            return
            
        user_id, username = user
        token = secrets.token_urlsafe(32)
        
        # Delete any existing tokens for this user
        cursor.execute("""
            DELETE FROM password_resets 
            WHERE user_id = %s
        """, (user_id,))
        
        # Insert new token
        cursor.execute("""
            INSERT INTO password_resets (user_id, email, token)
            VALUES (%s, %s, %s)
        """, (user_id, email, token))
        
        conn.commit()
        
        # Send email (in production this would be async)
        send_password_reset_email(
            to_email=email,
            username=username,
            token=token
        )
        
        show_toast("Reset link sent to your email", "success")
        
    except Exception as e:
        if conn: conn.rollback()
        show_toast(f"Error: {str(e)}", "error")
    finally:
        if conn: conn.close()