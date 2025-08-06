# src/views/reset_password.py

import streamlit as st
from db.database import get_db_connection
from werkzeug.security import generate_password_hash
from urllib.parse import parse_qs
import time

def reset_password():
    st.title("🔐 Create a New Password")

    query_params = st.query_params
    token = query_params.get("token", [None])[0]

    if not token:
        st.error("❌ Invalid or missing token.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id FROM password_resets
        WHERE token = ? AND is_used = 0
        AND datetime(created_at) >= datetime('now', '-30 minutes')
    """, (token,))
    row = cursor.fetchone()

    if not row:
        st.error("⏳ Token is expired or invalid.")
        return

    user_id = row[0]
    new_pass = st.text_input("New Password", type="password")
    confirm_pass = st.text_input("Confirm Password", type="password")

    if st.button("Update Password"):
        if new_pass != confirm_pass:
            st.error("❌ Passwords do not match.")
        elif len(new_pass) < 8:
            st.error("🔐 Password must be at least 8 characters.")
        else:
            hashed = generate_password_hash(new_pass)
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
            cursor.execute("UPDATE password_resets SET is_used = 1 WHERE token = ?", (token,))
            conn.commit()
            st.success("✅ Password updated! Redirecting to login...")
            time.sleep(2)
            st.query_params.clear()  # ✅ Clears token param
            st.rerun()


    conn.close()
