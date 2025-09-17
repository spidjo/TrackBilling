# auth_view.py
import time
import streamlit as st
import psycopg2.extras
import logging
from auth_manager import (
    register_user,
    authenticate_user,
    verify_token,
    resend_verification_email
)
from main import LIGHT_THEME, DARK_THEME
from utils.session import init_session_state
from db.database import get_db_connection
from utils.login_attempts import is_rate_limited
import base64

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_logo_base64():
    # Replace with your actual logo path or base64 encoded string
    logo_path = "logo.png"  # Placeholder
    try:
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

def apply_auth_theme(theme):
    st.markdown(f"""
    <style>
        .auth-container {{
            max-width: 500px;
            margin: 2rem auto;
            padding: 2.5rem;
            border-radius: 12px;
            background-color: {theme["CARD"]};
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }}
        
        .stButton>button {{
            width: 100%;
            border-radius: 8px;
            padding: 0.75rem;
            background-color: {theme["ACCENT"]};
            color: white;
            border: none;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .stButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px {theme["ACCENT"]}40;
        }}
        
        .stTextInput>div>div>input, .stSelectbox>div>div>select {{
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid {theme["SECONDARY"]};
        }}
        
        .stTabs > div > div > button {{
            color: {theme["TEXT"]};
            padding: 0.5rem 1rem;
        }}
        
        .stTabs > div > div > button[aria-selected="true"] {{
            color: {theme["ACCENT"]};
            font-weight: 600;
            border-bottom: 2px solid {theme["ACCENT"]};
        }}
        
        .password-strength {{
            margin-top: -15px;
            margin-bottom: 15px;
        }}
        
        .password-bar {{
            height: 6px;
            background: #eee;
            border-radius: 5px;
            margin-top: 5px;
        }}
        
        .password-label {{
            text-align: center;
            font-size: 0.8rem;
            margin-top: 3px;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .auth-transition {{
            animation: fadeIn 0.5s ease-out;
        }}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_tenants():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT name, id FROM tenants ORDER BY name")
    tenants = cursor.fetchall()
    conn.close()
    return tenants

def auth_view():
    logger.info(f"Session state at start: {dict(st.session_state)}")
    
    init_session_state()
    
    logger.info(f"Session state after init: {dict(st.session_state)}")
    
    # Theme setup
    dark_mode = st.session_state.get("dark_mode", False)
    theme = DARK_THEME if dark_mode else LIGHT_THEME
    apply_auth_theme(theme)
    
    # Logo
    logo_base64 = get_logo_base64()
    
    # Main container with animation
    st.markdown('<div class="auth-transition">', unsafe_allow_html=True)
    
    # Center the auth form
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        if logo_base64:
            st.markdown(
                f'<div style="text-align: center; margin-bottom: 2rem;">'
                f'<img src="data:image/png;base64,{logo_base64}" style="max-width: 200px;">'
                f'</div>',
                unsafe_allow_html=True
            )
        
        st.markdown(f'<h1 style="text-align: center; color: {theme["TEXT"]};">🔐 SglTrack SaaS Billing Platform</h1>', 
                   unsafe_allow_html=True)
        
        tabs = st.tabs(["Login", "Register"])
        
        # --- Login Tab ---
        with tabs[0]:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                login_submitted = st.form_submit_button("Login", type="primary")

                st.markdown(
                        f"""<div style="text-align: right; margin: 1rem 0 1.5rem 0;">
                        <a href="/reset_password_request?reset=1" target="_self" 
                        style="color: {theme["ACCENT"]}; text-decoration: none;">
                            Forgot password?
                        </a>
                        </div>""",
                        unsafe_allow_html=True
                    )
            # --- Handle login result ---
            if login_submitted:
                handle_login(username, password)

            # --- Render resend button for unverified users ---
            if "unverified_user" in st.session_state:
                unverified_username = st.session_state["unverified_user"]
                logger.info(f"Rendering resend button for: {unverified_username}")
                
                resend_key = f"resend_{unverified_username}"
                resend_clicked = st.button(
                    "📨 Resend Verification Email",
                    key=resend_key
                )
                logger.info(f"Button created with key: {resend_key}, clicked: {resend_clicked}")
                
                if resend_clicked:
                    logger.info(f"Resend verification email button CLICKED for: {unverified_username}")
                    logger.info(f"Resend verification email requested for: {unverified_username}")
                    with st.spinner("Sending verification email..."):
                        resend_result = resend_verification_email(unverified_username)
                    if resend_result.get("success"):
                        st.success("✅ Verification email resent. Please check your inbox.")
                        logger.info(f"Verification email resent successfully for: {unverified_username}")
                    else:
                        error_msg = resend_result.get("error", "Unknown error")
                        st.error(f"❌ Error: {error_msg}")
                        logger.error(f"Failed to resend verification email for {unverified_username}: {error_msg}")
        
        # --- Register Tab ---
        with tabs[1]:
            with st.form("register_form", clear_on_submit=False):
                st.markdown(f'<h3 style="color: {theme["TEXT"]};">Create Account</h3>', 
                          unsafe_allow_html=True)
                
                cols = st.columns(2)
                with cols[0]:
                    first_name = st.text_input("First Name", key="reg_first_name")
                with cols[1]:
                    last_name = st.text_input("Last Name", key="reg_last_name")
                
                reg_username = st.text_input("Username", key="reg_username")
                reg_email = st.text_input("Email", key="reg_email")
                reg_company = st.text_input("Company", key="reg_company")
                
                reg_password = st.text_input("Password", type="password", key="reg_password")
                if reg_password:
                    show_password_strength(reg_password, theme)
                
                tenants = fetch_tenants()
                tenant_names = [t['name'] for t in tenants] if tenants else []
                reg_tenant = st.selectbox("Select Tenant", options=tenant_names, key="reg_tenant")
                reg_tenant_id = next((t['id'] for t in tenants if t['name'] == reg_tenant), None)
                
                if st.form_submit_button("Register", type="primary"):
                    with st.spinner("Creating your account..."):
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
                        for key in ["reg_first_name", "reg_last_name", "reg_username", "reg_email", "reg_company", "reg_password", "reg_tenant"]:
                            if key in st.session_state:
                                del st.session_state[key]
                    else:
                        st.error(f"❌ Registration failed: {message}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- handle login ---
def handle_login(username, password):
    logger.info(f"Login attempt for user: {username}")
    if is_rate_limited(username):
        st.error("🚫 Too many login attempts. Please try again later.")
        return

    with st.spinner("Authenticating..."):
        result, role, tenant_id, user_id = authenticate_user(username, password) 

    # store unverified state
    if result == "unverified":
        st.session_state["unverified_user"] = username
        st.warning("⚠️ Your account is not verified. Please check your email.")
    elif result is True:
        st.session_state.update({
            "authenticated": True,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "username": username,
            "role": role,
            "last_activity": time.time(),
            "session_start": time.time(),
            "login_redirect": False
        })
        st.success("✅ Login successful. Redirecting...")
        time.sleep(1)
        st.rerun()
    else:
        st.error("❌ Invalid username or password.")

def show_password_strength(password, theme):
    """Visual feedback for password strength"""
    strength = 0
    if len(password) >= 8: strength += 1
    if any(c.islower() for c in password): strength += 1
    if any(c.isupper() for c in password): strength += 1 
    if any(c.isdigit() for c in password): strength += 1
    if any(c in "!@#$%^&*()-_=+" for c in password): strength += 1
    
    colors = [
        theme["ERROR"], 
        "#ffa700", 
        "#ffa700", 
        theme["SUCCESS"], 
        theme["SUCCESS"]
    ]
    labels = ["Very Weak", "Weak", "Moderate", "Strong", "Very Strong"]
    
    st.markdown(f"""
        <div class="password-strength">
            <div class="password-bar">
                <div style="width: {strength * 20}%; height: 100%; 
                          background: {colors[strength-1]}; 
                          border-radius: 5px;"></div>
            </div>
            <div class="password-label" style="color: {colors[strength-1]}">
                {labels[strength-1]}
            </div>
        </div>
    """, unsafe_allow_html=True)