import streamlit as st
from utils.session_guard import require_login
from db.database import get_db_connection

def subscription_audit_admin():
    st.set_page_config(page_title="Subscription Audit Trail")
    require_login('admin')

    user = st.session_state.get("user")
    if not user:
        st.stop()

    st.title("📊 Subscription Audit Trail")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sa.timestamp, u.username, sa.action, p1.name, p2.name
        FROM subscription_audit sa
        JOIN users u ON sa.user_id = u.id
        LEFT JOIN plans p1 ON sa.old_plan_id = p1.id
        LEFT JOIN plans p2 ON sa.new_plan_id = p2.id
        WHERE sa.tenant_id = ?
        ORDER BY sa.timestamp DESC
    """, (user["tenant_id"],))

    rows = cursor.fetchall()

    if not rows:
        st.info("No subscription activity recorded yet.")
    else:
        for ts, username, action, old_plan, new_plan in rows:
            if action == "subscribed":
                st.markdown(f"🟢 **{username}** subscribed to **{new_plan}** on {ts}")
            elif action == "cancelled":
                st.markdown(f"🔴 **{username}** cancelled **{old_plan}** on {ts}")
            elif action == "switched":
                st.markdown(f"🔁 **{username}** switched from **{old_plan}** to **{new_plan}** on {ts}")

    conn.close()
