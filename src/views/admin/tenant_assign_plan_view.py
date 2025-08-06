import streamlit as st
from db.database import get_db_connection
from utils.session import init_session_state

def assign_plans():
    init_session_state()

    if st.session_state.role not in ["admin", "tenantadmin", "superadmin"]:
        st.warning("Access denied. Only tenant administrators can assign plans.")
        st.stop()

    tenant_id = st.session_state.tenant_id
    st.subheader("🏷️ Assign Plans to Users")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get users in the same tenant
    users = cursor.execute("""
        SELECT username FROM users WHERE tenant_id = ?
    """, (tenant_id,)).fetchall()
    usernames = [u[0] for u in users]

    # Get available plans for this tenant
    plans = cursor.execute("""
        SELECT id, name FROM plans WHERE tenant_id = ?
    """, (tenant_id,)).fetchall()
    plan_options = {name: pid for pid, name in plans}

    # UI for selection
    selected_user = st.selectbox("Select User", usernames)
    selected_plan_name = st.selectbox("Select Plan", list(plan_options.keys()))
    selected_plan_id = plan_options[selected_plan_name]

    if st.button("Assign Plan"):
        # Check if user already subscribed
        existing = cursor.execute("""
            SELECT id FROM subscriptions WHERE user_id = ? AND tenant_id = ?
        """, (selected_user, tenant_id)).fetchone()

        if existing:
            # Update existing subscription
            cursor.execute("""
                UPDATE subscriptions SET plan_id = ? WHERE user_id = ? AND tenant_id = ?
            """, (selected_plan_id, selected_user, tenant_id))
            st.success("Plan updated for user.")
        else:
            # Create new subscription
            cursor.execute("""
                INSERT INTO subscriptions (user_id, plan_id, tenant_id, start_date)
                VALUES (?, ?, ?, ?)
            """, (selected_user, selected_plan_id, tenant_id, "2025-07-31"))
            st.success("Plan assigned to user.")

        conn.commit()

    # Show current assignments
    st.markdown("### 📋 Current Subscriptions")
    assignments = cursor.execute("""
        SELECT s.user_id, p.name
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE p.tenant_id = ?
    """, (tenant_id,)).fetchall()

    for user, plan in assignments:
        st.markdown(f"- **{user}** → Plan: **{plan}**")

    conn.close()
