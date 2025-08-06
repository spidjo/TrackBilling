# src/views/superadmin_dashboard.py

import streamlit as st
from datetime import datetime, timedelta
from db.database import get_db_connection
from utils.session_guard import require_login
from utils.report_utils import generate_superadmin_pdf_report
import pandas as pd
import matplotlib.pyplot as plt


def superadmin_dashboard():
    st.set_page_config(page_title="📊 SuperAdmin Dashboard", layout="wide")
    require_login("superadmin")
    st.title("📊 SuperAdmin Reporting & Analytics")

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Filters ---
    with st.expander("📌 Filters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("📅 Start Date", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("📅 End Date", datetime.now())

        cursor.execute("SELECT id, name FROM tenants ORDER BY name")
        tenants = cursor.fetchall()
        tenant_options = ["All"] + [f"{tid}: {tname}" for tid, tname in tenants]
        selected_tenant = st.selectbox("🏢 Tenant", tenant_options)

    tenant_filter_sql = ""
    tenant_filter_param = ()
    if selected_tenant != "All":
        tenant_id = int(selected_tenant.split(":")[0])
        tenant_filter_sql = "AND u.tenant_id = ?"
        tenant_filter_param = (tenant_id,)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    # --- TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        "📈 Revenue Trends",
        "📉 Churn & Retention",
        "📤 Export Reports"
    ])

    # ---------------------- TAB 1: Overview ----------------------
    with tab1:
        st.subheader("🔢 Key Metrics")

        # Total tenants
        cursor.execute("SELECT COUNT(*) FROM tenants")
        total_tenants = cursor.fetchone()[0]

        # Active subscriptions
        cursor.execute(f"""
            SELECT COUNT(*) FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.is_active = 1 {tenant_filter_sql}
        """, tenant_filter_param)
        active_subs = cursor.fetchone()[0]

        # Revenue
        cursor.execute(f"""
            SELECT COALESCE(SUM(total_amount), 0) FROM invoices i
            JOIN users u ON i.user_id = u.id
            WHERE i.invoice_date BETWEEN ? AND ? {tenant_filter_sql}
        """, (start_date_str, end_date_str, *tenant_filter_param))
        total_revenue = cursor.fetchone()[0]

        # ARPU
        arpu = total_revenue / active_subs if active_subs > 0 else 0

        # Usage logs
        cursor.execute(f"""
            SELECT COUNT(*) FROM usage_records ur
            JOIN users u ON ur.user_id = u.id
            WHERE ur.usage_date BETWEEN ? AND ? {tenant_filter_sql}
        """, (start_date_str, end_date_str, *tenant_filter_param))
        usage_logs = cursor.fetchone()[0]

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("🏢 Tenants", total_tenants)
        k2.metric("👥 Active Subs", active_subs)
        k3.metric("💰 Revenue", f"R{total_revenue:.2f}")
        k4.metric("📊 ARPU", f"R{arpu:.2f}")
        k5.metric("📈 Usage Logs", usage_logs)

        # --- Top Subscribed Plans ---
        st.subheader("🏆 Top Subscribed Plans")
        cursor.execute(f"""
            SELECT p.name, COUNT(*) as count FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            JOIN users u ON s.user_id = u.id
            WHERE s.is_active = 1 {tenant_filter_sql}
            GROUP BY s.plan_id ORDER BY count DESC LIMIT 5
        """, tenant_filter_param)
        top_plans = cursor.fetchall()


        if top_plans:
            df = pd.DataFrame(top_plans, columns=["Plan", "Subscribers"])
            st.bar_chart(df.set_index("Plan"))
        else:
            st.info("No active subscriptions found.")
            
        # --- Generate PDF Report ---
        start_date = st.date_input("Start Date", datetime.now().replace(day=1))
        end_date = st.date_input("End Date", datetime.now())

        if st.button("🔄 Generate Report"):
            pdf_bytes = generate_superadmin_pdf_report(start_date, end_date)
            
            if pdf_bytes:
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"superadmin_report_{start_date}_{end_date}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Failed to generate PDF.")

    # ---------------------- TAB 2: Revenue Trends ----------------------
    with tab2:
        st.subheader("📈 Monthly Revenue Trend")
        cursor.execute(f"""
            SELECT strftime('%Y-%m', i.invoice_date) AS month,
                   SUM(i.total_amount)
            FROM invoices i
            JOIN users u ON i.user_id = u.id
            WHERE i.invoice_date BETWEEN ? AND ? {tenant_filter_sql}
            GROUP BY month
            ORDER BY month
        """, (start_date_str, end_date_str, *tenant_filter_param))
        revenue_data = cursor.fetchall()

        if revenue_data:
            df_rev = pd.DataFrame(revenue_data, columns=["Month", "Revenue"])
            st.line_chart(df_rev.set_index("Month"))
        else:
            st.warning("No revenue data found in selected period.")

    # ---------------------- TAB 3: Churn & Retention ----------------------
    with tab3:
        st.subheader("📉 Churn & Retention")

        # Churned subs
        cursor.execute(f"""
            SELECT COUNT(*) FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.is_active = 0
            AND s.end_date BETWEEN ? AND ? {tenant_filter_sql}
        """, (start_date_str, end_date_str, *tenant_filter_param))
        churned = cursor.fetchone()[0]

        # New subs
        cursor.execute(f"""
            SELECT COUNT(*) FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.start_date BETWEEN ? AND ? {tenant_filter_sql}
        """, (start_date_str, end_date_str, *tenant_filter_param))
        new_subs = cursor.fetchone()[0]

        st.metric("⬇️ Churned Subscriptions", churned)
        st.metric("⬆️ New Subscriptions", new_subs)

        churn_rate = (churned / (churned + active_subs)) * 100 if churned + active_subs > 0 else 0
        retention_rate = 100 - churn_rate

        st.progress(retention_rate / 100)
        st.info(f"📈 Retention Rate: **{retention_rate:.2f}%** | Churn Rate: **{churn_rate:.2f}%**")

    # ---------------------- TAB 4: Export ----------------------
    with tab4:
        st.subheader("📤 Export Reports")

        if st.button("📥 Download Revenue CSV"):
            df = df_rev if revenue_data else pd.DataFrame()
            st.download_button("⬇️ Download Revenue Data", df.to_csv(index=False), file_name="revenue_report.csv")

        if st.button("📥 Download Top Plans CSV"):
            st.download_button("⬇️ Download Plans", df.to_csv(index=False), file_name="top_plans.csv")

    conn.close()
