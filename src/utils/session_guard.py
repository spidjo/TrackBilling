# src/utils/session_guard.py
import streamlit as st

def require_login(role=None):
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("🚫 Please log in to access this page.")
        st.stop()
    if role and st.session_state.get("role") != role:
        st.warning(f"🚫 This page is only for '{role}' users.")
        st.stop()
