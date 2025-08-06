# src/views/superadmin/resend_log_view.py

import streamlit as st
import pandas as pd
from db.database import get_db_connection

def fetch_resend_attempts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.id, u.username, u.email, v.timestamp, v.ip_address, v.status, v.reason
        FROM verification_resend_log v
        JOIN users u ON v.user_id = u.id
        ORDER BY v.timestamp DESC
    ''')
    rows = cursor.fetchall()
    conn.close()

    columns = ["Log ID", "Username", "Email", "Timestamp", "IP Address", "Status", "Reason"]
    return pd.DataFrame(rows, columns=columns)

def resend_log_view():
    st.title("🔍 Verification Resend Log Viewer")
    st.caption("Audit log for all verification email resend attempts.")

    df = fetch_resend_attempts()

    with st.expander("🔎 Filters", expanded=False):
        usernames = df["Username"].unique()
        status_options = df["Status"].unique()

        selected_username = st.selectbox("Filter by Username", ["All"] + list(usernames))
        selected_status = st.selectbox("Filter by Status", ["All"] + list(status_options))

        if selected_username != "All":
            df = df[df["Username"] == selected_username]
        if selected_status != "All":
            df = df[df["Status"] == selected_status]

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Log as CSV",
        data=csv,
        file_name="verification_resend_log.csv",
        mime="text/csv"
    )
