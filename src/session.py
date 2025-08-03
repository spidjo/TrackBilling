import streamlit as st

def init_session_state():
    defaults = {
        "authenticated": False,
        "username": None,
        "role": None,
        "tenant_id": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value