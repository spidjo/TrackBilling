#src/views/superadmin/admin_analytics_dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from db.database import get_db_connection
from datetime import datetime, timedelta
from dateutil import parser

def render_admin_analytics_dashboard():
    st.title("📊 Admin Analytics Dashboard")

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Sidebar Filters ---
    st.sidebar.subheader("Filters")
    start_date = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=180))
    end_date = st.sidebar.date_input("End Date", datetime.today())

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Key Metrics",
        "💡 CLV",
        "🔁 Retention",
        "⚠️ Inactive Clients",
        "💵 Revenue Breakdown",
        "🧾 Payment Status",
        "🔔 Notifications"
    ])

    with tab1:
        st.subheader("💰 Key Metrics")
        cursor.execute("""
            SELECT tenant_id, strftime('%Y-%m', invoice_date) as month, SUM(total_amount) as revenue
            FROM invoices
            WHERE invoice_date BETWEEN ? AND ?
            GROUP BY tenant_id, month
        """, (start_date, end_date))
        revenue_data = cursor.fetchall()

        df_rev = pd.DataFrame(revenue_data, columns=["tenant_id", "month", "revenue"])
        df_mrr = df_rev.groupby("month").agg(mrr=("revenue", "sum")).reset_index()
        df_arpu = df_rev.groupby("tenant_id").agg(arpu=("revenue", "mean"))

        st.metric("📈 Total MRR (last month)", f"R{df_mrr['mrr'].iloc[-1]:,.2f}" if not df_mrr.empty else "N/A")
        st.metric("📊 Avg ARPU per Tenant", f"R{df_arpu['arpu'].mean():.2f}" if not df_arpu.empty else "N/A")

        cursor.execute("""
            SELECT strftime('%Y-%m', start_date) as month, COUNT(DISTINCT user_id)
            FROM subscriptions
            WHERE is_active = 1
            GROUP BY month
            ORDER BY month
        """)
        subs = cursor.fetchall()
        df_churn = pd.DataFrame(subs, columns=["month", "active_users"])
        df_churn["churn"] = df_churn["active_users"].diff(-1) * -1

        st.line_chart(df_churn.set_index("month")["active_users"], height=250, use_container_width=True)
        st.caption("👥 Active Subscriptions over Time")

    with tab2:
        st.subheader("💡 Customer Lifetime Value (CLV)")
        cursor.execute("""
            SELECT s.tenant_id, s.user_id, t.name, MIN(s.start_date), MAX(s.start_date)
            FROM subscriptions s
            JOIN tenants t ON s.tenant_id = t.id
            WHERE s.is_active = 1
            GROUP BY s.tenant_id, s.user_id
        """)
        rows = cursor.fetchall()
        data = []
        for t_id, u_id, tenant_name, min_date, max_date in rows:
            months = (parser.parse(str(max_date)) - parser.parse(str(min_date))).days / 30
            arpu = df_arpu.loc[t_id, "arpu"] if t_id in df_arpu.index else 0
            data.append((t_id, u_id, tenant_name, arpu * months))
        df_clv = pd.DataFrame(data, columns=["tenant_id", "user_id", "tenant_name", "CLV"])

        st.bar_chart(df_clv.groupby("tenant_name")["CLV"].mean())

    with tab3:
        st.subheader("🔁 Retention & Acquisition")
        cursor.execute("""
            SELECT strftime('%Y-%m', registration_date) as month, COUNT(*) FROM users
            GROUP BY month
        """)
        reg = cursor.fetchall()
        df_reg = pd.DataFrame(reg, columns=["month", "new_users"])

        st.line_chart(df_reg.set_index("month"), use_container_width=True)
        st.caption("📥 New Client Registrations")

    with tab4:
        st.subheader("⚠️ Inactive Clients")
        inactive_cutoff = datetime.today() - timedelta(days=30)
        cursor.execute("""
            SELECT DISTINCT u.username FROM users u
            LEFT JOIN usage_records um ON u.id = um.user_id
            WHERE (um.usage_date IS NULL OR um.usage_date < ?) AND u.role = 'client'
        """, (inactive_cutoff,))
        inactive_clients = [row[0] for row in cursor.fetchall()]
        if inactive_clients:
            st.warning(f"⚠️ {len(inactive_clients)} clients inactive in last 30 days:")
            st.write(inactive_clients)
        else:
            st.success("✅ No inactive clients in the past 30 days.")

    with tab5:
        st.subheader("💵 Revenue Breakdown by Plan")
        cursor.execute("""
            SELECT p.name AS plan_name, SUM(i.total_amount) AS revenue
            FROM invoices i
            JOIN subscriptions s ON i.user_id = s.user_id AND s.is_active = 1
            JOIN plans p ON s.plan_id = p.id
            WHERE i.tenant_id = s.tenant_id
            GROUP BY p.name
        """)
        plan_rev = cursor.fetchall()
        df_plan = pd.DataFrame(plan_rev, columns=["Plan", "Revenue"])
        st.bar_chart(df_plan.set_index("Plan"))

        cursor.execute("""
            SELECT t.name AS tenant_name, SUM(i.total_amount) AS revenue
            FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            GROUP BY t.name
        """)
        tenant_rev = cursor.fetchall()
        df_trev = pd.DataFrame(tenant_rev, columns=["Tenant", "Revenue"])
        st.subheader("🏢 Revenue Breakdown by Tenant")
        st.bar_chart(df_trev.set_index("Tenant"))

    with tab6:
        st.subheader("🧾 Invoice Payment Status")
        cursor.execute("SELECT is_paid, COUNT(*) FROM invoices GROUP BY is_paid")
        status_counts = cursor.fetchall()
        df_status = pd.DataFrame(status_counts, columns=["is_paid", "count"])
        df_status["label"] = df_status["is_paid"].map({0: "Unpaid", 1: "Paid"})
        fig, ax = plt.subplots()
        ax.pie(df_status["count"], labels=df_status["label"], autopct='%1.1f%%', startangle=90)
        st.pyplot(fig)
        st.caption("🧾 Invoice Payment Status")
    with tab7:
        st.subheader("🔔 Global Notifications Center")

        # --- Overdue Invoices by Tenant ---
        st.markdown("### 🚨 Tenants with Overdue Invoices")
        cursor.execute("""
            SELECT t.name, t.id, COUNT(*) as overdue_count, SUM(i.total_amount) as total_due
            FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.is_paid = 0
            GROUP BY i.tenant_id
            HAVING overdue_count > 0
        """)
        overdue = cursor.fetchall()
        if overdue:
            df_overdue = pd.DataFrame(overdue, columns=["Tenant Name", "Tenant ID", "Overdue Count", "Total Due"])
            st.warning(f"{len(df_overdue)} tenants have overdue invoices.")
            st.dataframe(df_overdue, use_container_width=True)
        else:
            st.success("✅ No tenants with overdue invoices.")

        # --- Tenants near usage limits ---
        st.markdown("### ⚠️ Tenants Near Usage Limits")
        cursor.execute("""
            SELECT t.name, SUM(um.usage_amount) as total_usage, p.included_units
            FROM usage_records um
            JOIN tenants t ON um.tenant_id = t.id
            JOIN subscriptions s ON um.tenant_id = s.tenant_id
            JOIN plans p ON s.plan_id = p.id
            WHERE s.is_active = 1
            GROUP BY s.tenant_id, p.included_units
        """)
        usage_alerts = []
        for row in cursor.fetchall():
            name, used, limit = row
            if limit and used >= 0.8 * limit:
                usage_alerts.append((name, used, limit))

        if usage_alerts:
            df_usage = pd.DataFrame(usage_alerts, columns=["Tenant Name", "Usage", "Plan Limit"])
            st.error("Some tenants are nearing or exceeding their usage limits.")
            st.dataframe(df_usage, use_container_width=True)
        else:
            st.success("✅ All tenants are within usage limits.")

        # --- Inactive Tenants (No usage in last 30 days) ---
        st.markdown("### 📉 Inactive Tenants")
        cursor.execute("""
            SELECT DISTINCT t.name
            FROM usage_metrics um
            JOIN tenants t ON um.tenant_id = t.id
            WHERE um.usage_date >= DATE('now', '-30 day')
        """)
        active_tenants = {r[0] for r in cursor.fetchall()}

        cursor.execute("SELECT DISTINCT name FROM tenants")
        all_tenants = {r[0] for r in cursor.fetchall()}

        inactive = list(all_tenants - active_tenants)
        if inactive:
            st.info(f"{len(inactive)} tenants had no usage activity in the last 30 days.")
            st.write(inactive)
        else:
            st.success("✅ All tenants have recent activity.")
    conn.close()
