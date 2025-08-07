

import streamlit as st
import secrets
import smtplib
from email.message import EmailMessage
from db.database import get_db_connection
from datetime import datetime
from utils.email_utils import send_password_reset_email

def reset_password_request():
    st.title("🔑 Reset Your Password")

    email_input = st.text_input("Enter your account email")

    if st.button("Send Reset Link"):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email_input,))
        user = cursor.fetchone()

        if user:
            user_id = user[0]
            token = secrets.token_urlsafe(32)

            cursor.execute("""
                INSERT INTO password_resets (user_id, email, token)
                VALUES (?, ?, ?)
            """, (user_id, email_input, token))
            conn.commit()

            # Get username fron users table
            cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
            username = cursor.fetchone()[0]
            
            reset_link = f"http://localhost:8501/reset_password?token={token}"
            

            # Send email (replace with real email sending)
            try:
                send_password_reset_email(to_email=email_input, username=username, token=token)
                
            except Exception as e:
                st.warning("⚠️ Email sending failed. Use the link below:")
                st.code(reset_link)

        else:
            st.error("❌ Email not found.")

        conn.close()
