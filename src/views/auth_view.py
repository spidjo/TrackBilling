# src/views/auth_view.py

import streamlit as st
from auth_manager import register_user, authenticate_user, verify_token
from session import init_session_state
from database import get_db_connection

def get_available_tenants():
    conn = get_db_connection()
    cursor = conn.cursor()
    tenants = cursor.execute("SELECT id, name FROM tenants").fetchall()
    conn.close()
    return tenants

def auth_view():
    init_session_state()

    query_params = st.query_params
    if "verify" in query_params:
        result = verify_token(query_params["verify"])
        if result["success"]:
            st.success("✅ Email verified! You may now log in.")
        else:
            st.error(result["error"])
        st.query_params.clear()

    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

    with tab_login:
        st.subheader("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        st.markdown("[Forgot your password? Click here to reset.](?reset=1)")   
        if st.button("Login"):
            result, role, tenant_id = authenticate_user(username, password)
            if result:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = role
                st.session_state.tenant_id = tenant_id
                st.success("✅ Login successful.")
                st.rerun()
            else:
                st.error("Invalid username or password.")
        
        
    with tab_register:
        st.subheader("Register")
        new_username = st.text_input("Username", key="reg_username")
        new_password = st.text_input("Password", type="password", key="reg_password")
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        company = st.text_input("Company")
        email = st.text_input("Email")
        
        tenants = get_available_tenants()
        tenant_options = {name: tid for tid, name in tenants}
        selected_tenant = st.selectbox("Select Your Company", list(tenant_options.keys()))

        if st.button("Register"):
            if not all([new_username, new_password, first_name, last_name, company, email, selected_tenant]):
                st.warning("All fields are required.")
            else:
                result = register_user(new_username, new_password, first_name, last_name, company, email, selected_tenant)
                if result["success"]:
                    st.success("✅ Registration successful. Please check your email to verify.")
                else:
                    st.error(result["error"])
