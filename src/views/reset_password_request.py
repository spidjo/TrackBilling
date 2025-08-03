

import streamlit as st
import secrets
import smtplib
from email.message import EmailMessage
from database import get_db_connection
from datetime import datetime

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

            reset_link = f"http://localhost:8501/reset_password?token={token}"
            st.success("✅ Reset link sent to your email!")

            # Send email (replace with real email sending)
            try:
                msg = EmailMessage()
                msg["Subject"] = "Your Password Reset Link"
                msg["From"] = "no-reply@billing-saas.com"
                msg["To"] = email_input
                msg.set_content(f"Click below to reset your password:\n{reset_link}")

                with smtplib.SMTP("localhost") as smtp:
                    smtp.send_message(msg)
            except Exception as e:
                st.warning("⚠️ Email sending failed. Use the link below:")
                st.code(reset_link)

        else:
            st.error("❌ Email not found.")

        conn.close()
