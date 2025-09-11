import streamlit as st
from datetime import datetime, timedelta
from db.database import get_db_connection
from utils.session_guard import require_login
from utils.report_utils import generate_superadmin_pdf_report
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================================
# CUSTOM STYLING
# ==============================================
st.markdown("""
<style>
    :root {
        --primary-color: #4f46e5;
        --primary-dark: #4338ca;
        --secondary-color: #f9fafb;
        --accent-color: #10b981;
        --danger-color: #ef4444;
        --warning-color: #f59e0b;
        --info-color: #3b82f6;
        --text-primary: #1f2937;
        --text-secondary: #6b7280;
        --border-color: #e5e7eb;
        --card-bg: #ffffff;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.12);
        --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stApp {
        background-color: #f9fafb;
    }
    
    /* Main containers */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 95%;
    }
    
    /* Cards */
    .metric-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: var(--card-bg);
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-color);
        transition: all 0.2s ease;
    }
    
    .metric-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }
    
    .metric-card h3 {
        color: var(--text-secondary);
        font-size: 1rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    
    .metric-card h2 {
        color: var(--text-primary);
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
    }
    
    .positive-metric {
        border-left: 4px solid var(--accent-color);
    }
    
    .negative-metric {
        border-left: 4px solid var(--danger-color);
    }
    
    .neutral-metric {
        border-left: 4px solid var(--info-color);
    }
    
    /* Tabs */
    .stTabs [role="tablist"] {
        gap: 0.5rem;
    }
    
    .stTabs [role="tab"] {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        transition: all 0.2s ease;
        font-weight: 500;
    }
    
    .stTabs [role="tab"][aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
    }
    
    .stTabs [role="tab"][aria-selected="false"]:hover {
        background-color: #f3f4f6;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-1px);
    }
    
    .stButton button:active {
        transform: translateY(0);
    }
    
    /* Date inputs */
    .stDateInput input {
        border-radius: 8px !important;
    }
    
    /* Filters section */
    .stExpander [data-testid="stExpander"] {
        border-radius: 12px;
        border: 1px solid var(--border-color);
    }
    
    /* Custom section headers */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }
    
    .section-header h2 {
        margin: 0;
        color: var(--text-primary);
    }
    
    .section-header .divider {
        flex-grow: 1;
        height: 1px;
        background-color: var(--border-color);
    }
    
    /* Tooltip styling */
    .stTooltip {
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================
# DASHBOARD FUNCTION
# ==============================================
def superadmin_dashboard():
    st.set_page_config(
        page_title="SuperAdmin Dashboard | SaaS Analytics", 
        layout="wide",
        page_icon="📊"
    )
    require_login("superadmin")
    
    # Page header with breadcrumb
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.5rem;">
            SuperAdmin Panel / Analytics Dashboard
        </div>
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <h1 style="margin: 0; flex-grow: 1;">Platform Analytics Dashboard</h1>
        </div>
        <div style="height: 2px; background: linear-gradient(to right, #4f46e5, transparent); margin-top: 0.5rem;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Comprehensive overview of platform performance and tenant analytics")
    
    # --- Filters Section ---
    with st.expander("🔍 Filter Dashboard Data", expanded=True):
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
    tenant_filter_params = ()
    if selected_tenant != "All Tenants":
        tenant_id = int(selected_tenant.split("ID: ")[1].rstrip(")"))
        tenant_filter_sql = "AND u.tenant_id = %s"
        tenant_filter_params = (tenant_id,)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    # --- TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview Metrics",
        "💰 Revenue Analytics",
        "📉 Churn Analysis",
        "📤 Export Center"
    ])

    # ---------------------- TAB 1: Overview Metrics ----------------------
    with tab1:
        # Key Metrics Section
        st.markdown("""
        <div class="section-header">
            <h2>🔢 Key Performance Indicators</h2>
            <div class="divider"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Fetch all metrics in single query for efficiency
        query = f"""
            SELECT 
                (SELECT COUNT(*) FROM tenants) as total_tenants,
                (SELECT COUNT(*) FROM subscriptions s JOIN users u ON s.user_id = u.id 
                WHERE s.is_active {tenant_filter_sql}) as active_subs,
                (SELECT COALESCE(SUM(total_invoiced), 0) FROM invoices i JOIN users u ON i.user_id = u.id 
                WHERE i.invoice_date BETWEEN %s AND %s {tenant_filter_sql}) as total_revenue,
                (SELECT COUNT(*) FROM usage_records ur JOIN users u ON ur.user_id = u.id 
                WHERE ur.usage_date BETWEEN %s AND %s {tenant_filter_sql}) as usage_logs
        """
        
        params = []
        params.extend(tenant_filter_params)
        params.extend([start_date_str, end_date_str])
        if tenant_filter_params:
            params.extend(tenant_filter_params)
        params.extend([start_date_str, end_date_str])
        if tenant_filter_params:
            params.extend(tenant_filter_params)

        cursor.execute(query, params)                
        metrics = cursor.fetchone()
        total_tenants, active_subs, total_revenue, usage_logs = metrics
        arpu = total_revenue / active_subs if active_subs > 0 else 0

        # Metrics cards grid
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

        # Top Subscribed Plans Section
        st.markdown("""
        <div class="section-header">
            <h2>📊 Top Subscribed Plans</h2>
            <div class="divider"></div>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute(f"""
            SELECT p.name, COUNT(*) as count FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            JOIN users u ON s.user_id = u.id
            WHERE s.is_active {tenant_filter_sql}
            GROUP BY p.name ORDER BY count DESC LIMIT 5
        """, tenant_filter_params)
        top_plans = cursor.fetchall()

        if top_plans:
            df_plans = pd.DataFrame(top_plans, columns=["Plan", "Subscribers"])
            fig = px.bar(
                df_plans,
                x="Plan",
                y="Subscribers",
                color="Subscribers",
                color_continuous_scale="Blues",
                text="Subscribers",
                template="plotly_white"
            )
            fig.update_layout(
                xaxis_title="Subscription Plan",
                yaxis_title="Number of Subscribers",
                showlegend=False,
                hovermode="x unified",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            fig.update_traces(
                marker_line_color='rgb(8,48,107)',
                marker_line_width=1.5,
                opacity=0.8
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active subscriptions found.")

    # ---------------------- TAB 2: Revenue Analytics ----------------------
    with tab2:
        st.markdown("""
        <div class="section-header">
            <h2>💰 Revenue Performance</h2>
            <div class="divider"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Revenue trend with Plotly
        cursor.execute(f"""
            SELECT DATE_TRUNC('month', i.invoice_date) AS month,
                   SUM(i.total_invoiced) as revenue
            FROM invoices i
            JOIN users u ON i.user_id = u.id
            WHERE i.invoice_date BETWEEN %s AND %s {tenant_filter_sql}
            GROUP BY month
            ORDER BY month
        """, (start_date_str, end_date_str, *tenant_filter_params))
        revenue_data = cursor.fetchall()

        if revenue_data:
            df_rev = pd.DataFrame(revenue_data, columns=["Month", "Revenue"])
            df_rev["Month"] = pd.to_datetime(df_rev["Month"]).dt.strftime("%b %Y")
            
            fig = px.line(
                df_rev,
                x="Month",
                y="Revenue",
                markers=True,
                title="",
                labels={"Revenue": "Revenue (R)"},
                template="plotly_white"
            )
            fig.update_layout(
                hovermode="x unified",
                xaxis_title="Month",
                yaxis_title="Revenue (R)",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            fig.update_traces(
                line=dict(width=3, color="#4f46e5"),
                marker=dict(size=8, color="#4f46e5", line=dict(width=2, color="white"))
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Revenue by tenant breakdown
            st.markdown("""
            <div class="section-header">
                <h2>📌 Revenue by Tenant</h2>
                <div class="divider"></div>
            </div>
            """, unsafe_allow_html=True)
            
            cursor.execute(f"""
                SELECT t.name as tenant, SUM(i.total_invoiced) as revenue
                FROM invoices i
                JOIN users u ON i.user_id = u.id
                JOIN tenants t ON u.tenant_id = t.id
                WHERE i.invoice_date BETWEEN %s AND %s {tenant_filter_sql}
                GROUP BY t.name
                ORDER BY revenue DESC
            """, (start_date_str, end_date_str, *tenant_filter_params))
            tenant_revenue = cursor.fetchall()
            
            if tenant_revenue:
                df_tenant = pd.DataFrame(tenant_revenue, columns=["Tenant", "Revenue"])
                fig = px.pie(
                    df_tenant,
                    names="Tenant",
                    values="Revenue",
                    title="",
                    template="plotly_white",
                    color_discrete_sequence=px.colors.sequential.Blues_r
                )
                fig.update_layout(
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.3,
                        xanchor="center",
                        x=0.5
                    )
                )
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    marker=dict(line=dict(color='#ffffff', width=1))
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No revenue data found in selected period.")

    # ---------------------- TAB 3: Churn Analysis ----------------------
    with tab3:
        st.markdown("""
        <div class="section-header">
            <h2>📉 Subscription Health</h2>
            <div class="divider"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Fetch churn metrics
        cursor.execute(f"""
            SELECT 
                (SELECT COUNT(*) FROM subscriptions s
                 JOIN users u ON s.user_id = u.id
                 WHERE s.is_active = False AND s.end_date BETWEEN %s AND %s {tenant_filter_sql}) as churned,
                (SELECT COUNT(*) FROM subscriptions s
                 JOIN users u ON s.user_id = u.id
                 WHERE s.start_date BETWEEN %s AND %s {tenant_filter_sql}) as new_subs
        """, (start_date_str, end_date_str, start_date_str, end_date_str, *tenant_filter_params))

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
        st.markdown("""
        <div class="section-header">
            <h2>📊 Retention Metrics</h2>
            <div class="divider"></div>
        </div>
        """, unsafe_allow_html=True)
        
        fig = go.Figure()
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=retention_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Retention Rate (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#10b981"},
                'steps': [
                    {'range': [0, 70], 'color': "#ef4444"},
                    {'range': [70, 90], 'color': "#f59e0b"},
                    {'range': [90, 100], 'color': "#10b981"}
                ],
                'threshold': {
                    'line': {'color': "white", 'width': 4},
                    'thickness': 0.75,
                    'value': retention_rate
                }
            }
        ))
        fig.update_layout(
            template="plotly_white",
            margin=dict(t=50, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.info(f"""
        **📈 Retention Rate:** `{retention_rate:.2f}%`  
        **📉 Churn Rate:** `{churn_rate:.2f}%`
        """)

    # ---------------------- TAB 4: Export Center ----------------------
    with tab4:
        st.markdown("""
        <div class="section-header">
            <h2>📤 Data Export Center</h2>
            <div class="divider"></div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("### 📅 Custom Report Generator")
            report_start = st.date_input("Report Start Date", start_date)
            report_end = st.date_input("Report End Date", end_date)
            
            if st.button("🔄 Generate Custom Report", type="primary", use_container_width=True):
                with st.spinner("Generating comprehensive report..."):
                    # Convert date objects to datetime objects
                    report_start_dt = datetime.combine(report_start, datetime.min.time())
                    report_end_dt = datetime.combine(report_end, datetime.max.time())
                    pdf_bytes = generate_superadmin_pdf_report(report_start_dt, report_end_dt)
                    
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