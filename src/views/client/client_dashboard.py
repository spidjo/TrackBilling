# src/views/client/client_dashboard.py
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from db.database import get_db_connection
from utils.session import init_session_state
from utils.ui_helpers import loading_spinner, show_toast
from billing_engine import get_invoice_summary, generate_invoice_pdf
from io import BytesIO
import base64

def client_dashboard():
    """Optimized client dashboard with improved UX and performance"""
    init_session_state()

    if not st.session_state.get("authenticated"):
        st.warning("🔒 Please log in to view your dashboard")
        st.stop()

    # Initialize session variables
    user_id = st.session_state.username
    tenant_id = st.session_state.tenant_id
    
    # Page config for better mobile experience
    st.set_page_config(layout="wide", page_title="Client Dashboard", page_icon="📊")

    # Custom CSS for better UI
    st.markdown("""
        <style>
            .dashboard-card {
                border-radius: 10px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                background-color: #f9f9f9;
            }
            .metric-card {
                border-left: 4px solid #4e79a7;
                padding: 1rem;
                margin-bottom: 1rem;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 10px;
            }
            .stTabs [data-baseweb="tab"] {
                padding: 8px 16px;
                border-radius: 4px 4px 0 0;
            }
            .stDataFrame {
                font-size: 0.9rem;
            }
        </style>
    """, unsafe_allow_html=True)

    # Get user data with loading state
    with loading_spinner("Loading your dashboard..."):
        plan_data = get_current_plan(user_id)
        client_info = get_client_info(user_id)
        tenant_info = get_tenant_info(tenant_id)

    # Dashboard header with user info
    st.title(f"📊 Welcome, {client_info.get('name', 'Client')}")
    
    # Create tabbed interface
    tabs = st.tabs(["📊 Overview", "📈 Usage Analytics", "🧾 Invoices", "🔔 Alerts"])

    # --- Overview Tab ---
    with tabs[0]:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Your Current Plan")
            if not plan_data:
                st.warning("You are not subscribed to a plan")
            else:
                with st.container(border=True):
                    st.markdown(f"### {plan_data['name']}")
                    st.markdown(f"**Monthly Fee:** R{plan_data['monthly_fee']:.2f}")
                    st.markdown(f"**Included Units:** {plan_data['included_units']}")
                    st.markdown(f"**Overage Rate:** R{plan_data['overage_rate']:.2f}/unit")
                    st.markdown(f"**Start Date:** {plan_data['start_date'].strftime('%Y-%m-%d')}")
                    st.button("Upgrade Plan", use_container_width=True)

        with col2:
            st.subheader("Usage Summary")
            with st.container(border=True):
                if plan_data:
                    usage = get_current_usage(user_id, tenant_id)
                    usage_pct = (usage / plan_data['included_units']) * 100 if plan_data['included_units'] > 0 else 0
                    
                    st.metric("Units Used", f"{usage}/{plan_data['included_units']}", 
                             f"{usage_pct:.1f}% of limit")
                    
                    # Progress bar
                    st.progress(min(usage_pct/100, 1))
                    
                    if usage_pct > 90:
                        st.warning("You're approaching your usage limit")
                    elif usage_pct > 100:
                        st.error("You've exceeded your usage limit")
                else:
                    st.info("No active plan to track usage")

    # --- Usage Analytics Tab ---
    with tabs[1]:
        st.subheader("Usage Analytics")
        
        with st.expander("🔍 Filter Options", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                date_range = st.date_input("Date Range", [], key="usage_date_range")
            with col2:
                metric_filter = st.text_input("Filter by Metric", "")
        
        with loading_spinner("Loading usage data..."):
            usage_data = get_usage_data(user_id, tenant_id, date_range, metric_filter)
        
        if usage_data.empty:
            st.info("No usage data found for selected filters")
        else:
            # Usage Heatmap
            st.subheader("Usage Heatmap")
            heatmap = create_heatmap(usage_data)
            st.altair_chart(heatmap, use_container_width=True)
            
            # Monthly Trends
            st.subheader("Monthly Trends")
            trend_chart = create_trend_chart(usage_data)
            st.altair_chart(trend_chart, use_container_width=True)
            
            # Data Export
            st.download_button(
                label="📥 Export Usage Data (CSV)",
                data=usage_data.to_csv(index=False),
                file_name=f"usage_data_{datetime.now().date()}.csv",
                mime="text/csv"
            )

    # --- Invoices Tab ---
    with tabs[2]:
        st.subheader("Invoice Management")
        
        # Latest Invoice
        with st.expander("Latest Invoice", expanded=True):
            latest_invoice = get_latest_invoice(user_id)
            if latest_invoice:
                display_invoice(latest_invoice, tenant_info, client_info)
            else:
                st.info("No invoices available")
        
        # Invoice History
        with st.expander("Invoice History", expanded=True):
            invoice_history = get_invoice_history(user_id)
            if not invoice_history.empty:
                st.dataframe(
                    invoice_history,
                    column_config={
                        "total_amount": st.column_config.NumberColumn("Amount", format="R%.2f"),
                        "is_paid": st.column_config.CheckboxColumn("Paid")
                    },
                    use_container_width=True
                )
                
                # PDF Preview
                selected_invoice = st.selectbox(
                    "Select invoice to preview",
                    invoice_history["id"],
                    format_func=lambda x: f"Invoice #{x}"
                )
                
                if selected_invoice:
                    with loading_spinner("Generating invoice preview..."):
                        display_invoice_preview(selected_invoice, tenant_info, client_info)
            else:
                st.info("No invoice history available")

    # --- Alerts Tab ---
    with tabs[3]:
        st.subheader("Notifications & Alerts")
        
        # Overdue Invoices
        with st.container(border=True):
            st.markdown("### Overdue Invoices")
            overdue = get_overdue_invoices(user_id)
            if overdue:
                for inv in overdue:
                    st.error(f"Invoice #{inv['id']} overdue since {inv['due_date']} - Amount: R{inv['total_amount']:.2f}")
            else:
                st.success("✅ No overdue invoices")
        
        # Usage Alerts
        with st.container(border=True):
            st.markdown("### Usage Alerts")
            if plan_data:
                usage = get_current_usage(user_id, tenant_id)
                usage_pct = (usage / plan_data['included_units']) * 100
                
                if usage_pct >= 100:
                    st.error(f"⚠️ You have exceeded your usage limit! ({usage} units used)")
                elif usage_pct >= 80:
                    st.warning(f"⏳ Approaching limit: {usage_pct:.1f}% of monthly units used")
                else:
                    st.info(f"📊 Current usage: {usage} units ({usage_pct:.1f}% of limit)")
            else:
                st.info("No active plan to monitor usage")

# --------------------------
# Data Fetching Functions
# --------------------------

def get_current_plan(user_id: str) -> dict:
    """Get the user's current subscription plan"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.name, p.description, p.monthly_fee, p.included_units, p.overage_rate, s.start_date
                FROM subscriptions s
                JOIN plans p ON s.plan_id = p.id
                WHERE s.user_id = %s AND s.is_active
                ORDER BY s.start_date DESC LIMIT 1
            """, (get_user_id(user_id),))
            plan = cursor.fetchone()
            
            if plan:
                return {
                    "name": plan[0],
                    "description": plan[1],
                    "monthly_fee": float(plan[2]),
                    "included_units": plan[3],
                    "overage_rate": float(plan[4]),
                    "start_date": plan[5]
                }
            return {}
    finally:
        conn.close()

def get_current_usage(user_id: str, tenant_id: int) -> float:
    """Get current month's usage total"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            today = datetime.now()
            first_day = today.replace(day=1).date().isoformat()
            last_day = today.date().isoformat()
            
            cursor.execute("""
                SELECT COALESCE(SUM(usage_amount), 0)
                FROM usage_records
                WHERE user_id = %s AND tenant_id = %s 
                AND usage_date BETWEEN %s AND %s
            """, (get_user_id(user_id), tenant_id, first_day, last_day))
            return float(cursor.fetchone()[0])
    finally:
        conn.close()

def get_usage_data(user_id: str, tenant_id: int, date_range: list, metric_filter: str = "") -> pd.DataFrame:
    """Get filtered usage data as DataFrame"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT usage_date, metric_name, usage_amount
                FROM usage_records
                WHERE user_id = %s AND tenant_id = %s
            """
            params = [get_user_id(user_id), tenant_id]

            if metric_filter:
                query += " AND metric_name ILIKE %s"
                params.append(f"%{metric_filter}%")

            if len(date_range) == 2:
                query += " AND usage_date BETWEEN %s AND %s"
                params.extend([date_range[0], date_range[1]])

            cursor.execute(query, params)
            data = cursor.fetchall()
            
            if data:
                df = pd.DataFrame(data, columns=["date", "metric", "amount"])
                df["date"] = pd.to_datetime(df["date"])
                df["month"] = df["date"].dt.to_period("M").astype(str)
                return df
            return pd.DataFrame()
    finally:
        conn.close()

def get_latest_invoice(user_id: str) -> dict:
    """Get the user's most recent invoice"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM invoices
                WHERE user_id = %s 
                ORDER BY invoice_date DESC LIMIT 1
            """, (get_user_id(user_id),))
            row = cursor.fetchone()
            if row:
                invoice, _ = get_invoice_summary(row[0])
                return invoice
            return {}
    finally:
        conn.close()

def get_invoice_history(user_id: str) -> pd.DataFrame:
    """Get all user invoices as DataFrame"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, invoice_date, period_start, period_end, total_amount, is_paid
                FROM invoices
                WHERE user_id = %s
                ORDER BY invoice_date DESC
            """, (get_user_id(user_id),))
            
            data = cursor.fetchall()
            if data:
                df = pd.DataFrame(data, columns=["id", "date", "period_start", "period_end", "total_amount", "is_paid"])
                df["date"] = pd.to_datetime(df["date"])
                return df
            return pd.DataFrame()
    finally:
        conn.close()

def get_overdue_invoices(user_id: str) -> list:
    """Get list of overdue invoices"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, invoice_date, due_date, total_amount
                FROM invoices
                WHERE user_id = %s AND NOT is_paid AND due_date < CURRENT_DATE
                ORDER BY due_date ASC
            """, (get_user_id(user_id),))
            
            return [dict(zip(["id", "invoice_date", "due_date", "total_amount"], row)) 
                   for row in cursor.fetchall()]
    finally:
        conn.close()

# --------------------------
# Display Functions
# --------------------------

def display_invoice(invoice: dict, tenant_info: dict, client_info: dict):
    """Display invoice summary with download option"""
    if not invoice:
        return
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Invoice #** `{invoice['id']}`")
        st.markdown(f"**Period:** `{invoice['period_start']}` to `{invoice['period_end']}`")
        st.markdown(f"**Amount Due:** R{invoice['total_amount']:.2f}")
        st.markdown(f"**Status:** {'✅ Paid' if invoice['is_paid'] else '❌ Unpaid'}")
    
    with col2:
        with loading_spinner("Generating PDF..."):
            pdf_bytes = generate_invoice_pdf(
                invoice, 
                get_invoice_summary(invoice['id'])[1],
                tenant_info,
                client_info
            )
        
        st.download_button(
            label="Download PDF",
            data=pdf_bytes.getvalue(),
            file_name=f"invoice_{invoice['id']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

def display_invoice_preview(invoice_id: int, tenant_info: dict, client_info: dict):
    """Display interactive invoice preview"""
    invoice, items = get_invoice_summary(invoice_id)
    if not invoice:
        return
    
    pdf_bytes = generate_invoice_pdf(invoice, items, tenant_info, client_info)
    b64 = base64.b64encode(pdf_bytes.getvalue()).decode('utf-8')
    
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600px"></iframe>',
        unsafe_allow_html=True
    )

def create_heatmap(usage_data: pd.DataFrame) -> alt.Chart:
    """Create a usage heatmap visualization"""
    heatmap_data = usage_data.groupby(["date", "metric"])["amount"].sum().reset_index()
    return alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X('date:T', title="Date"),
        y=alt.Y('metric:N', title="Metric"),
        color=alt.Color('amount:Q', scale=alt.Scale(scheme='blues'), title="Usage"),
        tooltip=['date', 'metric', 'amount']
    ).properties(height=300)

def create_trend_chart(usage_data: pd.DataFrame) -> alt.Chart:
    """Create a monthly usage trend visualization"""
    monthly_usage = usage_data.groupby(["month", "metric"])["amount"].sum().reset_index()
    return alt.Chart(monthly_usage).mark_line(point=True).encode(
        x='month:T',
        y='amount:Q',
        color='metric:N',
        tooltip=["month", "metric", "amount"]
    ).properties(height=300)

# --------------------------
# Helper Functions
# --------------------------

def get_user_id(username: str) -> int:
    """Get user ID from username"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            return result[0] if result else None
    finally:
        conn.close()

def get_client_info(user_id: str) -> dict:
    """Get client information"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT first_name || ' ' || last_name, company_name, email
                FROM users WHERE id = %s
            """, (get_user_id(user_id),))
            row = cursor.fetchone()
            return {
                "name": row[0] if row else "",
                "address": row[1] if row else "",
                "email": row[2] if row else ""
            }
    finally:
        conn.close()

def get_tenant_info(tenant_id: int) -> dict:
    """Get tenant information"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT name, address, email, phone FROM tenants WHERE id = %s
            """, (tenant_id,))
            row = cursor.fetchone()
            return {
                "name": row[0] if row else "",
                "address": row[1] if row else "",
                "email": row[2] if row else "",
                "phone": row[3] if row else ""
            }
    finally:
        conn.close()