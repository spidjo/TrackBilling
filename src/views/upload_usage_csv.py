import streamlit as st
import pandas as pd
import io
from datetime import datetime
from database import get_db_connection
from session import init_session_state

# Initialize session state
init_session_state()

def insert_usage_records(df, tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    success = 0
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO usage_metrics (tenant_id, user_id, metric_type, quantity, usage_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tenant_id,
                row['user_id'],  # Assuming user_id is unique per tenant
                row['metric_type'],
                int(row['quantity']),
                row['usage_date']
            ))
            success += 1
        except Exception as e:
            st.warning(f"Row failed: {row.to_dict()} | Error: {e}")
    conn.commit()
    conn.close()
    return success

def render_upload_usage_csv():
    st.title("📄 Upload Usage CSV")

    if st.session_state.role != 'admin':
        st.error("You do not have permission to view this page.")
        return

    tenant_id = st.session_state.tenant_id

    st.markdown("Upload a CSV file with jfj the following headers: `user_id`, `metric_type`, `quantity`, `usage_date` (YYYY-MM-DD)")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)

            # Basic validation
            required_columns = {'user_id', 'metric_type', 'quantity', 'usage_date'}
            if not required_columns.issubset(df.columns):
                st.error(f"CSV must contain the columns: {required_columns}")
                return

            st.dataframe(df.head())

            if st.button("📤 Upload to Database"):
                count = insert_usage_records(df, tenant_id)
                st.success(f"{count} usage records successfully inserted for tenant '{tenant_id}'")

        except Exception as e:
            st.error(f"Failed to process CSV: {e}")
