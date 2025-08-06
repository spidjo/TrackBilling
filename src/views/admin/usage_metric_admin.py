# views/admin/usage_metric_admin.py

import streamlit as st
from db.database import get_db_connection
from utils.session_guard import require_login

def usage_metric_admin():
    require_login('admin')
    st.title("📊 Manage Usage Metrics")

    user = st.session_state.get("user")
    tenant_id = user["tenant_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    st.subheader("➕ Add New Metric")
    with st.form("add_metric_form"):
        name = st.text_input("Metric Name (e.g., API Calls, Seats)")
        unit = st.text_input("Unit (e.g., requests, users)")
        submitted = st.form_submit_button("Add Metric")
        if submitted:
            if not name or not unit:
                st.warning("Both name and unit are required.")
            else:
                try:
                    cursor.execute("INSERT INTO usage_metrics (tenant_id, name, unit) VALUES (?, ?, ?)", (tenant_id, name.strip(), unit.strip()))
                    conn.commit()
                    st.success(f"✅ Metric '{name}' added.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    st.subheader("📋 Existing Metrics")
    cursor.execute("SELECT id, name, unit FROM usage_metrics WHERE tenant_id = ?", (tenant_id,))
    metrics = cursor.fetchall()

    if metrics:
        for mid, name, unit in metrics:
            col1, col2, col3 = st.columns([3, 3, 2])
            col1.markdown(f"**{name}**")
            col2.markdown(f"Unit: `{unit}`")
            if col3.button("🗑 Delete", key=f"delete_{mid}"):
                cursor.execute("DELETE FROM usage_metrics WHERE id = ?", (mid,))
                conn.commit()
                st.success(f"Metric '{name}' deleted.")
                st.rerun()
    else:
        st.info("No metrics defined for your tenant.")

    conn.close()
