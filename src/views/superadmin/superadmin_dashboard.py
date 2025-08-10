import streamlit as st
from datetime import datetime, timedelta
from db.database import get_db_connection
from utils.session_guard import require_login
from utils.report_utils import generate_superadmin_pdf_report
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    .report-card {
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: #f8f9fa;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

def superadmin_dashboard():
    st.set_page_config(page_title="📊 SuperAdmin Dashboard", layout="wide")
    require_login("superadmin")
    
    # Page header
    st.title("📊 SuperAdmin Reporting & Analytics")
    st.markdown("Comprehensive overview of platform performance and tenant analytics")
    
    # --- Filters ---
    with st.expander("🔍 Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input(
                "Start Date", 
                datetime.now() - timedelta(days=30),
                help="Select start date for reporting period"
            )
        with col2:
            end_date = st.date_input(
                "End Date", 
                datetime.now(),
                help="Select end date for reporting period"
            )
        with col3:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM tenants ORDER BY name")
            tenants = cursor.fetchall()
            tenant_options = ["All Tenants"] + [f"{tname} (ID: {tid})" for tid, tname in tenants]
            selected_tenant = st.selectbox(
                "Filter by Tenant", 
                tenant_options,
                help="Filter data for specific tenant"
            )
    
    # Prepare SQL filters
    tenant_filter_sql = ""
    tenant_filter_param = ()
    if selected_tenant != "All Tenants":
        tenant_id = int(selected_tenant.split("ID: ")[1].rstrip(")"))
        tenant_filter_sql = "AND u.tenant_id = %s"
        tenant_filter_param = (tenant_id,)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    # --- TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview Metrics",
        "📈 Revenue Analytics",
        "📉 Churn Analysis",
        "📤 Export Center"
    ])

    # ---------------------- TAB 1: Overview Metrics ----------------------
    with tab1:
        st.subheader("🔢 Key Performance Indicators")
        
        # Fetch all metrics in single query for efficiency
        cursor.execute(f"""
            SELECT 
                (SELECT COUNT(*) FROM tenants) as total_tenants,
                (SELECT COUNT(*) FROM subscriptions s JOIN users u ON s.user_id = u.id 
                 WHERE s.is_active {tenant_filter_sql}) as active_subs,
                (SELECT COALESCE(SUM(total_amount), 0) FROM invoices i JOIN users u ON i.user_id = u.id 
                 WHERE i.invoice_date BETWEEN %s AND %s {tenant_filter_sql}) as total_revenue,
                (SELECT COUNT(*) FROM usage_records ur JOIN users u ON ur.user_id = u.id 
                 WHERE ur.usage_date BETWEEN %s AND %s {tenant_filter_sql}) as usage_logs
        """, (start_date_str, end_date_str, start_date_str, end_date_str, *tenant_filter_param))
        
        metrics = cursor.fetchone()
        total_tenants, active_subs, total_revenue, usage_logs = metrics
        arpu = total_revenue / active_subs if active_subs > 0 else 0

        # Metrics cards
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""
            <div class="metric-card neutral-metric">
                <h3>🏢 Tenants</h3>
                <h2>{total_tenants}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card positive-metric">
                <h3>👥 Active Subs</h3>
                <h2>{active_subs}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card positive-metric">
                <h3>💰 Revenue</h3>
                <h2>R{total_revenue:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card neutral-metric">
                <h3>📊 ARPU</h3>
                <h2>R{arpu:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="metric-card neutral-metric">
                <h3>📈 Usage Logs</h3>
                <h2>{usage_logs:,}</h2>
            </div>
            """, unsafe_allow_html=True)

        # Top Subscribed Plans - Plotly chart
        st.subheader("📊 Top Subscribed Plans")
        cursor.execute(f"""
            SELECT p.name, COUNT(*) as count FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            JOIN users u ON s.user_id = u.id
            WHERE s.is_active {tenant_filter_sql}
            GROUP BY p.name ORDER BY count DESC LIMIT 5
        """, tenant_filter_param)
        top_plans = cursor.fetchall()

        if top_plans:
            df_plans = pd.DataFrame(top_plans, columns=["Plan", "Subscribers"])
            fig = px.bar(
                df_plans,
                x="Plan",
                y="Subscribers",
                color="Subscribers",
                color_continuous_scale="Blues",
                text="Subscribers"
            )
            fig.update_layout(
                xaxis_title="Subscription Plan",
                yaxis_title="Number of Subscribers",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active subscriptions found.")

    # ---------------------- TAB 2: Revenue Analytics ----------------------
    with tab2:
        st.subheader("💰 Revenue Performance")
        
        # Revenue trend with Plotly
        cursor.execute(f"""
            SELECT DATE_TRUNC('month', i.invoice_date) AS month,
                   SUM(i.total_amount) as revenue
            FROM invoices i
            JOIN users u ON i.user_id = u.id
            WHERE i.invoice_date BETWEEN %s AND %s {tenant_filter_sql}
            GROUP BY month
            ORDER BY month
        """, (start_date_str, end_date_str, *tenant_filter_param))
        revenue_data = cursor.fetchall()

        if revenue_data:
            df_rev = pd.DataFrame(revenue_data, columns=["Month", "Revenue"])
            df_rev["Month"] = pd.to_datetime(df_rev["Month"]).dt.strftime("%b %Y")
            
            fig = px.line(
                df_rev,
                x="Month",
                y="Revenue",
                markers=True,
                title="Monthly Revenue Trend",
                labels={"Revenue": "Revenue (R)"}
            )
            fig.update_layout(
                hovermode="x unified",
                xaxis_title="Month",
                yaxis_title="Revenue (R)",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Revenue by tenant breakdown
            st.subheader("📌 Revenue by Tenant")
            cursor.execute(f"""
                SELECT t.name as tenant, SUM(i.total_amount) as revenue
                FROM invoices i
                JOIN users u ON i.user_id = u.id
                JOIN tenants t ON u.tenant_id = t.id
                WHERE i.invoice_date BETWEEN %s AND %s {tenant_filter_sql}
                GROUP BY t.name
                ORDER BY revenue DESC
            """, (start_date_str, end_date_str, *tenant_filter_param))
            tenant_revenue = cursor.fetchall()
            
            if tenant_revenue:
                df_tenant = pd.DataFrame(tenant_revenue, columns=["Tenant", "Revenue"])
                fig = px.pie(
                    df_tenant,
                    names="Tenant",
                    values="Revenue",
                    title="Revenue Distribution by Tenant"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No revenue data found in selected period.")

    # ---------------------- TAB 3: Churn Analysis ----------------------
    with tab3:
        st.subheader("📉 Subscription Health")
        
        # Fetch churn metrics
        cursor.execute(f"""
            SELECT 
                (SELECT COUNT(*) FROM subscriptions s
                 JOIN users u ON s.user_id = u.id
                 WHERE s.is_active = False AND s.end_date BETWEEN %s AND %s {tenant_filter_sql}) as churned,
                (SELECT COUNT(*) FROM subscriptions s
                 JOIN users u ON s.user_id = u.id
                 WHERE s.start_date BETWEEN %s AND %s {tenant_filter_sql}) as new_subs
        """, (start_date_str, end_date_str, start_date_str, end_date_str, *tenant_filter_param))
        
        churn_data = cursor.fetchone()
        churned, new_subs = churn_data
        churn_rate = (churned / (churned + active_subs)) * 100 if churned + active_subs > 0 else 0
        retention_rate = 100 - churn_rate

        # Metrics cards
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card negative-metric">
                <h3>⬇️ Churned Subscriptions</h3>
                <h2>{churned}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card positive-metric">
                <h3>⬆️ New Subscriptions</h3>
                <h2>{new_subs}</h2>
            </div>
            """, unsafe_allow_html=True)

        # Churn rate visualization
        st.subheader("📊 Retention Metrics")
        fig = go.Figure()
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=retention_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Retention Rate (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#4CAF50"},
                'steps': [
                    {'range': [0, 70], 'color': "#F44336"},
                    {'range': [70, 90], 'color': "#FFC107"},
                    {'range': [90, 100], 'color': "#4CAF50"}
                ]
            }
        ))
        st.plotly_chart(fig, use_container_width=True)
        
        st.info(f"""
        **📈 Retention Rate:** `{retention_rate:.2f}%`  
        **📉 Churn Rate:** `{churn_rate:.2f}%`
        """)

    # ---------------------- TAB 4: Export Center ----------------------
    with tab4:
        st.subheader("📤 Data Export Center")
        
        with st.container(border=True):
            st.markdown("### 📅 Custom Report Generator")
            report_start = st.date_input("Report Start Date", start_date)
            report_end = st.date_input("Report End Date", end_date)
            
            if st.button("🔄 Generate Custom Report", type="primary"):
                with st.spinner("Generating comprehensive report..."):
                    pdf_bytes = generate_superadmin_pdf_report(report_start, report_end)
                    
                    if pdf_bytes:
                        st.download_button(
                            label="📥 Download PDF Report",
                            data=pdf_bytes,
                            file_name=f"superadmin_report_{report_start}_{report_end}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.toast("✅ Report generated successfully", icon="✅")
                    else:
                        st.error("Failed to generate PDF report")

        # Data export options
        st.markdown("### 📊 Export Raw Data")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Export Revenue Data", use_container_width=True):
                if 'df_rev' in locals():
                    csv = df_rev.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download as CSV",
                        data=csv,
                        file_name="revenue_data.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.warning("No revenue data to export")
        
        with col2:
            if st.button("💾 Export Subscription Data", use_container_width=True):
                if 'df_plans' in locals():
                    csv = df_plans.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download as CSV",
                        data=csv,
                        file_name="subscription_data.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.warning("No subscription data to export")

    conn.close()

if __name__ == "__main__":
    superadmin_dashboard()