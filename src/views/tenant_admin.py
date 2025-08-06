# src/views/tenant_admin.py

import streamlit as st
import sqlite3
import uuid
from db.database import get_db_connection

def manage_tenants():
    st.subheader("🔧 Manage Tenants")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Add tenant
    with st.form("add_tenant"):
        st.markdown("### Add New Tenant")
        tenant_id = str(uuid.uuid4())
        name = st.text_input("Company Name")
        industry = st.selectbox("Industry", ["SaaS", "Cloud", "Telecom", "FinTech", "Fleet/Logistics", "Other"])
        submitted = st.form_submit_button("Add Tenant")

        if submitted:
            try:
                cursor.execute(
                    "INSERT INTO tenants (id, name, industry) VALUES (?, ?, ?)",
                    (tenant_id, name, industry)
                )
                conn.commit()
                st.success("Tenant added.")
            except sqlite3.IntegrityError:
                st.error("Tenant ID already exists.")

    # List tenants
    st.markdown("### Registered Tenants")
    tenants = cursor.execute("SELECT id, name, industry, created_at FROM tenants").fetchall()
    for tid, name, industry, created in tenants:
        st.markdown(f"- **{name}** ({industry}) – ID: `{tid}` | Created: {created}")

    conn.close()
