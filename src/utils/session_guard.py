# src/utils/session_guard.py
import streamlit as st

# Pass more that one role to the require_login function
def require_login(*roles):
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("🚫 Please log in to access this page.")
        st.stop()
    if roles and st.session_state.get("role") not in roles:
        st.warning(f"🚫 This page is only for {', '.join(roles)} users.")
        st.stop()
