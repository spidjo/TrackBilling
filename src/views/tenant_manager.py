# src/views/tenant_manager.py
import streamlit as st
from database import get_db_connection

def load_tenants():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, industry FROM tenants")
    rows = cursor.fetchall()
    conn.close()
    return rows

def create_tenant(name, industry):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tenants (name, industry) VALUES (?, ?)", (name, industry))
    conn.commit()
    conn.close()

def update_tenant(tenant_id, name, industry):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tenants SET name = ?, industry = ? WHERE id = ?", (name, industry, tenant_id))
    conn.commit()
    conn.close()

def tenant_manager():
    st.subheader("🏢 Tenant Management")

    if st.session_state.get("role") != "superadmin":
        st.warning("Access denied. SuperAdmin only.")
        st.stop()

    tenants = load_tenants()
    tenant_names = [t[1] for t in tenants]
    selected = st.selectbox("Select Tenant to Edit", ["-- New Tenant --"] + tenant_names)

    if selected != "-- New Tenant --":
        selected_index = tenant_names.index(selected)
        selected_id, selected_name, industry = tenants[selected_index]
    else:
        selected_id, selected_name, industry = None, "", ""

    name = st.text_input("Tenant Name", value=selected_name)
    industry_options = ["SaaS", "Cloud", "Telecom", "FinTech", "Fleet/Logistics", "Other"]
    default_index = industry_options.index(industry) if industry in industry_options else 0
    industry = st.selectbox("Industry", industry_options, index=default_index)

    if st.button("💾 Save Tenant"):
        if not name.strip():
            st.error("Tenant name is required.")
            return
        if selected_id:
            update_tenant(selected_id, name, industry)
            st.success("Tenant updated.")
        else:
            create_tenant(name, industry)
            st.success("Tenant created.")

    st.divider()
    st.markdown("### Existing Tenants")
    for tenant in tenants:
        st.markdown(f"- **{tenant[1]}** – {tenant[2]}")
