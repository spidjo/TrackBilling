# views/invoice_preview.py

import streamlit as st
import sqlite3
from datetime import datetime
from utils.session_guard import require_login
from billing_engine import estimate_invoice_for_user

def invoice_preview():
    user = st.session_state.get("user")
    if not user:
        st.stop()
    st.title("🧾 Invoice Preview")
    user_id = user["username"]
    tenant_id = user["tenant_id"]

    if not user_id or not tenant_id:
        st.warning("User or tenant info missing.")
        return

    with st.expander("Preview this month's estimated invoice"):
        estimated_items, total = estimate_invoice_for_user(user_id, tenant_id)

        if estimated_items:
            for item in estimated_items:
                st.write(f"- **{item['description']}**: {item['quantity']} @ {item['unit_price']} = {item['total_price']}")
            st.success(f"💰 Estimated Total: **${total:.2f}**")
        else:
            st.info("No billable usage this month.")
