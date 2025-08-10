# src/views/auth_view.py
import streamlit as st
import os
import psycopg2.extras
from auth_manager import (
    register_user,
    authenticate_user,
    verify_token,
    resend_verification_email
)
from utils.session import init_session_state
from db.database import get_db_connection
from utils.login_attempts import is_rate_limited
from utils.ui_helpers import center_form, show_form_errors, loading_spinner

def auth_view():
    # Initialize session state
    init_session_state()
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
            .auth-container {
                max-width: 500px;
                margin: 0 auto;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .stButton>button {
                width: 100%;
                border-radius: 5px;
                padding: 0.5rem;
            }
            .stTextInput>div>div>input {
                padding: 0.5rem;
            }
            .tab-content {
                padding: 1rem 0;
            }
            .error-message {
                color: #ff4b4b;
                font-size: 0.9rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔐 Account Authentication")
    
    # Use columns to center the auth form
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        with st.container():
            tabs = st.tabs(["Login", "Register"])
            
            # --- Login Tab ---
            with tabs[0]:
                with st.form("login_form"):
                    st.subheader("Welcome Back")
                    username = st.text_input("Username", key="login_username")
                    password = st.text_input("Password", type="password", key="login_password")
                    
                    # Forgot password link
                    st.markdown(
                        """<div style="text-align: right; margin-bottom: 1rem;">
                        <a href="/reset_password_request?reset=1" target="_self">Forgot password?</a>
                        </div>""",
                        unsafe_allow_html=True
                    )
                    
                    login_button = st.form_submit_button("Login")
                    
                    if login_button:
                        handle_login(username, password)
            
            # --- Register Tab ---
            with tabs[1]:
                registration_form = st.form("register_form")
                with registration_form:
                    st.subheader("Create Account")
                    cols = st.columns(2)
                    with cols[0]:
                        first_name = st.text_input("First Name", key="reg_first_name")
                    with cols[1]:
                        last_name = st.text_input("Last Name", key="reg_last_name")
                    
                    reg_username = st.text_input("Username", key="reg_username")
                    reg_email = st.text_input("Email", key="reg_email")
                    reg_company = st.text_input("Company", key="reg_company")
                    
                    # Password with strength meter
                    reg_password = st.text_input("Password", type="password", key="reg_password")
                    if reg_password:
                        show_password_strength(reg_password)
                    
                    # Tenant selection
                    conn = get_db_connection()
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                    cursor.execute("SELECT name, id FROM tenants")
                    tenants = cursor.fetchall()
                    tenant_names = [t['name'] for t in tenants] if tenants else []
                    reg_tenant = st.selectbox("Select Tenant", options=tenant_names, key="reg_tenant")
                    reg_tenant_id = next((t['id'] for t in tenants if t['name'] == reg_tenant), None)
                    conn.close()
                    
                    if st.form_submit_button("Register"):
                        with loading_spinner("Creating your account..."):
                            success, message = register_user(
                                username=reg_username,
                                password=reg_password,
                                email=reg_email,
                                first_name=first_name,
                                last_name=last_name,
                                company=reg_company,
                                tenant_id=reg_tenant_id
                            )
                            
                        if success:
                            st.success("✅ Registration successful. Please check your email to verify your account.")
                            # Clear form fields after successful registration
                            registration_form.form_submit_button("Register")  # This resets the form
                        else:
                            st.error(f"❌ Registration failed: {message}")

def handle_login(username, password):
    if is_rate_limited(username):
        st.error("🚫 Too many login attempts. Please try again later.")
        return
    
    with loading_spinner("Authenticating..."):
        result, role, tenant_id = authenticate_user(username, password)
    
    if result == "unverified":
        st.warning("⚠️ Your account is not verified. Please check your email.")
        if st.button("Resend Verification Email"):
            with loading_spinner("Sending verification email..."):
                resend_result = resend_verification_email(username)
            if resend_result["success"]:
                st.success("📨 Verification email resent. Please check your inbox.")
            else:
                st.error(f"Error: {resend_result['error']}")
    elif result is True:
        st.session_state.update({
            "authenticated": True,
            "username": username,
            "role": role,
            "tenant_id": tenant_id,
            "user": {"username": username, "role": role, "tenant_id": tenant_id}
        })
        st.success("✅ Login successful. Redirecting...")
        st.rerun()
    else:
        st.error("❌ Invalid username or password.")

def show_password_strength(password):
    """Visual feedback for password strength"""
    strength = 0
    if len(password) >= 8: strength += 1
    if any(c.islower() for c in password): strength += 1
    if any(c.isupper() for c in password): strength += 1 
    if any(c.isdigit() for c in password): strength += 1
    if any(c in "!@#$%^&*()-_=+" for c in password): strength += 1
    
    colors = ["#ff4b4b", "#ffa700", "#ffa700", "#2ecc71", "#2ecc71"]
    labels = ["Very Weak", "Weak", "Moderate", "Strong", "Very Strong"]
    
    st.markdown(f"""
        <div style="margin-top: -15px; margin-bottom: 15px;">
            <div style="height: 5px; background: #eee; border-radius: 5px;">
                <div style="width: {strength * 20}%; height: 100%; background: {colors[strength-1]}; border-radius: 5px;"></div>
            </div>
            <div style="text-align: center; font-size: 0.8rem; color: {colors[strength-1]}">
                {labels[strength-1]}
            </div>
        </div>
    """, unsafe_allow_html=True)    