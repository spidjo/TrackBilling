# src/utils/validation.py
import streamlit as st
from typing import Optional, Tuple
import time
from db.database import get_db_connection  
from utils.ui_helpers import display_error

def validate_user_session() -> bool:
    """
    Validate the current user session with comprehensive checks.
    
    Returns:
        bool: True if session is valid, False otherwise
    """
    required_keys = {
        "authenticated": bool,
        "user_id": (int, str),
        "username": str,
        "tenant_id": (int, str),
        "role": str
    }
    
    # Check if all required keys exist and have correct types
    for key, expected_type in required_keys.items():
        if key not in st.session_state:
            display_error(f"Session validation failed: Missing {key}")
            return False
        
        if not isinstance(st.session_state[key], expected_type):
            display_error(f"Session validation failed: Invalid type for {key}")
            return False
    
    # Additional validation checks
    if not st.session_state["authenticated"]:
        display_error("Session validation failed: Not authenticated")
        return False
    
    if not st.session_state["username"] or not st.session_state["tenant_id"]:
        display_error("Session validation failed: Missing user identifiers")
        return False
    
    return True

def validate_db_connection(conn) -> bool:
    """
    Validate a database connection is active and working.
    
    Args:
        conn: Database connection object
        
    Returns:
        bool: True if connection is valid, False otherwise
    """
    if conn is None:
        display_error("Database connection failed: No connection established")
        return False
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone()[0] == 1
    except Exception as e:
        display_error(f"Database connection validation failed: {str(e)}")
        return False

def validate_db_user_exists(username: str) -> Tuple[bool, Optional[int]]:
    """
    Validate that a user exists in the database and return their ID.
    
    Args:
        username: Username to validate
        
    Returns:
        Tuple[bool, Optional[int]]: (True, user_id) if valid, (False, None) if not
    """
    try:
        conn = get_db_connection()
        if not validate_db_connection(conn):
            return False, None
            
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            return (True, result[0]) if result else (False, None)
    except Exception as e:
        display_error(f"User validation failed: {str(e)}")
        return False, None
    finally:
        if conn:
            conn.close()

def validate_tenant_access(user_id: int, tenant_id: int) -> bool:
    """
    Validate that a user has access to the specified tenant.
    
    Args:
        user_id: User ID to validate
        tenant_id: Tenant ID to check access for
        
    Returns:
        bool: True if access is valid, False otherwise
    """
    try:
        conn = get_db_connection()
        if not validate_db_connection(conn):
            return False
            
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 1 FROM user_tenants 
                WHERE user_id = %s AND tenant_id = %s
            """, (user_id, tenant_id))
            return cursor.fetchone() is not None
    except Exception as e:
        display_error(f"Tenant access validation failed: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()