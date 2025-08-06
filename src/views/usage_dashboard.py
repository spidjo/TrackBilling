import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime, timedelta
from db.database import get_db_connection
from utils.session import init_session_state

def usage_dashboard():
    init_session_state()

    if not st.session_state.get("authenticated"):
        st.warning("🔒 Please log in to view usage dashboards.")
        st.stop()

    tenant_id = st.session_state.tenant_id
    username = st.session_state.username
    role = st.session_state.role

    st.subheader("📈 Usage Dashboard")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch usage records
    if role == "tenantadmin":
        cursor.execute("""
            SELECT user_id, metric_type, quantity, usage_date
            FROM usage_metrics
            WHERE tenant_id = ?
        """, (tenant_id,))
    else:
        cursor.execute("""
            SELECT user_id, metric_type, quantity, usage_date
            FROM usage_metrics
            WHERE tenant_id = ? AND user_id = (
                SELECT id FROM users WHERE username = ?
            )
        """, (tenant_id, username))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        st.info("No usage data available.")
        return

    # Format DataFrame
    df = pd.DataFrame(rows, columns=["user_id", "metric_type", "quantity", "usage_date"])
    df["usage_date"] = pd.to_datetime(df["usage_date"])
    df["date"] = df["usage_date"].dt.date
    df["month"] = df["usage_date"].dt.to_period("M")
    df["hour"] = df["usage_date"].dt.hour

    # Metric Filter
    metrics = df["metric_type"].unique().tolist()
    selected_metric = st.selectbox("📊 Filter by Metric", ["All"] + metrics)

    if selected_metric != "All":
        df = df[df["metric_type"] == selected_metric]

    # 🔁 Export CSV
    st.markdown("#### ⬇️ Export Usage Data")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="usage_data.csv", mime="text/csv")

    # 📊 Usage Over Time
    st.markdown("### 🔄 Usage Over Time")
    daily = df.groupby("date")["quantity"].sum().reset_index()
    st.line_chart(daily.rename(columns={"date": "index"}).set_index("index"))

    # 🔔 Anomaly Detection
    st.markdown("### 🔔 Anomaly Alerts")
    q_mean = daily["quantity"].mean()
    q_std = daily["quantity"].std()
    if q_std > 0:
        anomalies = daily[daily["quantity"] > q_mean + 2 * q_std]
        if not anomalies.empty:
            st.warning(f"⚠️ Detected {len(anomalies)} high-usage anomalies:")
            st.dataframe(anomalies)
        else:
            st.success("✅ No anomalies detected in recent usage.")
    else:
        st.info("Not enough variation to determine anomalies.")

    # 📆 Monthly Aggregation
    st.markdown("### 📆 Monthly Usage Summary")
    monthly = df.groupby(["month", "metric_type"])["quantity"].sum().reset_index()
    st.dataframe(monthly.pivot(index="month", columns="metric_type", values="quantity").fillna(0), use_container_width=True)

    # 👥 User Breakdown (only tenant admins)
    if role == "tenantadmin":
        st.markdown("### 👥 User-Level Breakdown")
        by_user = df.groupby(["user_id", "metric_type"])["quantity"].sum().reset_index()
        st.dataframe(by_user.pivot(index="user_id", columns="metric_type", values="quantity").fillna(0), use_container_width=True)

    # 🌡️ Hourly Heatmap
    st.markdown("### 🌡️ Hourly Usage Heatmap")

    heatmap_data = df.groupby(["hour", "date"])["quantity"].sum().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(heatmap_data, cmap="YlOrRd", ax=ax)
    ax.set_title("Hourly Usage by Day")
    ax.set_xlabel("Date")
    ax.set_ylabel("Hour of Day")
    st.pyplot(fig)

def usage_heatmap():
    user_id = st.session_state.get("user_id")
    if user_id is None:
        st.info("No usage data available.")
        return
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT usage_date, metric_type, metric_subtype, SUM(quantity) AS total
        FROM usage_metrics
        WHERE user_id = ?
        GROUP BY usage_date, metric_type, metric_subtype
    """, conn, params=(user_id,))
    conn.close()

    if df.empty:
        st.info("No usage data available.")
        return

    df["usage_date"] = pd.to_datetime(df["usage_date"])
    heatmap_data = df.pivot_table(index="metric_type", columns="usage_date", values="total", fill_value=0)
    st.dataframe(heatmap_data.style.background_gradient(cmap='viridis'))

    if st.checkbox("Download CSV"):
        st.download_button("📥 Export", data=df.to_csv(index=False), file_name="usage.csv")

    st.markdown("### 🔎 Drill-Down by Subtype")
    selected_metric = st.selectbox("Select Metric", df["metric_type"].unique())
    filtered = df[df["metric_type"] == selected_metric]
    st.dataframe(filtered)
