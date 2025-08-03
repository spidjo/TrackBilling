import streamlit as st
from database import get_db_connection
from session import init_session_state

def manage_subscriptions():
    init_session_state()
    tenant_id = st.session_state.tenant_id

    st.subheader("📬 My Subscriptions")

    conn = get_db_connection()
    cursor = conn.cursor()

    # View all plans from this tenant
    plans = cursor.execute("SELECT id, name FROM plans WHERE tenant_id = ?", (tenant_id,)).fetchall()
    plan_options = {name: pid for pid, name in plans}

    st.markdown("### Subscribe to a Plan")
    plan_choice = st.selectbox("Available Plans", list(plan_options.keys()))
    if st.button("Subscribe"):
        user_id = st.session_state.username  # optionally map username to ID
        cursor.execute("""
            INSERT INTO subscriptions (user_id, plan_id, tenant_id)
            VALUES (?, ?, ?)
        """, (user_id, plan_options[plan_choice], tenant_id))
        conn.commit()
        st.success("Subscription activated.")

    # List current subscriptions
    st.markdown("### Current Subscriptions")
    rows = cursor.execute("""
        SELECT s.id, p.name
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.tenant_id = ? AND s.user_id = ?
    """, (tenant_id, st.session_state.username)).fetchall()

    for row in rows:
        st.markdown(f"- **{row[1]}**")

    conn.close()
