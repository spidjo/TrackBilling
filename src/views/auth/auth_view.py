# src/views/auth_view.py

import streamlit as st
import os
import requests
from auth_manager import register_user, authenticate_user, verify_token, resend_verification_email
from utils.session import init_session_state
from db.database import get_db_connection
from utils.login_attempts import is_rate_limited
from streamlit_js_eval import streamlit_js_eval

RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")

def auth_view():
    st.title("🔐 Authentication")

    tabs = st.tabs(["Login", "Register", "Reset Password"])
    tab_login, tab_register, tab_reset = tabs

    # --- Login Tab ---
    with tab_login:
        st.subheader("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        st.markdown("[Forgot your password? Click here to reset.](?reset=1)")

        # --- CAPTCHA Integration ---
        st.markdown("""
            <script src="https://www.google.com/recaptcha/api.js?onload=onloadCallback&render=explicit" async defer></script>
            <div id="recaptcha-container"></div>
            <script>
                function onSubmit(token) {
                    window.__last_recaptcha_token = token;
                }

                var onloadCallback = function() {
                    grecaptcha.render('recaptcha-container', {  
                        'sitekey' : '%s',
                        'callback' : onSubmit
                    });
                };
            </script>
        """ % RECAPTCHA_SITE_KEY, unsafe_allow_html=True)

        # --- Evaluate the token from frontend
        token_from_js = streamlit_js_eval(js_expressions="window.__last_recaptcha_token", key="captcha_eval")

        # --- Fallback manual entry
        captcha_token_manual = st.text_input("Captcha Token (Paste here if blocked)", key="captcha_token")

        # --- Session defaults
        st.session_state.setdefault("login_attempted", False)
        st.session_state.setdefault("login_result", None)
        st.session_state.setdefault("username_temp", None)
        st.session_state.setdefault("tenant_id_temp", None)
        st.session_state.setdefault("role_temp", None)

        # --- Login Button ---
        if st.button("Login"):
            if is_rate_limited(username):
                st.error("🚫 Too many login attempts. Please try again later.")
                return

            token = token_from_js or captcha_token_manual
            if not token or not validate_captcha(token):
                st.error("❌ CAPTCHA validation failed. Please try again.")
                return

            result, role, tenant_id = authenticate_user(username, password)
            st.session_state.login_attempted = True
            st.session_state.login_result = result
            st.session_state.username_temp = username
            st.session_state.tenant_id_temp = tenant_id
            st.session_state.role_temp = role
            st.rerun()

        # --- Post-login feedback ---
        if st.session_state.login_attempted:
            result = st.session_state.login_result
            username = st.session_state.username_temp
            tenant_id = st.session_state.tenant_id_temp
            role = st.session_state.role_temp

            if result == "unverified":
                st.warning("⚠️ Your account is not verified. Please check your email.")
                if st.button("Resend Verification Email"):
                    resend_result = resend_verification_email(username)
                    if resend_result["success"]:
                        st.success("📨 Verification email resent. Please check your inbox.")
                    else:
                        st.error(f"Error: {resend_result['error']}")
            elif result is True:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = role
                st.session_state.tenant_id = tenant_id
                st.session_state.user = {
                    "username": username,
                    "role": role,
                    "tenant_id": tenant_id
                }
                st.success("✅ Login successful.")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

    # --- Register Tab ---
    with tab_register:
        st.subheader("Register")
        reg_username = st.text_input("Username", key="reg_username")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        reg_email = st.text_input("Email", key="reg_email")
        reg_client_name = st.text_input("Client Name", key="reg_client")
        reg_company = st.text_input("Company", key="reg_company")

        if st.button("Register"):
            success, message = register_user(
                username=reg_username,
                password=reg_password,
                email=reg_email,
                client_name=reg_client_name,
                company_name=reg_company
            )
            if success:
                st.success("✅ Registration successful. Please check your email to verify your account.")
            else:
                st.error(f"❌ Registration failed: {message}")

    # --- Reset Password Tab ---
    with tab_reset:
        st.subheader("Reset Password")
        reset_email = st.text_input("Email Address", key="reset_email")

        if st.button("Request Reset Link"):
            success = request_password_reset(reset_email)
            if success:
                st.success("📨 Password reset link sent. Check your email.")
            else:
                st.error("❌ Unable to send reset email. Please check the email address.")

        reset_token = st.text_input("Reset Token", key="reset_token")
        new_password = st.text_input("New Password", type="password", key="new_password")

        if st.button("Reset Password"):
            success = reset_password(reset_token, new_password)
            if success:
                st.success("✅ Password successfully reset. You can now log in.")
            else:
                st.error("❌ Invalid or expired reset token.")
