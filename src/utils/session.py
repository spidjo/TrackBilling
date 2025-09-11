# src/utils/session.py
import streamlit as st
import time
from utils.ui_helpers import display_error
from utils.validation import validate_db_connection, validate_db_user_exists
from db.database import get_db_connection  

def init_session_state():
    """Initialize all required session state variables with defaults"""
    defaults = {
        "authenticated": False,
        "user_id": None,
        "username": None,
        "role": None,
        "tenant_id": None,
        "last_activity": None,
        "session_start": None,
        "login_redirect": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def validate_session(max_inactive_minutes: int = 30) -> bool:
    """
    Validate the current session with comprehensive checks.
    
    Args:
        max_inactive_minutes: Maximum allowed inactive time (default: 30)
        
    Returns:
        bool: True if session is valid, False otherwise
    """
    # Basic authentication check
    if not st.session_state.get("authenticated"):
        handle_session_expired("Session not authenticated")
        return False
    
    # Validate user exists in database
    username = st.session_state.get("username")
    if username:
        user_valid, user_id = validate_db_user_exists(username)
        if not user_valid or user_id != st.session_state.get("user_id"):
            handle_session_expired("User validation failed")
            return False
    
    # Validate database connection
    if not validate_db_connection(get_db_connection()):
        handle_session_expired("Database connection failed")
        return False
    
    # Check session activity timeout
    current_time = time.time()
    last_activity = st.session_state.get("last_activity", current_time)
    
    if current_time - last_activity > max_inactive_minutes * 60:
        handle_session_expired("Session expired due to inactivity")
        return False
    
    # Update last activity timestamp
    st.session_state["last_activity"] = current_time
    return True

def handle_session_expired(reason: str):
    """Handle session expiration and redirect to login"""
    # Clear sensitive session data
    st.session_state.update({
        "authenticated": False,
        "user_id": None,
        "username": None,
        "tenant_id": None,
        "login_redirect": True,
        "session_expired_reason": reason
    })
    
    # Show error message if on a page that renders UI
    if not st.runtime.exists():
        display_error("Session expired or invalid. Please log in again.", 
                     details=reason)
        
    # Force a rerun to trigger redirect
    st.rerun()

def login_required(role: str = None):
    """
    Decorator to enforce login and optional role-based access.
    
    Args:
        role: Optional required role for access
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not validate_session():
                st.stop()
            
            if role and st.session_state.get("role") != role:
                display_error(f"Access denied: Requires {role} role")
                st.stop()
                
            return func(*args, **kwargs)
        return wrapper
    return decorator