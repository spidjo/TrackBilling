import streamlit as st
import bcrypt
from datetime import datetime, timezone
from db.database import get_db_connection
from utils.ui_helpers import show_toast, validate_password

def reset_password():
    st.title("🔐 Set New Password")
    
    params = st.query_params
    token = params.get("token")
    
    if not token:
        st.error("Invalid or missing token")
        return
        
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Validate token
        cursor.execute("""
            SELECT user_id FROM password_resets
            WHERE token = %s 
            AND is_used = false
            AND expires_at >= current_timestamp
        """, (token,))
        
        
        result = cursor.fetchone()
        if not result:
            st.error("Invalid or expired token")
            return
            
        user_id = result[0]
        
        with st.form("reset_password_form"):
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Update Password"):
                if new_password != confirm_password:
                    show_toast("Passwords don't match", "error")
                elif not validate_password(new_password):
                    show_toast("Password doesn't meet requirements", "error")
                else:
                    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
                    cursor.execute("""
                        UPDATE users 
                        SET password = %s 
                        WHERE id = %s
                    """, (hashed.decode('utf-8'), user_id))
                    
                    cursor.execute("""
                        UPDATE password_resets
                        SET is_used = True
                        WHERE token = %s
                    """, (token,))
                    
                    conn.commit()
                    show_toast("Password updated successfully!", "success")
                    st.balloons()
                    # Redirect to login page after reset
                    st.query_params.clear()  # clear token param
                    st.rerun()
                    
    except Exception as e:
        if conn: conn.rollback()
        show_toast(f"Error: {str(e)}", "error")
    finally:
        if conn: conn.close()
