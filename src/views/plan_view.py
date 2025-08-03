import streamlit as st
from database import get_db_connection
from session import init_session_state

def manage_plans():
    init_session_state()

    if st.session_state.role != "superadmin":
        st.warning("Access denied. SuperAdmin only.")
        st.stop()

    st.subheader("📦 Manage Billing Plans")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Create new plan
    with st.form("new_plan"):
        st.markdown("### Create New Plan")
        name = st.text_input("Plan Name")
        monthly_fee = st.number_input("Monthly Fee", min_value=0.0)
        included_usage = st.number_input("Included Usage Units", min_value=0)
        overage_rate = st.number_input("Overage Rate (per unit)", min_value=0.0)
        tenant_id = st.text_input("Tenant ID")

        if st.form_submit_button("Add Plan"):
            cursor.execute("""
                INSERT INTO plans (name, monthly_fee, included_usage, overage_rate, tenant_id)
                VALUES (?, ?, ?, ?, ?)
            """, (name, monthly_fee, included_usage, overage_rate, tenant_id))
            conn.commit()
            st.success("Plan added.")

    # List existing plans
    st.markdown("### Existing Plans")
    rows = cursor.execute("SELECT id, name, monthly_fee, tenant_id FROM plans").fetchall()
    for row in rows:
        st.markdown(f"- **{row[1]}** – ${row[2]}/mo (Tenant: `{row[3]}`)")

    conn.close()
