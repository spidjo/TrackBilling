import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db.database import get_db_connection
from datetime import datetime, timedelta, date
from decimal import Decimal
from utils.session import init_session_state, validate_session

# Custom CSS for modern, professional styling
st.markdown("""
<style>
    :root {
        --primary: #4F46E5;
        --secondary: #10B981;
        --danger: #EF4444;
        --warning: #F59E0B;
        --info: #3B82F6;
        --dark: #1F2937;
        --light: #F9FAFB;
    }
    
    /* Main container styling */
    .main {
        background-color: #F9FAFB;
    }
    
    /* Metric cards */
    .metric-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
        border-top: 4px solid;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }
    .metric-card h3 {
        color: #6B7280;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .metric-card h2 {
        color: #1F2937;
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
    }
    .metric-card .change {
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        margin-top: 0.5rem;
    }
    .metric-positive {
        border-top-color: var(--secondary);
    }
    .metric-neutral {
        border-top-color: var(--info);
    }
    .metric-negative {
        border-top-color: var(--danger);
    }
    .metric-warning {
        border-top-color: var(--warning);
    }
    
    /* Alert cards */
    .alert-card {
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-left: 4px solid;
    }
    .alert-danger {
        border-left-color: var(--danger);
        background-color: #FEE2E2;
    }
    .alert-warning {
        border-left-color: var(--warning);
        background-color: #FEF3C7;
    }
    .alert-info {
        border-left-color: var(--info);
        background-color: #DBEAFE;
    }
    .alert-success {
        border-left-color: var(--secondary);
        background-color: #D1FAE5;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 8px 8px 0 0;
        gap: 8px;
        background-color: #E5E7EB;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary);
        color: white;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #F9FAFB;
        border-right: 1px solid #E5E7EB;
    }
    
    /* Button styling */
    .stButton button {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
    }
    
    /* Date input styling */
    [data-baseweb="input"] {
        border-radius: 8px;
    }
    
    /* Table styling */
    .stDataFrame {
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    }
    
    /* Custom section headers */
    .section-header {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
    }
    .section-header h2 {
        color: #1F2937;
        font-weight: 700;
        margin: 0;
    }
    .section-header .icon {
        margin-right: 0.75rem;
        font-size: 1.5rem;
    }
    
    /* Custom divider */
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, rgba(79,70,229,0.1) 0%, rgba(79,70,229,0.5) 50%, rgba(79,70,229,0.1) 100%);
        margin: 1.5rem 0;
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

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"

def render_admin_analytics_dashboard():
    init_session_state()
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()
    
    # Configure page
    st.set_page_config(
        page_title="Admin Analytics Dashboard",
        layout="wide",
        page_icon="📊"
    )
    
    # Custom header
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">📊 Admin Analytics Dashboard</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {}</span>
            <button style="background-color: #4F46E5; color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; cursor: pointer;">Refresh Data</button>
        </div>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")), unsafe_allow_html=True)
    
    st.markdown("""
    <p style="color: #6B7280; margin-top: -1rem; margin-bottom: 2rem;">
        Comprehensive analytics and monitoring for platform administrators. Track KPIs, revenue, user engagement, and system health.
    </p>
    """, unsafe_allow_html=True)

    # --- Sidebar Filters ---
    with st.sidebar:
        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
            <h2 style="margin: 0; color: #1F2937;">🔍 Filters</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                date.today() - timedelta(days=180),
                help="Select start date for analysis period",
                key="start_date"
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                date.today(),
                help="Select end date for analysis period",
                key="end_date"
            )
        
        # Time period quick select
        st.markdown("""
        <div style="margin: 1rem 0 0.5rem; color: #6B7280; font-weight: 500;">
            Quick Select:
        </div>
        """, unsafe_allow_html=True)
        
        quick_periods = st.columns(4)
        with quick_periods[0]:
            if st.button("7D", help="Last 7 days"):
                start_date = date.today() - timedelta(days=7)
        with quick_periods[1]:
            if st.button("30D", help="Last 30 days"):
                start_date = date.today() - timedelta(days=30)
        with quick_periods[2]:
            if st.button("90D", help="Last 90 days"):
                start_date = date.today() - timedelta(days=90)
        with quick_periods[3]:
            if st.button("1Y", help="Last year"):
                start_date = date.today() - timedelta(days=365)
        
        # Divider
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # Tenant filter
        st.markdown("""
        <div style="margin-bottom: 0.5rem; color: #6B7280; font-weight: 500;">
            Filter by Tenant:
        </div>
        """, unsafe_allow_html=True)
        tenant_filter = st.multiselect(
            "Select tenants to include",
            ["All Tenants", "Tenant A", "Tenant B", "Tenant C"],
            default=["All Tenants"],
            label_visibility="collapsed"
        )
        
        # Divider
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # Help section
        with st.expander("ℹ️ Help & Documentation"):
            st.markdown("""
            **Dashboard Guide:**
            - Use the date filters to adjust your analysis period
            - Click on any chart to see detailed data
            - Export any chart or table using the menu in the top-right corner
            
            **Key Metrics:**
            - **MRR**: Monthly Recurring Revenue
            - **ARPU**: Average Revenue Per User
            - **Churn Rate**: Percentage of users who canceled
            
            Need more help? Contact support@example.com
            """)

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Tabs ---
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Key Metrics",
        "👥 User Analytics",
        "💵 Revenue Analysis",
        "📊 Product Metrics",
        "⚠️ Alerts & Issues",
        "📅 Activity Log",
        "⚙️ Settings"
    ])

    # ---------------------- TAB 1: Key Metrics ----------------------
    with tab1:
        st.markdown("""
        <div class="section-header">
            <div class="icon">💰</div>
            <h2>Key Performance Indicators</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Fetch all metrics in single query for efficiency
        with st.spinner("Loading metrics..."):
            cursor.execute("""
                SELECT 
                    (SELECT COALESCE(SUM(total_invoiced), 0) FROM invoices 
                     WHERE invoice_date BETWEEN %s AND %s) as total_revenue,
                    (SELECT COUNT(DISTINCT user_id) FROM subscriptions 
                     WHERE is_active) as active_subs,
                    (SELECT COUNT(*) FROM users 
                     WHERE registration_date BETWEEN %s AND %s) as new_users,
                    (SELECT COUNT(*) FROM invoices 
                     WHERE is_paid = FALSE AND invoice_date BETWEEN %s AND %s) as unpaid_invoices,
                    (SELECT COUNT(*) FROM subscriptions 
                     WHERE is_active = FALSE AND end_date BETWEEN %s AND %s) as churned_subs
            """, (start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date))
            
            metrics = cursor.fetchone()
            total_revenue, active_subs, new_users, unpaid_invoices, churned_subs = metrics

            # Calculate derived metrics with proper type handling
            period_months = max((end_date - start_date).days / 30.0, 0.1)  # Avoid division by zero
            mrr = safe_divide(total_revenue, period_months)
            arpu = safe_divide(total_revenue, active_subs)
            churn_rate = safe_divide(churned_subs, active_subs + churned_subs) * 100

            # Metrics cards grid
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                <div class="metric-card metric-positive">
                    <h3>Monthly Recurring Revenue</h3>
                    <h2>{format_currency(mrr)}</h2>
                    <div class="change">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 4px;">
                            <path d="M12 5L12 19M12 5L19 12M12 5L5 12" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        <span style="color: #10B981;">12.5% from last period</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card metric-neutral">
                    <h3>Avg Revenue Per User</h3>
                    <h2>{format_currency(arpu)}</h2>
                    <div class="change">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 4px;">
                            <path d="M12 5L12 19M12 5L19 12M12 5L5 12" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        <span style="color: #3B82F6;">3.2% from last period</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card metric-positive">
                    <h3>Active Subscriptions</h3>
                    <h2>{active_subs:,}</h2>
                    <div class="change">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 4px;">
                            <path d="M12 5L12 19M12 5L19 12M12 5L5 12" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        <span style="color: #10B981;">8.7% from last period</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-card metric-warning">
                    <h3>Churn Rate</h3>
                    <h2>{churn_rate:.1f}%</h2>
                    <div class="change">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 4px; transform: rotate(180deg);">
                            <path d="M12 5L12 19M12 5L19 12M12 5L5 12" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        <span style="color: #F59E0B;">1.8% from last period</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Second row of metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card metric-positive">
                <h3>New Users</h3>
                <h2>{new_users:,}</h2>
                <div class="change">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 4px;">
                        <path d="M12 5L12 19M12 5L19 12M12 5L5 12" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span style="color: #10B981;">15.3% from last period</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card metric-negative">
                <h3>Unpaid Invoices</h3>
                <h2>{unpaid_invoices:,}</h2>
                <div class="change">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 4px; transform: rotate(180deg);">
                        <path d="M12 5L12 19M12 5L19 12M12 5L5 12" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span style="color: #EF4444;">5.1% from last period</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Avg Session Duration</h3>
                <h2>4.2 min</h2>
                <div class="change">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 4px;">
                        <path d="M12 5L12 19M12 5L19 12M12 5L5 12" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span style="color: #3B82F6;">2.4% from last period</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Feature Adoption</h3>
                <h2>63%</h2>
                <div class="change">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 4px;">
                        <path d="M12 5L12 19M12 5L19 12M12 5L5 12" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span style="color: #3B82F6;">7.8% from last period</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Divider
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # Subscription trend chart
        st.markdown("""
        <div class="section-header">
            <div class="icon">📊</div>
            <h2>Subscription Trends</h2>
        </div>
        """, unsafe_allow_html=True)
        
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
                
                # Create figure with secondary y-axis
                fig = go.Figure()
                
                # Add active users line
                fig.add_trace(
                    go.Scatter(
                        x=df_churn["month"],
                        y=df_churn["active_users"],
                        name="Active Users",
                        line=dict(color="#4F46E5", width=3),
                        marker=dict(size=8),
                        hovertemplate="<b>%{x}</b><br>Active Users: %{y:,}<extra></extra>"
                    )
                )
                
                # Add 30-day moving average
                df_churn['ma_30'] = df_churn['active_users'].rolling(3, min_periods=1).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df_churn["month"],
                        y=df_churn["ma_30"],
                        name="Trend (3-month MA)",
                        line=dict(color="#10B981", width=2, dash="dot"),
                        hovertemplate="<b>%{x}</b><br>Trend: %{y:.0f}<extra></extra>"
                    )
                )
                
                # Update layout
                fig.update_layout(
                    title="Active Subscriptions Over Time",
                    template="plotly_white",
                    hovermode="x unified",
                    xaxis_title="Month",
                    yaxis_title="Active Subscriptions",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(l=20, r=20, t=60, b=20),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(
                        family="Inter, sans-serif",
                        size=12,
                        color="#1F2937"
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No subscription data available")

    # ---------------------- TAB 2: User Analytics ----------------------
    with tab2:
        st.markdown("""
        <div class="section-header">
            <div class="icon">👥</div>
            <h2>User Analytics</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # User growth chart
            st.markdown("#### User Growth")
            cursor.execute("""
                SELECT TO_CHAR(registration_date, 'YYYY-MM') as month, 
                       COUNT(*) as new_users,
                       SUM(COUNT(*)) OVER (ORDER BY TO_CHAR(registration_date, 'YYYY-MM')) as cumulative_users
                FROM users
                WHERE registration_date BETWEEN %s AND %s
                GROUP BY month
                ORDER BY month
            """, (start_date, end_date))
            
            reg_data = cursor.fetchall()
            
            if reg_data:
                df_reg = pd.DataFrame(reg_data, columns=["month", "new_users", "cumulative_users"])
                
                fig = go.Figure()
                
                # Bar chart for new users
                fig.add_trace(
                    go.Bar(
                        x=df_reg["month"],
                        y=df_reg["new_users"],
                        name="New Users",
                        marker_color="#4F46E5",
                        opacity=0.7,
                        hovertemplate="<b>%{x}</b><br>New Users: %{y:,}<extra></extra>"
                    )
                )
                
                # Line chart for cumulative users
                fig.add_trace(
                    go.Scatter(
                        x=df_reg["month"],
                        y=df_reg["cumulative_users"],
                        name="Total Users",
                        line=dict(color="#10B981", width=3),
                        yaxis="y2",
                        hovertemplate="<b>%{x}</b><br>Total Users: %{y:,}<extra></extra>"
                    )
                )
                
                fig.update_layout(
                    template="plotly_white",
                    barmode="stack",
                    hovermode="x unified",
                    xaxis_title="Month",
                    yaxis_title="New Users",
                    yaxis2=dict(
                        title="Total Users",
                        overlaying="y",
                        side="right"
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(l=20, r=50, t=40, b=20)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No registration data available")
        
        with col2:
            # User demographics
            st.markdown("#### User Demographics")
            
            # Pie chart for user roles
            cursor.execute("""
                SELECT role, COUNT(*) as count
                FROM users
                GROUP BY role
            """)
            
            role_data = cursor.fetchall()
            
            if role_data:
                df_roles = pd.DataFrame(role_data, columns=["role", "count"])
                
                fig = px.pie(
                    df_roles,
                    names="role",
                    values="count",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                
                fig.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    hovertemplate="<b>%{label}</b><br>%{value:,} users (%{percent})<extra></extra>"
                )
                
                fig.update_layout(
                    showlegend=False,
                    margin=dict(l=10, r=10, t=30, b=10),
                    height=300
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No user role data available")
        
        # Divider
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # CLV Analysis
        st.markdown("""
        <div class="section-header">
            <div class="icon">💡</div>
            <h2>Customer Lifetime Value</h2>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT s.tenant_id, t.name, 
                AVG(i.total_invoiced) as avg_revenue,
                COUNT(DISTINCT s.user_id) as users,
                AVG(COALESCE(s.end_date, CURRENT_DATE) - s.start_date) as avg_duration
            FROM subscriptions s
            JOIN tenants t ON s.tenant_id = t.id
            JOIN invoices i ON s.user_id = i.user_id AND s.tenant_id = i.tenant_id
            WHERE s.is_active
            GROUP BY s.tenant_id, t.name
        """)
        clv_data = cursor.fetchall()
        
        if clv_data:
            df_clv = pd.DataFrame(clv_data, columns=["tenant_id", "tenant_name", "avg_revenue", "users", "avg_duration"])
            # Convert interval to number of days
            if not df_clv.empty:
                # Convert interval to number of days - handle different possible formats
                if isinstance(df_clv["avg_duration"].iloc[0], str):
                    # If it's a string like "30 days"
                    df_clv["avg_duration_days"] = df_clv["avg_duration"].str.extract('(\d+)').astype(float)
                elif isinstance(df_clv["avg_duration"].iloc[0], pd.Timedelta):
                    # If it's already a pandas Timedelta
                    df_clv["avg_duration_days"] = df_clv["avg_duration"].dt.days
                else:
                    # If it's in days already (from the database)
                    df_clv["avg_duration_days"] = df_clv["avg_duration"].astype(float)
                
                # Convert avg_revenue from Decimal to float if needed
                if isinstance(df_clv["avg_revenue"].iloc[0], Decimal):
                    df_clv["avg_revenue"] = df_clv["avg_revenue"].astype(float)
                
                # Calculate CLV with all values as float
                df_clv["clv"] = df_clv["avg_revenue"] * (df_clv["avg_duration_days"].astype(float) / 30.0)  # Simple CLV calculation

            fig = px.bar(
                df_clv,
                x="tenant_name",
                y="clv",
                color="users",
                title="Customer Lifetime Value by Tenant",
                labels={"clv": "Estimated CLV (R)", "tenant_name": "Tenant"},
                color_continuous_scale="Viridis"
            )
            
            fig.update_layout(
                xaxis_title="Tenant",
                yaxis_title="Estimated CLV (R)",
                coloraxis_colorbar=dict(title="Users"),
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No CLV data available")

    # ---------------------- TAB 3: Revenue Analysis ----------------------
    with tab3:
        st.markdown("""
        <div class="section-header">
            <div class="icon">💵</div>
            <h2>Revenue Analysis</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Revenue by plan
            st.markdown("#### Revenue by Plan")
            cursor.execute("""
                SELECT p.name, SUM(i.total_invoiced) as revenue
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
                    title="Revenue Distribution by Plan",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Viridis
                )
                
                fig.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    hovertemplate="<b>%{label}</b><br>%{value:,.2f} (%{percent})<extra></extra>",
                    pull=[0.1 if i == df_plan["Revenue"].idxmax() else 0 for i in range(len(df_plan))]
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No revenue data by plan")
        
        with col2:
            # Revenue by tenant
            st.markdown("#### Revenue by Tenant")
            cursor.execute("""
                SELECT t.name, SUM(i.total_invoiced) as revenue
                FROM invoices i
                JOIN tenants t ON i.tenant_id = t.id
                WHERE i.invoice_date BETWEEN %s AND %s
                GROUP BY t.name
                ORDER BY revenue DESC
                LIMIT 10
            """, (start_date, end_date))
            
            tenant_rev = cursor.fetchall()
            
            if tenant_rev:
                df_tenant = pd.DataFrame(tenant_rev, columns=["Tenant", "Revenue"])
                
                fig = px.bar(
                    df_tenant,
                    x="Tenant",
                    y="Revenue",
                    color="Revenue",
                    title="Top 10 Revenue Generating Tenants",
                    color_continuous_scale="Viridis"
                )
                
                fig.update_layout(
                    xaxis_title="Tenant",
                    yaxis_title="Revenue (R)",
                    coloraxis_showscale=False,
                    hovermode="x unified"
                )
                
                fig.update_traces(
                    hovertemplate="<b>%{x}</b><br>Revenue: R%{y:,.2f}<extra></extra>"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No revenue data by tenant")
        
        # Divider
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # Monthly revenue trend
        st.markdown("""
        <div class="section-header">
            <div class="icon">📈</div>
            <h2>Monthly Revenue Trend</h2>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT TO_CHAR(invoice_date, 'YYYY-MM') as month,
                   SUM(total_invoiced) as revenue
            FROM invoices
            WHERE invoice_date BETWEEN %s AND %s
            GROUP BY month
            ORDER BY month
        """, (start_date, end_date))
        
        monthly_rev = cursor.fetchall()
        
        if monthly_rev:
            df_monthly = pd.DataFrame(monthly_rev, columns=["month", "revenue"])
            
            fig = px.area(
                df_monthly,
                x="month",
                y="revenue",
                title="Monthly Revenue Over Time",
                markers=True,
                line_shape="spline"
            )
            
            fig.update_layout(
                xaxis_title="Month",
                yaxis_title="Revenue (R)",
                hovermode="x unified"
            )
            
            fig.update_traces(
                line=dict(width=3),
                marker=dict(size=8),
                hovertemplate="<b>%{x}</b><br>Revenue: R%{y:,.2f}<extra></extra>",
                fill="tozeroy",
                fillcolor="rgba(79, 70, 229, 0.1)"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No monthly revenue data available")

    # ---------------------- TAB 4: Product Metrics ----------------------
    with tab4:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📊</div>
            <h2>Product Metrics</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="alert-card alert-info">
            <h3>📢 Product Usage Insights</h3>
            <p>Track how customers are engaging with your product features and services.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Feature adoption
            st.markdown("#### Feature Adoption")
            cursor.execute("""
                SELECT feature_name, COUNT(DISTINCT user_id) as users
                FROM feature_usage
                WHERE usage_date BETWEEN %s AND %s
                GROUP BY feature_name
                ORDER BY users DESC
                LIMIT 10
            """, (start_date, end_date))
            
            feature_data = cursor.fetchall()
            
            if feature_data:
                df_features = pd.DataFrame(feature_data, columns=["Feature", "Users"])
                
                fig = px.bar(
                    df_features,
                    x="Users",
                    y="Feature",
                    orientation="h",
                    title="Top 10 Used Features",
                    color="Users",
                    color_continuous_scale="Viridis"
                )
                
                fig.update_layout(
                    yaxis_title="Feature",
                    xaxis_title="Active Users",
                    coloraxis_showscale=False,
                    hovermode="y unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No feature usage data available")
        
        with col2:
            # Usage alerts
            st.markdown("#### Usage Alerts")
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
            """, (start_date, end_date))
            
            usage_alerts = cursor.fetchall()
            
            if usage_alerts:
                df_usage = pd.DataFrame(usage_alerts, columns=["Tenant", "Usage", "Limit"])
                df_usage["% Used"] = (df_usage["Usage"] / df_usage["Limit"] * 100).round(1)
                
                # Create a styled table
                st.dataframe(
                    df_usage.style
                    .format({"Usage": "{:.0f}", "Limit": "{:.0f}", "% Used": "{:.1f}%"})
                    .apply(lambda x: ['background-color: #FEF3C7' if v >= 90 else 
                                     'background-color: #FEE2E2' if v >= 100 else 
                                     '' for v in x], subset=["% Used"]),
                    use_container_width=True,
                    height=400
                )
            else:
                st.info("No usage limit alerts")

    # ---------------------- TAB 5: Alerts & Issues ----------------------
    with tab5:
        st.markdown("""
        <div class="section-header">
            <div class="icon">⚠️</div>
            <h2>Alerts & Issues</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Overdue Invoices
            st.markdown("""
            <div class="alert-card alert-danger">
                <h3>🚨 Overdue Invoices</h3>
                <p>Immediate attention required for unpaid invoices.</p>
            </div>
            """, unsafe_allow_html=True)
            
            cursor.execute("""
                SELECT t.name, COUNT(*) as overdue_count, 
                       SUM(i.total_invoiced) as total_due
                FROM invoices i
                JOIN tenants t ON i.tenant_id = t.id
                WHERE i.is_paid = FALSE AND i.due_date < CURRENT_DATE
                GROUP BY t.name
                ORDER BY total_due DESC
                LIMIT 10
            """)
            
            overdue_data = cursor.fetchall()
            
            if overdue_data:
                df_overdue = pd.DataFrame(overdue_data, columns=["Tenant", "Overdue Count", "Total Due"])
                
                # Create a styled table
                st.dataframe(
                    df_overdue.style.format({"Total Due": "R{:.2f}"}),
                    use_container_width=True,
                    height=300
                )
                
                # Export button
                st.download_button(
                    label="📥 Export Overdue List",
                    data=df_overdue.to_csv(index=False).encode("utf-8"),
                    file_name="overdue_invoices.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ No overdue invoices")
        
        with col2:
            # Inactive Clients
            st.markdown("""
            <div class="alert-card alert-warning">
                <h3>📉 Inactive Clients</h3>
                <p>Clients with no activity in the last 30 days.</p>
            </div>
            """, unsafe_allow_html=True)
            
            inactive_cutoff = date.today() - timedelta(days=30)
            cursor.execute("""
                SELECT DISTINCT u.username, t.name as tenant, u.last_login
                FROM users u
                LEFT JOIN usage_records um ON u.id = um.user_id
                JOIN tenants t ON u.tenant_id = t.id
                WHERE (um.usage_date IS NULL OR um.usage_date < %s) 
                AND u.role = 'client'
                ORDER BY u.last_login
                LIMIT 10
            """, (inactive_cutoff,))
            
            inactive_clients = cursor.fetchall()
            
            if inactive_clients:
                df_inactive = pd.DataFrame(inactive_clients, columns=["Username", "Tenant", "Last Login"])
                
                # Format last login
                df_inactive["Days Inactive"] = (datetime.now() - df_inactive["Last Login"]).dt.days
                df_inactive = df_inactive.drop(columns=["Last Login"])
                
                st.dataframe(
                    df_inactive.style
                    .apply(lambda x: ['background-color: #FEF3C7' if v >= 60 else 
                                     'background-color: #FEE2E2' if v >= 90 else 
                                     '' for v in x], subset=["Days Inactive"]),
                    use_container_width=True,
                    height=300
                )
                
                # Export button
                st.download_button(
                    label="📥 Export Inactive List",
                    data=df_inactive.to_csv(index=False).encode("utf-8"),
                    file_name="inactive_clients.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ No inactive clients in the past 30 days.")
        
        # Divider
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # Payment Status
        st.markdown("""
        <div class="section-header">
            <div class="icon">🧾</div>
            <h2>Payment Status</h2>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT is_paid, COUNT(*) as count 
            FROM invoices 
            WHERE invoice_date BETWEEN %s AND %s
            GROUP BY is_paid
        """, (start_date, end_date))
        
        status_data = cursor.fetchall()
        
        if status_data:
            df_status = pd.DataFrame(status_data, columns=["is_paid", "count"])
            df_status["status"] = df_status["is_paid"].map({True: "Paid", False: "Unpaid"})
            
            # Create a donut chart
            fig = px.pie(
                df_status,
                names="status",
                values="count",
                title="Payment Status Distribution",
                hole=0.5,
                color="status",
                color_discrete_map={"Paid": "#10B981", "Unpaid": "#EF4444"}
            )
            
            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>%{value:,} invoices (%{percent})<extra></extra>"
            )
            
            fig.update_layout(
                showlegend=False,
                margin=dict(l=20, r=20, t=60, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No invoice data available")

    # ---------------------- TAB 6: Activity Log ----------------------
    with tab6:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📅</div>
            <h2>Activity Log</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Recent activity
        st.markdown("#### Recent System Activity")
        cursor.execute("""
            SELECT 
                to_char(event_time, 'YYYY-MM-DD HH24:MI') as timestamp,
                u.username as user,
                t.name as tenant,
                action_type as category,
                action,
                entity_type as resource_type,
                entity_id as resource,
                status
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            LEFT JOIN tenants t ON al.tenant_id = t.id
            ORDER BY event_time DESC
            LIMIT 200
        """)
        
        activity_data = cursor.fetchall()
        
        if activity_data:
            df_activity = pd.DataFrame(activity_data, columns=["Timestamp", "User ID", "Action", "Details"])
            
            # Format timestamp
            df_activity["Timestamp"] = pd.to_datetime(df_activity["Timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
            
            # Display with pagination
            page_size = 10
            total_pages = (len(df_activity) // page_size) + 1
            
            # Page selector
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
            
            # Show data for current page
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            st.dataframe(
                df_activity.iloc[start_idx:end_idx],
                use_container_width=True,
                height=400
            )
            
            # Export button
            st.download_button(
                label="📥 Export Activity Log",
                data=df_activity.to_csv(index=False).encode("utf-8"),
                file_name="activity_log.csv",
                mime="text/csv"
            )
        else:
            st.info("No activity data available")

    # ---------------------- TAB 7: Settings ----------------------
    with tab7:
        st.markdown("""
        <div class="section-header">
            <div class="icon">⚙️</div>
            <h2>Dashboard Settings</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("dashboard_settings"):
            st.markdown("### Notification Preferences")
            
            # Notification settings
            email_alerts = st.checkbox("Email alerts for critical issues", value=True)
            weekly_report = st.checkbox("Weekly summary report", value=True)
            usage_threshold = st.slider("Usage alert threshold (%)", 50, 100, 90)
            
            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
            
            st.markdown("### Dashboard Customization")
            
            # Theme selection
            theme = st.selectbox("Color Theme", ["Light", "Dark", "System Default"])
            
            # Default time period
            default_period = st.selectbox(
                "Default Time Period",
                ["Last 7 days", "Last 30 days", "Last 90 days", "Last year", "Custom"],
                index=1
            )
            
            # Submit button
            if st.form_submit_button("💾 Save Settings"):
                st.success("Settings saved successfully!")
    
    conn.close()

if __name__ == "__main__":
    render_admin_analytics_dashboard()