import streamlit as st
from auth_manager import verify_token

st.set_page_config(page_title="Verify Email", page_icon="✉️")

st.title("Email Verification")

# Read token from query parameters
token = st.query_params.get("token", [None])[0]

if not token:
    st.error("❌ Invalid or missing verification token.")
else:
    result = verify_token(token)
    if result.get("success"):
        st.success("✅ Your email has been verified! You can now log in.")
        st.page_link("Login", label="Go to Login", icon="➡️")
    else:
        st.error(f"❌ Verification failed: {result.get('error')}")