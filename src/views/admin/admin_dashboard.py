import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db.database import get_db_connection
from utils.ui_helpers import loading_spinner, show_toast
from utils.session import init_session_state, validate_session

# Custom CSS for professional styling
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
    
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, rgba(79,70,229,0.1) 0%, rgba(79,70,229,0.5) 50%, rgba(79,70,229,0.1) 100%);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"

def admin_dashboard():
    """Enhanced Tenant Admin Dashboard with professional UX"""
    init_session_state()
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()
        
    # Page configuration
    st.set_page_config(
        page_title="Tenant Admin Dashboard",
        layout="wide",
        page_icon="📊"
    )
    
    if 'tenant_id' not in st.session_state:
        st.error("Access denied. Please log in as admin.")
        st.stop()

    tenant_id = st.session_state.tenant_id

    # Initialize session state for filters
    if 'filter_user' not in st.session_state:
        st.session_state.filter_user = "All"
    if 'filter_date_range' not in st.session_state:
        st.session_state.filter_date_range = [
            datetime.now() - timedelta(days=30),
            datetime.now()
        ]

    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">📊 Tenant Admin Dashboard</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            <button style="background-color: #4F46E5; color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; cursor: pointer;">Refresh Data</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # Database connection with loading spinner
    with loading_spinner("Loading dashboard data..."):
        conn = get_db_connection()
        cursor = conn.cursor()

        # --- Common Data Fetching ---
        # Get all users for filters
        cursor.execute("""
            SELECT id, username FROM users 
            WHERE tenant_id = %s AND is_active = 1
            ORDER BY username
        """, (tenant_id,))
        all_users = cursor.fetchall()
        user_options = ["All"] + [f"{user[1]} (ID: {user[0]})" for user in all_users]

        # Get current plan limits
        cursor.execute("""
            SELECT p.name, p.included_units FROM plans p
            JOIN subscriptions s ON p.id = s.plan_id
            WHERE s.tenant_id = %s AND s.is_active = TRUE
            LIMIT 1
        """, (tenant_id,))
        plan = cursor.fetchone()
        plan_name = plan[0] if plan else "No active plan"
        included_units = plan[1] if plan else 0

        # Get tenant name
        cursor.execute("SELECT name FROM tenants WHERE id = %s", (tenant_id,))
        tenant_name = cursor.fetchone()[0]

        # --- Summary Metrics ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE tenant_id = %s AND is_active = 1
            """, (tenant_id,))
            active_users = cursor.fetchone()[0]
            st.markdown(f"""
            <div class="metric-card metric-positive">
                <h3>Active Users</h3>
                <h2>{active_users:,}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            cursor.execute("""
                SELECT COALESCE(SUM(total_invoiced), 0) 
                FROM invoices 
                WHERE tenant_id = %s AND is_paid = FALSE
            """, (tenant_id,))
            outstanding = cursor.fetchone()[0]
            st.markdown(f"""
            <div class="metric-card metric-negative">
                <h3>Outstanding Balance</h3>
                <h2>{format_currency(outstanding)}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            cursor.execute("""
                SELECT COALESCE(SUM(usage_amount), 0) 
                FROM usage_records 
                WHERE tenant_id = %s 
                AND usage_date BETWEEN date_trunc('month', CURRENT_DATE) AND CURRENT_DATE
            """, (tenant_id,))
            monthly_usage = cursor.fetchone()[0]
            usage_pct = (monthly_usage / included_units * 100) if included_units > 0 else 0
            st.markdown(f"""
            <div class="metric-card metric-{'warning' if usage_pct > 80 else 'neutral'}">
                <h3>Monthly Usage</h3>
                <h2>{monthly_usage:,}/{included_units:,}</h2>
                <div style="margin-top: 0.5rem;">
                    <span style="color: {'#F59E0B' if usage_pct > 80 else '#3B82F6'};">{usage_pct:.1f}% of limit</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            cursor.execute("""
                SELECT COUNT(*) FROM invoices 
                WHERE tenant_id = %s 
                AND due_date < CURRENT_DATE 
                AND is_paid = FALSE
            """, (tenant_id,))
            overdue_invoices = cursor.fetchone()[0]
            st.markdown(f"""
            <div class="metric-card metric-{'danger' if overdue_invoices > 0 else 'success'}">
                <h3>Overdue Invoices</h3>
                <h2>{overdue_invoices}</h2>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # --- Tabs Layout ---
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Usage Analytics", 
            "🧾 Billing & Invoices", 
            "👥 User Management", 
            "🚨 Alerts & Notifications"
        ])

        with tab1:
            # Usage Analytics Tab
            st.markdown("""
            <div class="section-header">
                <div class="icon">📊</div>
                <h2>Usage Analytics</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Filters sidebar
            with st.sidebar:
                st.markdown("""
                <div style="margin-bottom: 1.5rem;">
                    <h3 style="color: #1F2937; margin-bottom: 0.5rem;">🔍 Filters</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.session_state.filter_user = st.selectbox(
                    "Filter by User",
                    user_options,
                    index=user_options.index(st.session_state.filter_user),
                    key="user_filter_select"
                )
                
                st.session_state.filter_date_range = st.date_input(
                    "Date Range",
                    value=st.session_state.filter_date_range,
                    max_value=datetime.now(),
                    key="date_range_filter"
                )
                
                metric_filter = st.text_input(
                    "Filter by Metric Name",
                    placeholder="Search metrics...",
                    key="metric_filter"
                )

            # Apply filters to data
            user_filter = st.session_state.filter_user.split("(ID: ")[1][:-1] if st.session_state.filter_user != "All" else None
            date_filter = st.session_state.filter_date_range if len(st.session_state.filter_date_range) == 2 else None

            # Get usage data
            query = """
                SELECT 
                    ur.usage_date,
                    u.username,
                    ur.metric_name,
                    ur.usage_amount
                FROM usage_records ur
                JOIN users u ON ur.user_id = u.id
                WHERE ur.tenant_id = %s
            """
            params = [tenant_id]

            if user_filter:
                query += " AND ur.user_id = %s"
                params.append(user_filter)
            if metric_filter:
                query += " AND ur.metric_name ILIKE %s"
                params.append(f"%{metric_filter}%")
            if date_filter:
                query += " AND ur.usage_date BETWEEN %s AND %s"
                params.extend(date_filter)

            query += " ORDER BY ur.usage_date DESC"
            cursor.execute(query, tuple(params))
            usage_data = cursor.fetchall()

            if not usage_data:
                st.info("No usage data found for selected filters")
            else:
                # Create DataFrame
                df = pd.DataFrame(usage_data, columns=["Date", "User", "Metric", "Quantity"])
                df["Date"] = pd.to_datetime(df["Date"])
                df["Month"] = df["Date"].dt.to_period("M").astype(str)

                # Visualizations
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📈</div>
                    <h2>Usage Trends</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # Time series chart with Plotly
                trend_data = df.groupby(["Date", "Metric"])["Quantity"].sum().reset_index()
                fig = px.area(
                    trend_data,
                    x="Date",
                    y="Quantity",
                    color="Metric",
                    title="Usage Over Time",
                    template="plotly_white",
                    line_shape="spline"
                )
                fig.update_layout(
                    hovermode="x unified",
                    xaxis_title="Date",
                    yaxis_title="Usage Quantity",
                    legend_title="Metric"
                )
                st.plotly_chart(fig, use_container_width=True)

                # Top users chart
                st.markdown("""
                <div class="section-header">
                    <div class="icon">👥</div>
                    <h2>Usage by User</h2>
                </div>
                """, unsafe_allow_html=True)
                
                user_data = df.groupby("User")["Quantity"].sum().reset_index().sort_values("Quantity", ascending=False)
                fig = px.bar(
                    user_data,
                    x="User",
                    y="Quantity",
                    color="Quantity",
                    color_continuous_scale="Viridis",
                    title="Usage by User"
                )
                st.plotly_chart(fig, use_container_width=True)

                # Export options
                with st.expander("📤 Export Data", expanded=False):
                    st.download_button(
                        "Download Usage Data (CSV)",
                        df.to_csv(index=False),
                        file_name=f"usage_data_{tenant_id}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

        with tab2:
            # Billing & Invoices Tab
            st.markdown("""
            <div class="section-header">
                <div class="icon">🧾</div>
                <h2>Billing Overview</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Invoice status summary
            cursor.execute("""
                SELECT 
                    i.id,
                    u.username,
                    i.invoice_date,
                    i.due_date,
                    i.total_invoiced,
                    i.is_paid,
                    COALESCE(SUM(p.amount), 0) as paid_amount
                FROM invoices i
                JOIN users u ON i.user_id = u.id
                LEFT JOIN payments p ON i.id = p.invoice_id
                WHERE i.tenant_id = %s
                GROUP BY i.id, u.username
                ORDER BY i.invoice_date DESC
                LIMIT 50
            """, (tenant_id,))
            invoices = cursor.fetchall()

            if not invoices:
                st.info("No invoices found for this tenant")
            else:
                # Create DataFrame
                inv_df = pd.DataFrame(invoices, columns=[
                    "ID", "User", "Invoice Date", "Due Date", "Total", "Paid", "Paid Amount"
                ])
                inv_df["Invoice Date"] = pd.to_datetime(inv_df["Invoice Date"])
                inv_df["Due Date"] = pd.to_datetime(inv_df["Due Date"])
                inv_df["Status"] = inv_df.apply(
                    lambda x: "Paid" if x["Paid"] else "Partial" if x["Paid Amount"] > 0 else "Unpaid",
                    axis=1
                )
                inv_df["Days Overdue"] = inv_df.apply(
                    lambda x: (datetime.now().date() - x["Due Date"].date()).days 
                    if not x["Paid"] and x["Due Date"].date() < datetime.now().date() else 0,
                    axis=1
                )

                # Invoice table with filters
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📋</div>
                    <h2>Invoice Details</h2>
                </div>
                """, unsafe_allow_html=True)
                
                status_filter = st.multiselect(
                    "Filter by Status",
                    options=["Paid", "Partial", "Unpaid"],
                    default=["Paid", "Partial", "Unpaid"],
                    key="invoice_status_filter"
                )
                
                filtered_df = inv_df[inv_df["Status"].isin(status_filter)]
                
                # Display with AgGrid for better interactivity
                st.dataframe(
                    filtered_df[["ID", "User", "Invoice Date", "Due Date", "Total", "Paid Amount", "Status", "Days Overdue"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ID": "Invoice #",
                        "Invoice Date": st.column_config.DateColumn(),
                        "Due Date": st.column_config.DateColumn(),
                        "Total": st.column_config.NumberColumn(format="R%.2f"),
                        "Paid Amount": st.column_config.NumberColumn(format="R%.2f"),
                        "Days Overdue": st.column_config.NumberColumn(
                            format="%d days",
                            help="Number of days overdue (0 if paid or not due yet)"
                        )
                    }
                )

                # Payment status visualization
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📊</div>
                    <h2>Payment Status</h2>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    # Payment status pie chart
                    status_counts = inv_df["Status"].value_counts().reset_index()
                    fig = px.pie(
                        status_counts,
                        names="Status",
                        values="count",
                        title="Invoice Status Distribution",
                        hole=0.4,
                        color="Status",
                        color_discrete_map={
                            "Paid": "#10B981",
                            "Partial": "#F59E0B",
                            "Unpaid": "#EF4444"
                        }
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Monthly revenue trend
                    monthly_rev = inv_df.groupby(
                        inv_df["Invoice Date"].dt.to_period("M").astype(str)
                    )["Total"].sum().reset_index()
                    fig = px.bar(
                        monthly_rev,
                        x="Invoice Date",
                        y="Total",
                        title="Monthly Invoice Totals",
                        color="Total",
                        color_continuous_scale="Viridis"
                    )
                    st.plotly_chart(fig, use_container_width=True)

        with tab3:
            # User Management Tab
            st.markdown("""
            <div class="section-header">
                <div class="icon">👥</div>
                <h2>User Management</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # User table
            cursor.execute("""
                SELECT 
                    id,
                    username,
                    email,
                    is_active,
                    last_login,
                    registration_date AS created_at
                FROM users
                WHERE tenant_id = %s
                ORDER BY username
            """, (tenant_id,))
            users = cursor.fetchall()
            
            if not users: 
                st.info("No users found for this tenant")
            else:
                user_df = pd.DataFrame(users, columns=[
                    "ID", "Username", "Email", "Active", "Last Login", "Created At"
                ])
                user_df["Last Login"] = pd.to_datetime(user_df["Last Login"])
                user_df["Created At"] = pd.to_datetime(user_df["Created At"])
                user_df["Days Since Login"] = (datetime.now() - user_df["Last Login"]).dt.days
                
                # Display user table
                st.dataframe(
                    user_df[["Username", "Email", "Active", "Last Login", "Days Since Login"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Active": st.column_config.CheckboxColumn(),
                        "Last Login": st.column_config.DatetimeColumn(),
                        "Days Since Login": st.column_config.NumberColumn(
                            format="%d days",
                            help="Days since last login"
                        )
                    }
                )

                # User actions
                st.markdown("""
                <div class="section-header">
                    <div class="icon">⚙️</div>
                    <h2>User Actions</h2>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    with st.expander("🔄 Reset Password", expanded=True):
                        selected_user = st.selectbox(
                            "Select User",
                            [f"{row[1]} (ID: {row[0]})" for row in users],
                            key="user_select_reset"
                        )
                        user_id = selected_user.split("(ID: ")[1][:-1]
                        
                        new_password = st.text_input("New Password", type="password", key="new_pass_input")
                        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pass_input")
                        
                        if st.button("Reset Password", type="primary", key="reset_pass_btn"):
                            if new_password != confirm_password:
                                st.error("Passwords do not match")
                            elif len(new_password) < 8:
                                st.error("Password must be at least 8 characters")
                            else:
                                cursor.execute(
                                    "UPDATE users SET password = %s WHERE id = %s",
                                    (new_password, user_id)
                                )
                                conn.commit()
                                show_toast("Password reset successfully", "success")
                
                with col2:
                    with st.expander("📊 User Usage Report", expanded=True):
                        selected_user = st.selectbox(
                            "Select User for Report",
                            [f"{row[1]} (ID: {row[0]})" for row in users],
                            key="user_select_report"
                        )
                        user_id = selected_user.split("(ID: ")[1][:-1]
                        
                        cursor.execute("""
                            SELECT 
                                usage_date,
                                metric_name,
                                usage_amount
                            FROM usage_records
                            WHERE user_id = %s
                            ORDER BY usage_date DESC
                            LIMIT 100
                        """, (user_id,))
                        user_usage = cursor.fetchall()
                        
                        if user_usage:
                            usage_df = pd.DataFrame(user_usage, columns=["Date", "Metric", "Quantity"])
                            
                            # Display metrics
                            fig = px.bar(
                                usage_df,
                                x="Date",
                                y="Quantity",
                                color="Metric",
                                title=f"Usage for {selected_user.split(' (ID:')[0]}"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No usage data found for this user")

        with tab4:
            # Alerts & Notifications Tab
            st.markdown("""
            <div class="section-header">
                <div class="icon">🚨</div>
                <h2>Alerts Dashboard</h2>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Overdue invoices
                st.markdown("""
                <div class="alert-card alert-danger">
                    <h3>❌ Overdue Invoices</h3>
                    <p>Immediate attention required for unpaid invoices.</p>
                </div>
                """, unsafe_allow_html=True)
                
                cursor.execute("""
                    SELECT 
                        i.id,
                        u.username,
                        i.due_date,
                        i.total_invoiced,
                        i.invoice_date
                    FROM invoices i
                    JOIN users u ON i.user_id = u.id
                    WHERE i.is_paid = FALSE 
                    AND i.due_date < CURRENT_DATE
                    AND u.tenant_id = %s
                    ORDER BY i.due_date ASC
                    LIMIT 5
                """, (tenant_id,))
                overdue = cursor.fetchall()
                
                if overdue:
                    for inv_id, username, due_date, amount, inv_date in overdue:
                        days_overdue = (datetime.now().date() - due_date).days
                        with st.container(border=True):
                            st.markdown(f"""
                                **Invoice #{inv_id}**  
                                **Client:** {username}  
                                **Amount Due:** {format_currency(amount)}  
                                **Due Date:** {due_date} ({days_overdue} days overdue)  
                                **Issued:** {inv_date}
                            """)
                    st.button("View All Overdue Invoices", key="view_all_overdue")
                else:
                    st.success("✅ No overdue invoices")
            
            with col2:
                # High usage alerts
                st.markdown("""
                <div class="alert-card alert-warning">
                    <h3>⚠️ High Usage Clients (>90%)</h3>
                    <p>Users approaching or exceeding plan limits.</p>
                </div>
                """, unsafe_allow_html=True)
                
                cursor.execute("""
                    SELECT 
                        u.username,
                        p.included_units,
                        COALESCE(SUM(ur.usage_amount), 0) as usage
                    FROM users u
                    JOIN subscriptions s ON u.id = s.user_id AND s.is_active
                    JOIN plans p ON s.plan_id = p.id
                    LEFT JOIN usage_records ur ON u.id = ur.user_id 
                        AND ur.usage_date BETWEEN date_trunc('month', CURRENT_DATE) AND CURRENT_DATE
                    WHERE u.tenant_id = %s
                    GROUP BY u.username, p.included_units
                    HAVING SUM(ur.usage_amount) >= 0.9 * p.included_units
                    LIMIT 5
                """, (tenant_id,))
                high_usage = cursor.fetchall()
                
                if high_usage:
                    for username, limit, usage in high_usage:
                        pct = (usage / limit) * 100
                        with st.container(border=True):
                            st.markdown(f"""
                                **Client:** {username}  
                                **Usage:** {usage:,.0f} of {limit:,.0f} units ({pct:.0f}%)  
                                **Overage:** {max(0, usage - limit):,.0f} units
                            """)
                    st.button("View All High Usage Clients", key="view_all_high_usage")
                else:
                    st.success("✅ No high usage clients")
            
            # Inactive users section
            st.markdown("""
            <div class="alert-card alert-info">
                <h3>💤 Inactive Users</h3>
                <p>Users with no recent activity (30+ days).</p>
            </div>
            """, unsafe_allow_html=True)
            
            cursor.execute("""
                SELECT u.username, MAX(ur.usage_date) as last_usage
                FROM users u
                LEFT JOIN usage_records ur ON u.id = ur.user_id
                WHERE u.tenant_id = %s
                GROUP BY u.username
                HAVING MAX(ur.usage_date) IS NULL OR MAX(ur.usage_date) < CURRENT_DATE - INTERVAL '30 days'
                LIMIT 10
            """, (tenant_id,))
            inactive = cursor.fetchall()
            
            if inactive:
                for username, last_usage in inactive:
                    with st.container(border=True):
                        if last_usage:
                            days_inactive = (datetime.now().date() - last_usage).days
                            st.markdown(f"""
                                **Client:** {username}  
                                **Last Activity:** {last_usage} ({days_inactive} days ago)
                            """)
                        else:
                            st.markdown(f"""
                                **Client:** {username}  
                                **Last Activity:** Never
                            """)
                st.button("View All Inactive Users", key="view_all_inactive")
            else:
                st.success("✅ All users have recent activity")

        conn.close()

if __name__ == "__main__":
    admin_dashboard()