# views/upload_usage_csv.py

import streamlit as st
import pandas as pd
from datetime import datetime
from db.database import get_db_connection
from utils.session_guard import require_login

def render_upload_usage_csv():
    require_login("admin")
    st.title("📤 Upload Usage Data (Multi-Metric)")

    user = st.session_state.get("user")
    tenant_id = user["tenant_id"]

    st.info("Expected CSV Format: `user_id, metric_name, usage_amount, usage_date`")

    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)

            required_cols = {"user_id", "metric_name", "usage_amount", "usage_date"}
            if not required_cols.issubset(set(df.columns)):
                st.error(f"CSV must contain columns: {', '.join(required_cols)}")
                return

            conn = get_db_connection()
            cursor = conn.cursor()

            # Fetch all valid metrics for this tenant
            cursor.execute("SELECT id, name FROM usage_metrics WHERE tenant_id = ?", (tenant_id,))
            metric_map = {name: mid for mid, name in cursor.fetchall()}

            valid_rows = 0
            failed_rows = []

            for index, row in df.iterrows():
                user_id = row["user_id"]
                metric_name = row["metric_name"]
                usage_amount = row["usage_amount"]
                usage_date = row["usage_date"]

                metric_id = metric_map.get(metric_name)
                if not metric_id:
                    failed_rows.append((index + 2, f"Unknown metric: {metric_name}"))
                    continue

                try:
                    usage_amount = int(usage_amount)
                    usage_date_parsed = datetime.strptime(str(usage_date), "%Y-%m-%d").date()

                    cursor.execute("""
                        INSERT INTO usage_records (user_id, tenant_id, metric_id, metric_name, usage_amount, usage_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (user_id, tenant_id, metric_id, metric_name, usage_amount, usage_date_parsed))
                    valid_rows += 1

                except Exception as e:
                    failed_rows.append((index + 2, str(e)))

            conn.commit()
            conn.close()

            st.success(f"✅ Successfully uploaded {valid_rows} usage records.")
            if failed_rows:
                st.warning(f"⚠️ {len(failed_rows)} rows failed to upload:")
                for row_num, err in failed_rows:
                    st.text(f"Row {row_num}: {err}")

        except Exception as e:
            st.error(f"Failed to process file: {e}")
