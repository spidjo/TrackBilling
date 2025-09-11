# src/utils/session_guard.py
import streamlit as st
from utils.session import validate_session

def require_login(required_role: str = None):
    """Ensure user is logged in and has required role"""
    def decorator(view_func):
        def wrapper(*args, **kwargs):
            if not validate_session():
                st.session_state.login_redirect = True
                st.rerun()
            
            if required_role and st.session_state.get("role") != required_role:
                st.error("You don't have permission to access this page")
                st.stop()
                
            return view_func(*args, **kwargs)
        return wrapper
    return decorator