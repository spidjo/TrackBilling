import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from database import get_db_connection

def superadmin_dashboard():
    st.title("🧭 SuperAdmin Dashboard - Platform Overview")

    conn = get_db_connection()
    cursor = conn.cursor()

    # === SIDEBAR FILTERS ===
    st.sidebar.header("🔍 Filters")

    # Timeframe
    timeframe_option = st.sidebar.selectbox("Timeframe", ["All", "Last 3 Months", "Last 6 Months", "Last 12 Months"])
    cutoff_date = None
    if timeframe_option != "All":
        months_map = {
            "Last 3 Months": 3,
            "Last 6 Months": 6,
            "Last 12 Months": 12,
        }
        cutoff_date = date.today() - timedelta(days=30 * months_map[timeframe_option])

    # Industry and Region
    cursor.execute("SELECT DISTINCT industry FROM tenants WHERE industry IS NOT NULL")
    industries = [row[0] for row in cursor.fetchall()]
    selected_industry = st.sidebar.selectbox("Industry", ["All"] + industries)

    cursor.execute("SELECT DISTINCT region FROM tenants WHERE region IS NOT NULL")
    regions = [row[0] for row in cursor.fetchall()]
    selected_region = st.sidebar.selectbox("Region", ["All"] + regions)

    # Dynamic filter builder
    tenant_filter_clauses = ["1=1"]
    tenant_params = []

    if selected_industry != "All":
        tenant_filter_clauses.append("t.industry = ?")
        tenant_params.append(selected_industry)

    if selected_region != "All":
        tenant_filter_clauses.append("t.region = ?")
        tenant_params.append(selected_region)

    tenant_filter = " AND ".join(tenant_filter_clauses)

    # === TABS ===
    tabs = st.tabs(["📊 Overview", "📈 Signups & Growth", "🏭 Industry Insights"])

    # --- TAB 1: Overview ---
    with tabs[0]:
        st.subheader("🏢 Active Tenants")
        query = f"SELECT COUNT(*) FROM tenants t WHERE {tenant_filter}"
        cursor.execute(query, tuple(tenant_params))
        st.metric("Active Tenants", cursor.fetchone()[0])

        st.subheader("💰 Monthly Recurring Revenue (MRR)")
        query = f"""
            SELECT SUM(p.monthly_fee)
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            JOIN tenants t ON s.tenant_id = t.id
            WHERE s.is_active = 1 AND {tenant_filter}
        """
        cursor.execute(query, tuple(tenant_params))
        mrr = cursor.fetchone()[0] or 0
        st.metric("MRR", f"R{mrr:.2f}")

        st.subheader("📈 ARPU (Average Revenue Per User)")
        query = f"""
            SELECT COUNT(DISTINCT s.user_id)
            FROM subscriptions s
            JOIN tenants t ON s.tenant_id = t.id
            WHERE s.is_active = 1 AND {tenant_filter}
        """
        cursor.execute(query, tuple(tenant_params))
        active_users = cursor.fetchone()[0] or 1
        arpu = mrr / active_users
        st.metric("ARPU", f"R{arpu:.2f}")

        st.subheader("📉 Churn Rate")
        query = f"""
            SELECT COUNT(*)
            FROM subscriptions s
            JOIN tenants t ON s.tenant_id = t.id
            WHERE s.is_active = 0 AND {tenant_filter}
        """
        cursor.execute(query, tuple(tenant_params))
        churned = cursor.fetchone()[0] or 0

        query = f"""
            SELECT COUNT(*)
            FROM subscriptions s
            JOIN tenants t ON s.tenant_id = t.id
            WHERE {tenant_filter}
        """
        cursor.execute(query, tuple(tenant_params))
        total_subs = cursor.fetchone()[0] or 1

        churn_rate = (churned / total_subs) * 100
        st.metric("Churn Rate", f"{churn_rate:.1f}%")

    # --- TAB 2: Growth ---
    with tabs[1]:
        st.subheader("📅 Tenant Signups Over Time")
        query = f"""
            SELECT strftime('%Y-%m', t.created_at) AS month, COUNT(*)
            FROM tenants t
            WHERE {tenant_filter}
        """
        params = list(tenant_params)
        if cutoff_date:
            query += " AND t.created_at >= ?"
            params.append(cutoff_date.isoformat())

        query += " GROUP BY month ORDER BY month"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        if rows:
            df_signups = pd.DataFrame(rows, columns=["Month", "Signups"])
            st.line_chart(df_signups.set_index("Month"))
        else:
            st.info("No signup data for the selected timeframe or filters.")

    # --- TAB 3: Industry Revenue ---
    with tabs[2]:
        st.subheader("🏭 Revenue by Industry")
        cursor.execute("""
            SELECT t.industry, SUM(i.total_amount)
            FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            GROUP BY t.industry
        """)
        industry_rev = cursor.fetchall()
        if industry_rev:
            df_industry = pd.DataFrame(industry_rev, columns=["Industry", "Revenue"])
            st.bar_chart(df_industry.set_index("Industry"))
        else:
            st.info("No industry revenue data found.")

    conn.close()
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from database import get_db_connection

def superadmin_dashboard():
    st.title("🌐 Superadmin Dashboard")

    conn = get_db_connection()
    cursor = conn.cursor()

    # === SIDEBAR FILTERS ===
    st.sidebar.header("🔍 Filters")

    # Timeframe
    timeframe_option = st.sidebar.selectbox("Timeframe", ["All", "Last 3 Months", "Last 6 Months", "Last 12 Months"])
    cutoff_date = None
    if timeframe_option != "All":
        months_map = {
            "Last 3 Months": 3,
            "Last 6 Months": 6,
            "Last 12 Months": 12,
        }
        cutoff_date = date.today() - timedelta(days=30 * months_map[timeframe_option])

    # Industry and Region
    cursor.execute("SELECT DISTINCT industry FROM tenants WHERE industry IS NOT NULL")
    industries = [row[0] for row in cursor.fetchall()]
    selected_industry = st.sidebar.selectbox("Industry", ["All"] + industries)

    cursor.execute("SELECT DISTINCT region FROM tenants WHERE region IS NOT NULL")
    regions = [row[0] for row in cursor.fetchall()]
    selected_region = st.sidebar.selectbox("Region", ["All"] + regions)

    # Dynamic filter builder
    tenant_filter_clauses = ["1=1"]
    tenant_params = []

    if selected_industry != "All":
        tenant_filter_clauses.append("t.industry = ?")
        tenant_params.append(selected_industry)

    if selected_region != "All":
        tenant_filter_clauses.append("t.region = ?")
        tenant_params.append(selected_region)

    tenant_filter = " AND ".join(tenant_filter_clauses)

    # === TABS ===
    tabs = st.tabs(["📊 Overview", "📈 Signups & Growth", "🏭 Industry Insights"])

    # --- TAB 1: Overview ---
    with tabs[0]:
        st.subheader("🏢 Active Tenants")
        query = f"SELECT COUNT(*) FROM tenants t WHERE {tenant_filter}"
        cursor.execute(query, tuple(tenant_params))
        st.metric("Active Tenants", cursor.fetchone()[0])

        st.subheader("💰 Monthly Recurring Revenue (MRR)")
        query = f"""
            SELECT SUM(p.monthly_fee)
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            JOIN tenants t ON s.tenant_id = t.id
            WHERE s.is_active = 1 AND {tenant_filter}
        """
        cursor.execute(query, tuple(tenant_params))
        mrr = cursor.fetchone()[0] or 0
        st.metric("MRR", f"R{mrr:.2f}")

        st.subheader("📈 ARPU (Average Revenue Per User)")
        query = f"""
            SELECT COUNT(DISTINCT s.user_id)
            FROM subscriptions s
            JOIN tenants t ON s.tenant_id = t.id
            WHERE s.is_active = 1 AND {tenant_filter}
        """
        cursor.execute(query, tuple(tenant_params))
        active_users = cursor.fetchone()[0] or 1
        arpu = mrr / active_users
        st.metric("ARPU", f"R{arpu:.2f}")

        st.subheader("📉 Churn Rate")
        query = f"""
            SELECT COUNT(*)
            FROM subscriptions s
            JOIN tenants t ON s.tenant_id = t.id
            WHERE s.is_active = 0 AND {tenant_filter}
        """
        cursor.execute(query, tuple(tenant_params))
        churned = cursor.fetchone()[0] or 0

        query = f"""
            SELECT COUNT(*)
            FROM subscriptions s
            JOIN tenants t ON s.tenant_id = t.id
            WHERE {tenant_filter}
        """
        cursor.execute(query, tuple(tenant_params))
        total_subs = cursor.fetchone()[0] or 1

        churn_rate = (churned / total_subs) * 100
        st.metric("Churn Rate", f"{churn_rate:.1f}%")

    # --- TAB 2: Growth ---
    with tabs[1]:
        st.subheader("📅 Tenant Signups Over Time")
        query = f"""
            SELECT strftime('%Y-%m', t.created_at) AS month, COUNT(*)
            FROM tenants t
            WHERE {tenant_filter}
        """
        params = list(tenant_params)
        if cutoff_date:
            query += " AND t.created_at >= ?"
            params.append(cutoff_date.isoformat())

        query += " GROUP BY month ORDER BY month"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        if rows:
            df_signups = pd.DataFrame(rows, columns=["Month", "Signups"])
            st.line_chart(df_signups.set_index("Month"))
        else:
            st.info("No signup data for the selected timeframe or filters.")

    # --- TAB 3: Industry Revenue ---
    with tabs[2]:
        st.subheader("🏭 Revenue by Industry")
        cursor.execute("""
            SELECT t.industry, SUM(i.total_amount)
            FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            GROUP BY t.industry
        """)
        industry_rev = cursor.fetchall()
        if industry_rev:
            df_industry = pd.DataFrame(industry_rev, columns=["Industry", "Revenue"])
            st.bar_chart(df_industry.set_index("Industry"))
        else:
            st.info("No industry revenue data found.")

    conn.close()
