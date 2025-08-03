import streamlit as st
from database import get_db_connection
from datetime import datetime
from session import init_session_state

def log_usage():
    init_session_state()
    tenant_id = st.session_state.tenant_id

    st.subheader("📈 Report Usage")

    usage_amount = st.number_input("Usage Units", min_value=0.0)
    usage_type = st.text_input("Usage Type (e.g., calls, API requests)")
    if st.button("Log Usage"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usage_records (user_id, usage_amount, usage_type, timestamp, tenant_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            st.session_state.username,
            usage_amount,
            usage_type,
            datetime.utcnow().isoformat(),
            tenant_id
        ))
        conn.commit()
        conn.close()
        st.success("Usage logged.")

    # Show recent usage
    st.markdown("### Recent Usage")
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT usage_amount, usage_type, timestamp FROM usage_records
        WHERE user_id = ? AND tenant_id = ?
        ORDER BY timestamp DESC LIMIT 10
    """, (st.session_state.username, tenant_id)).fetchall()
    for amt, typ, ts in rows:
        st.markdown(f"- {amt} units of **{typ}** at {ts}")
    conn.close()
