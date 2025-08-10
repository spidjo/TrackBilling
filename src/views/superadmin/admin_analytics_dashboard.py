import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db.database import get_db_connection
from datetime import datetime, timedelta
from decimal import Decimal
from utils.session_guard import require_login

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        background-color: #f8f9fa;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .positive-metric {
        border-left: 5px solid #4CAF50;
    }
    .negative-metric {
        border-left: 5px solid #F44336;
    }
    .neutral-metric {
        border-left: 5px solid #2196F3;
    }
    .alert-card {
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #fff3e0;
        border-left: 5px solid #FF9800;
    }
    .tab-container {
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def safe_divide(numerator, denominator):
    """Safely divide Decimal and float values"""
    try:
        if isinstance(numerator, Decimal):
            numerator = float(numerator)
        return numerator / denominator if denominator != 0 else 0
    except Exception:
        return 0

def render_admin_analytics_dashboard():
    require_login('superadmin')
    st.set_page_config(page_title="📊 Admin Analytics Dashboard", layout="wide")
    st.title("📊 Admin Analytics Dashboard")
    st.markdown("Comprehensive analytics and monitoring for platform administrators")

    # --- Sidebar Filters ---
    with st.sidebar:
        st.subheader("🔍 Filters")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                datetime.today() - timedelta(days=180),
                help="Select start date for analysis period"
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                datetime.today(),
                help="Select end date for analysis period"
            )

        # Add time period quick select buttons
        st.markdown("**Quick Select:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("30 Days"):
                start_date = datetime.today() - timedelta(days=30)
        with col2:
            if st.button("90 Days"):
                start_date = datetime.today() - timedelta(days=90)
        with col3:
            if st.button("1 Year"):
                start_date = datetime.today() - timedelta(days=365)

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Tabs ---
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Key Metrics",
        "💡 CLV",
        "🔁 Retention",
        "⚠️ Inactive Clients",
        "💵 Revenue Breakdown",
        "🧾 Payment Status",
        "🔔 Notifications"
    ])

    # ---------------------- TAB 1: Key Metrics ----------------------
    with tab1:
        st.subheader("💰 Key Performance Indicators")
        
        # Fetch all metrics in single query for efficiency
        with st.spinner("Loading metrics..."):
            cursor.execute("""
                SELECT 
                    (SELECT COALESCE(SUM(total_amount), 0) FROM invoices 
                     WHERE invoice_date BETWEEN %s AND %s) as total_revenue,
                    (SELECT COUNT(DISTINCT user_id) FROM subscriptions 
                     WHERE is_active) as active_subs,
                    (SELECT COUNT(*) FROM users 
                     WHERE registration_date BETWEEN %s AND %s) as new_users,
                    (SELECT COUNT(*) FROM invoices 
                     WHERE is_paid = FALSE AND invoice_date BETWEEN %s AND %s) as unpaid_invoices
            """, (start_date, end_date, start_date, end_date, start_date, end_date))
            
            metrics = cursor.fetchone()
            total_revenue, active_subs, new_users, unpaid_invoices = metrics

            # Calculate derived metrics with proper type handling
            period_months = (end_date - start_date).days / 30.0
            mrr = safe_divide(total_revenue, period_months)
            arpu = safe_divide(total_revenue, active_subs)

            # Format metrics for display
            def format_currency(value):
                return f"R{float(value):,.2f}" if value else "R0.00"

            # Metrics cards
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                <div class="metric-card positive-metric">
                    <h3>📈 Monthly Recurring Revenue</h3>
                    <h2>{format_currency(mrr)}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card neutral-metric">
                    <h3>📊 Avg Revenue Per User</h3>
                    <h2>{format_currency(arpu)}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card positive-metric">
                    <h3>👥 Active Subscriptions</h3>
                    <h2>{active_subs:,}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-card negative-metric">
                    <h3>🧾 Unpaid Invoices</h3>
                    <h2>{unpaid_invoices:,}</h2>
                </div>
                """, unsafe_allow_html=True)

        # Subscription trend chart
        st.subheader("📊 Subscription Trends")
        with st.spinner("Loading subscription data..."):
            cursor.execute("""
                SELECT TO_CHAR(start_date, 'YYYY-MM') as month, 
                       COUNT(DISTINCT user_id) as active_users
                FROM subscriptions
                WHERE is_active AND start_date BETWEEN %s AND %s
                GROUP BY month
                ORDER BY month
            """, (start_date, end_date))
            
            subs = cursor.fetchall()
            
            if subs:
                df_churn = pd.DataFrame(subs, columns=["month", "active_users"])
                fig = px.line(
                    df_churn,
                    x="month",
                    y="active_users",
                    markers=True,
                    title="Active Subscriptions Over Time",
                    template="plotly_white"
                )
                fig.update_layout(
                    xaxis_title="Month",
                    yaxis_title="Active Subscriptions",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No subscription data available")

    # ---------------------- TAB 2: Customer Lifetime Value ----------------------
    with tab2:
        st.subheader("💡 Customer Lifetime Value (CLV)")
        
        cursor.execute("""
            SELECT s.tenant_id, t.name, 
                   AVG(i.total_amount) as avg_revenue,
                   COUNT(DISTINCT s.user_id) as users
            FROM subscriptions s
            JOIN tenants t ON s.tenant_id = t.id
            JOIN invoices i ON s.user_id = i.user_id AND s.tenant_id = i.tenant_id
            WHERE s.is_active
            GROUP BY s.tenant_id, t.name
        """)
        clv_data = cursor.fetchall()
        
        if clv_data:
            df_clv = pd.DataFrame(clv_data, columns=["tenant_id", "tenant_name", "avg_revenue", "users"])
            fig = px.bar(
                df_clv,
                x="tenant_name",
                y="avg_revenue",
                color="users",
                title="Average Revenue per Tenant",
                labels={"avg_revenue": "Average Revenue (R)"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No CLV data available")

    # ---------------------- TAB 3: Retention & Acquisition ----------------------
    with tab3:
        st.subheader("🔁 Retention & Acquisition")
        
        cursor.execute("""
            SELECT TO_CHAR(registration_date, 'YYYY-MM') as month, 
                   COUNT(*) as new_users
            FROM users
            WHERE registration_date BETWEEN %s AND %s
            GROUP BY month
            ORDER BY month
        """, (start_date, end_date))
        
        reg_data = cursor.fetchall()
        
        if reg_data:
            df_reg = pd.DataFrame(reg_data, columns=["month", "new_users"])
            fig = px.line(
                df_reg,
                x="month",
                y="new_users",
                markers=True,
                title="New User Registrations"
            )
            fig.update_layout(
                xaxis_title="Month",
                yaxis_title="New Users",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No registration data available")

    # ---------------------- TAB 4: Inactive Clients ----------------------
    with tab4:
        st.subheader("⚠️ Inactive Clients")
        
        inactive_cutoff = datetime.today() - timedelta(days=30)
        cursor.execute("""
            SELECT DISTINCT u.username 
            FROM users u
            LEFT JOIN usage_records um ON u.id = um.user_id
            WHERE (um.usage_date IS NULL OR um.usage_date < %s) 
            AND u.role = 'client'
        """, (inactive_cutoff,))
        
        inactive_clients = [row[0] for row in cursor.fetchall()]
        
        if inactive_clients:
            st.markdown(f"""
            <div class="alert-card">
                <h3>🚨 {len(inactive_clients)} Inactive Clients</h3>
                <p>No activity in last 30 days</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.dataframe(
                pd.DataFrame(inactive_clients, columns=["Username"]),
                use_container_width=True
            )
        else:
            st.success("✅ No inactive clients in the past 30 days.")

    # ---------------------- TAB 5: Revenue Breakdown ----------------------
    with tab5:
        st.subheader("💵 Revenue Breakdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### By Plan")
            cursor.execute("""
                SELECT p.name, SUM(i.total_amount) as revenue
                FROM invoices i
                JOIN subscriptions s ON i.user_id = s.user_id
                JOIN plans p ON s.plan_id = p.id
                WHERE i.invoice_date BETWEEN %s AND %s
                GROUP BY p.name
            """, (start_date, end_date))
            
            plan_rev = cursor.fetchall()
            
            if plan_rev:
                df_plan = pd.DataFrame(plan_rev, columns=["Plan", "Revenue"])
                fig = px.pie(
                    df_plan,
                    names="Plan",
                    values="Revenue",
                    title="Revenue by Plan"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No revenue data by plan")
        
        with col2:
            st.markdown("#### By Tenant")
            cursor.execute("""
                SELECT t.name, SUM(i.total_amount) as revenue
                FROM invoices i
                JOIN tenants t ON i.tenant_id = t.id
                WHERE i.invoice_date BETWEEN %s AND %s
                GROUP BY t.name
            """, (start_date, end_date))
            
            tenant_rev = cursor.fetchall()
            
            if tenant_rev:
                df_tenant = pd.DataFrame(tenant_rev, columns=["Tenant", "Revenue"])
                fig = px.bar(
                    df_tenant,
                    x="Tenant",
                    y="Revenue",
                    title="Revenue by Tenant"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No revenue data by tenant")

    # ---------------------- TAB 6: Payment Status ----------------------
    with tab6:
        st.subheader("🧾 Invoice Payment Status")
        
        cursor.execute("""
            SELECT is_paid, COUNT(*) as count 
            FROM invoices 
            GROUP BY is_paid
        """)
        
        status_data = cursor.fetchall()
        
        if status_data:
            df_status = pd.DataFrame(status_data, columns=["is_paid", "count"])
            df_status["status"] = df_status["is_paid"].map({True: "Paid", False: "Unpaid"})
            
            fig = px.pie(
                df_status,
                names="status",
                values="count",
                title="Payment Status Distribution",
                color="status",
                color_discrete_map={"Paid": "#4CAF50", "Unpaid": "#F44336"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No invoice data available")

    # ---------------------- TAB 7: Notifications ----------------------
    with tab7:
        st.subheader("🔔 Global Notifications Center")
        
        # Overdue Invoices
        st.markdown("### 🚨 Overdue Invoices")
        cursor.execute("""
            SELECT t.name, COUNT(*) as overdue_count, 
                   SUM(i.total_amount) as total_due
            FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.is_paid = FALSE
            GROUP BY t.name
            ORDER BY total_due DESC
        """)
        
        overdue_data = cursor.fetchall()
        
        if overdue_data:
            df_overdue = pd.DataFrame(overdue_data, columns=["Tenant", "Overdue Count", "Total Due"])
            st.dataframe(
                df_overdue.style.format({"Total Due": "R{:.2f}"}),
                use_container_width=True
            )
        else:
            st.success("✅ No overdue invoices")
        
        # Usage Alerts
        st.markdown("### ⚠️ Usage Alerts")
        cursor.execute("""
            SELECT t.name, SUM(um.usage_amount) as usage, 
                   p.included_units as limit
            FROM usage_records um
            JOIN tenants t ON um.tenant_id = t.id
            JOIN subscriptions s ON um.tenant_id = s.tenant_id
            JOIN plans p ON s.plan_id = p.id
            WHERE s.is_active
            GROUP BY t.name, p.included_units
            HAVING SUM(um.usage_amount) >= 0.8 * p.included_units
        """)
        
        usage_alerts = cursor.fetchall()
        
        if usage_alerts:
            df_usage = pd.DataFrame(usage_alerts, columns=["Tenant", "Usage", "Limit"])
            df_usage["% Used"] = (df_usage["Usage"] / df_usage["Limit"] * 100).round(1)
            st.dataframe(
                df_usage.style.format({"Usage": "{:.0f}", "Limit": "{:.0f}", "% Used": "{:.1f}%"}),
                use_container_width=True
            )
        else:
            st.success("✅ No usage limit alerts")
        
        # Inactive Tenants
        st.markdown("### 📉 Inactive Tenants")
        cursor.execute("""
            SELECT t.name
            FROM tenants t
            WHERE NOT EXISTS (
                SELECT 1 FROM usage_records um
                WHERE um.tenant_id = t.id
                AND um.usage_date >= CURRENT_DATE - INTERVAL '30 days'
            )
        """)
        
        inactive_tenants = [row[0] for row in cursor.fetchall()]
        
        if inactive_tenants:
            st.warning(f"⚠️ {len(inactive_tenants)} tenants with no recent activity")
            st.write(inactive_tenants)
        else:
            st.success("✅ All tenants have recent activity")

    conn.close()

if __name__ == "__main__":
    render_admin_analytics_dashboard()