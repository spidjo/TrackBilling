# src/views/client/client_dashboard.py
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db.database import get_db_connection
from utils.session import init_session_state, validate_session
from utils.ui_helpers import loading_spinner, show_toast
from billing_engine import BillingEngine
from utils.pdf_utils import PDFGenerationError, generate_invoice_pdf
from utils.pdf_generator import generate_pdf_invoice
from io import BytesIO
import base64
from typing import Tuple, Optional, List

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
    
    .plan-card {
        border-radius: 12px;
        padding: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-left: 4px solid var(--primary);
    }
</style>
""", unsafe_allow_html=True)

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"

def client_dashboard():
    """Enhanced Client Dashboard with professional UX"""
    init_session_state()
    
    # Session validation with redirect
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()

    # Page config for better mobile experience
    st.set_page_config(layout="wide", page_title="Client Dashboard", page_icon="📊")
    
    # Direct session user_id storage
    user_id = st.session_state.user_id  # Now stored directly in session
    tenant_id = st.session_state.tenant_id

    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">📊 Client Dashboard</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            <button style="background-color: #4F46E5; color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; cursor: pointer;" onclick="window.location.reload()">Refresh Data</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # Get user data with loading state and error handling
    try:
        with loading_spinner("Loading your dashboard..."):
            plan_data = get_current_plan(user_id)
            client_info = get_client_info(user_id)
            tenant_info = get_tenant_info(tenant_id)
    except Exception as e:
        show_toast(f"Failed to load dashboard data: {str(e)}", "error")
        st.error("Failed to load dashboard data. Please try again later.")
        st.stop()

    # Create tabbed interface
    tabs = st.tabs(["📊 Overview", "📈 Usage Analytics", "🧾 Invoices", "🔔 Alerts"])

    # --- Overview Tab ---
    with tabs[0]:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="section-header">
                <div class="icon">📋</div>
                <h2>Your Current Plan</h2>
            </div>
            """, unsafe_allow_html=True)
            
            if not plan_data:
                st.markdown("""
                <div class="alert-card alert-info">
                    <h3>No Active Plan</h3>
                    <p>You are not currently subscribed to a plan.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="plan-card">
                    <h3 style="color: #4F46E5; margin-top: 0;">{plan_data['name']}</h3>
                    <p><strong>Monthly Fee:</strong> {format_currency(plan_data['monthly_fee'])}</p>
                    <p><strong>Included Units:</strong> {plan_data['included_units']:,}</p>
                    <p><strong>Overage Rate:</strong> {format_currency(plan_data['overage_rate'])}/unit</p>
                    <p><strong>Start Date:</strong> {plan_data['start_date'].strftime('%Y-%m-%d')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # if st.button("Manage Subscription", use_container_width=True, key="manage_subscription"):
                #     st.switch_page("pages/my_subscriptions.py")

        with col2:
            st.markdown("""
            <div class="section-header">
                <div class="icon">📊</div>
                <h2>Usage Summary</h2>
            </div>
            """, unsafe_allow_html=True)
            
            if plan_data:
                try:
                    usage = get_current_usage(user_id, tenant_id)
                    usage_pct = (usage / plan_data['included_units']) * 100 if plan_data['included_units'] > 0 else 0
                    
                    # Determine card style based on usage
                    if usage_pct >= 100:
                        card_style = "metric-negative"
                    elif usage_pct >= 80:
                        card_style = "metric-warning"
                    else:
                        card_style = "metric-positive"
                    
                    st.markdown(f"""
                    <div class="metric-card {card_style}">
                        <h3>Units Used</h3>
                        <h2>{usage:,.0f}/{plan_data['included_units']:,}</h2>
                        <div style="margin-top: 0.5rem;">
                            <span style="color: {'#EF4444' if usage_pct >= 100 else '#F59E0B' if usage_pct >= 80 else '#10B981'};">{usage_pct:.1f}% of limit</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Progress bar
                    st.progress(min(usage_pct/100, 1), text=f"{usage_pct:.1f}% of monthly limit")
                    
                    if usage_pct > 90:
                        st.markdown("""
                        <div class="alert-card alert-warning">
                            <h3>⚠️ Approaching Limit</h3>
                            <p>You're approaching your usage limit. Consider upgrading your plan.</p>
                        </div>
                        """, unsafe_allow_html=True)
                    elif usage_pct > 100:
                        st.markdown("""
                        <div class="alert-card alert-danger">
                            <h3>❌ Limit Exceeded</h3>
                            <p>You've exceeded your usage limit. Overage charges may apply.</p>
                        </div>
                        """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Failed to load usage data: {str(e)}")
            else:
                st.markdown("""
                <div class="alert-card alert-info">
                    <h3>No Usage Data</h3>
                    <p>No active plan to track usage.</p>
                </div>
                """, unsafe_allow_html=True)

    # --- Usage Analytics Tab ---
    with tabs[1]:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📈</div>
            <h2>Usage Analytics</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("🔍 Filter Options", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                # Default to recent 30-day window if empty
                default_end = datetime.now().date()
                default_start = default_end - timedelta(days=30)
                date_range = st.date_input(
                    "Date Range",
                    [default_start, default_end],
                    key="usage_date_range"
                )
                
                # Validate date range has exactly two dates
                if len(date_range) != 2:
                    st.warning("Please select a start and end date")
                    st.stop()
                
                # Add option to view prior months
                months_to_show = st.slider(
                    "Months to include",
                    1, 12, 3,
                    help="Select how many months of historical data to include"
                )
                
            with col2:
                # Dropdown of available metrics
                available_metrics = get_available_metrics(user_id, tenant_id)
                metric_filter = st.multiselect(
                    "Filter by Metric",
                    options=available_metrics,
                    default=available_metrics[:3] if len(available_metrics) > 3 else available_metrics,
                    help="Select metrics to analyze"
                )
        
        try:
            with loading_spinner("Loading usage data..."):
                usage_data = get_usage_data(user_id, tenant_id, date_range, metric_filter)
            
            if usage_data.empty:
                st.info("No usage data found for selected filters")
            else:
                # Monthly Trends with Plotly
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📊</div>
                    <h2>Monthly Trends</h2>
                </div>
                """, unsafe_allow_html=True)
                
                monthly_usage = usage_data.groupby(["month", "metric"])["amount"].sum().reset_index()
                fig = px.line(
                    monthly_usage,
                    x="month",
                    y="amount",
                    color="metric",
                    title="Monthly Usage Trends",
                    template="plotly_white",
                    line_shape="spline"
                )
                fig.update_layout(
                    hovermode="x unified",
                    xaxis_title="Month",
                    yaxis_title="Usage Quantity",
                    legend_title="Metric"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Usage Heatmap
                st.markdown("""
                <div class="section-header">
                    <div class="icon">🔥</div>
                    <h2>Usage Heatmap</h2>
                </div>
                """, unsafe_allow_html=True)
                
                heatmap_data = usage_data.groupby(["date", "metric"])["amount"].sum().reset_index()
                fig = px.density_heatmap(
                    heatmap_data,
                    x="date",
                    y="metric",
                    z="amount",
                    title="Usage Distribution",
                    color_continuous_scale="Viridis"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Data Export
                with st.expander("📤 Export Data", expanded=False):
                    st.download_button(
                        label="Download Usage Data (CSV)",
                        data=usage_data.to_csv(index=False),
                        file_name=f"usage_data_{datetime.now().date()}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
        except Exception as e:
            st.error(f"Failed to load usage analytics: {str(e)}")

    # --- Invoices Tab ---
    with tabs[2]:
        st.markdown("""
        <div class="section-header">
            <div class="icon">🧾</div>
            <h2>Invoice Management</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Latest Invoice
        with st.expander("Latest Invoice", expanded=True):
            try:
                latest_invoice = get_latest_invoice(user_id)
                if latest_invoice:
                    display_invoice(latest_invoice, tenant_info, client_info)
                else:
                    st.info("No invoices available")
            except Exception as e:
                st.error(f"Failed to load latest invoice: {str(e)}")
        
        # Invoice History
        with st.expander("Invoice History", expanded=True):
            try:
                invoice_history = get_invoice_history(user_id)
                if not invoice_history.empty:
                    # Add sorting functionality
                    sort_column = st.selectbox(
                        "Sort by",
                        ["date", "total_invoiced", "is_paid"],
                        format_func=lambda x: x.replace("_", " ").title()
                    )
                    ascending = st.checkbox("Ascending order", True)
                    
                    invoice_history = invoice_history.sort_values(
                        by=sort_column,
                        ascending=ascending
                    )
                    
                    # Display with styled dataframe
                    st.dataframe(
                        invoice_history,
                        column_config={
                            "id": "Invoice #",
                            "date": st.column_config.DateColumn("Invoice Date"),
                            "period_start": st.column_config.DateColumn("Period Start"),
                            "period_end": st.column_config.DateColumn("Period End"),
                            "total_invoiced": st.column_config.NumberColumn("Amount", format="R%.2f"),
                            "is_paid": st.column_config.CheckboxColumn("Paid")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # PDF Preview
                    st.markdown("""
                    <div class="section-header">
                        <div class="icon">👁️</div>
                        <h2>Invoice Preview</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    selected_invoice = st.selectbox(
                        "Select invoice to preview",
                        invoice_history["id"],
                        format_func=lambda x: f"Invoice #{x} - {format_currency(invoice_history[invoice_history['id'] == x]['total_invoiced'].iloc[0])}"
                    )
                    
                    if selected_invoice:
                        try:
                            with loading_spinner("Generating invoice preview..."):
                                display_invoice_preview(selected_invoice, tenant_info, client_info)
                        except Exception as e:
                            st.error(f"Failed to generate preview: {str(e)}")
                else:
                    st.info("No invoice history available")
            except Exception as e:
                st.error(f"Failed to load invoice history: {str(e)}")

    # --- Alerts Tab ---
    with tabs[3]:
        st.markdown("""
        <div class="section-header">
            <div class="icon">🔔</div>
            <h2>Notifications & Alerts</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Overdue Invoices
        st.markdown("""
        <div class="alert-card alert-danger">
            <h3>❌ Overdue Invoices</h3>
            <p>Immediate attention required for unpaid invoices.</p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            overdue = get_overdue_invoices(user_id)
            if overdue:
                # Add sorting and filtering options
                sort_by = st.selectbox(
                    "Sort overdue invoices by",
                    ["due_date", "total_invoiced"],
                    key="overdue_sort"
                )
                reverse_sort = st.checkbox("Show oldest first", True, key="overdue_order")
                
                overdue = sorted(
                    overdue,
                    key=lambda x: x[sort_by],
                    reverse=not reverse_sort
                )
                
                for inv in overdue:
                    with st.container(border=True):
                        days_overdue = (datetime.now().date() - inv['due_date']).days
                        st.markdown(f"""
                            **Invoice #{inv['id']}**  
                            **Amount Due:** {format_currency(inv['total_invoiced'])}  
                            **Due Date:** {inv['due_date']} ({days_overdue} days overdue)  
                        """)
                        if st.button(f"Pay Invoice #{inv['id']}", key=f"pay_{inv['id']}"):
                            st.switch_page("pages/pay_invoice.py")
            else:
                st.success("✅ No overdue invoices")
        except Exception as e:
            st.error(f"Failed to load overdue invoices: {str(e)}")
        
        # Usage Alerts
        st.markdown("""
        <div class="alert-card alert-warning">
            <h3>⚠️ Usage Alerts</h3>
            <p>Monitor your usage to avoid overage charges.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if plan_data:
            try:
                usage = get_current_usage(user_id, tenant_id)
                usage_pct = (usage / plan_data['included_units']) * 100
                
                if usage_pct >= 100:
                    st.markdown(f"""
                    <div class="alert-card alert-danger">
                        <h3>❌ Usage Limit Exceeded</h3>
                        <p>You have exceeded your usage limit! ({usage} units used)</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif usage_pct >= 80:
                    st.markdown(f"""
                    <div class="alert-card alert-warning">
                        <h3>⚠️ Approaching Limit</h3>
                        <p>You're approaching your usage limit: {usage_pct:.1f}% of monthly units used</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="alert-card alert-info">
                        <h3>📊 Current Usage</h3>
                        <p>{usage} units ({usage_pct:.1f}% of limit)</p>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Failed to load usage alerts: {str(e)}")
        else:
            st.info("No active plan to monitor usage")

# --------------------------
# Enhanced Data Fetching Functions
# --------------------------

def get_current_plan(user_id: int) -> dict:
    """Get the user's current subscription plan with error handling"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.name, p.description, p.monthly_fee, p.included_units, p.overage_rate, s.start_date
                FROM subscriptions s
                JOIN plans p ON s.plan_id = p.id
                WHERE s.user_id = %s AND s.is_active
                ORDER BY s.start_date DESC LIMIT 1
            """, (user_id,))
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
    except Exception as e:
        st.error(f"Error fetching current plan: {str(e)}")
        return {}
    finally:
        if conn:
            conn.close()

def get_current_usage(user_id: int, tenant_id: int) -> float:
    """Get current month's usage total with error handling"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            today = datetime.now()
            first_day = today.replace(day=1).date().isoformat()
            last_day = today.date().isoformat()
            
            cursor.execute("""
                SELECT COALESCE(SUM(usage_amount), 0)
                FROM usage_records
                WHERE user_id = %s AND tenant_id = %s 
                AND usage_date BETWEEN %s AND %s
            """, (user_id, tenant_id, first_day, last_day))
            return float(cursor.fetchone()[0])
    except Exception as e:
        st.error(f"Error fetching current usage: {str(e)}")
        return 0.0
    finally:
        if conn:
            conn.close()

def get_usage_data(user_id: int, tenant_id: int, date_range: List[datetime], metric_filter: List[str] = None) -> pd.DataFrame:
    """Get filtered usage data as DataFrame with enhanced error handling"""
    if metric_filter is None:
        metric_filter = []
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            query = """
                SELECT usage_date, metric_name, usage_amount
                FROM usage_records
                WHERE user_id = %s AND tenant_id = %s
            """
            params = [user_id, tenant_id]

            if metric_filter:
                query += " AND metric_name = ANY(%s)"
                params.append(metric_filter)

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
    except Exception as e:
        st.error(f"Error fetching usage data: {str(e)}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def get_available_metrics(user_id: int, tenant_id: int) -> List[str]:
    """Get list of available metrics for the user"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT metric_name 
                FROM usage_records
                WHERE user_id = %s AND tenant_id = %s
                ORDER BY metric_name
            """, (user_id, tenant_id))
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error fetching available metrics: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def get_latest_invoice(user_id: int) -> dict:
    """Get the user's most recent invoice with BillingEngine error handling"""
    conn = None
    try:
        billing_engine = BillingEngine()
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM invoices
                WHERE user_id = %s 
                ORDER BY invoice_date DESC LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            if row:
                invoice, _ = billing_engine.get_invoice_summary(row[0])
                return invoice
            return {}
    except Exception as e:
        st.error(f"Error fetching latest invoice: {str(e)}")
        return {}
    finally:
        if conn:
            conn.close()

def get_invoice_history(user_id: int) -> pd.DataFrame:
    """Get all user invoices as DataFrame with error handling"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, invoice_date, period_start, period_end, total_invoiced, is_paid
                FROM invoices
                WHERE user_id = %s
                ORDER BY invoice_date DESC
            """, (user_id,))
            
            data = cursor.fetchall()
            if data:
                df = pd.DataFrame(data, columns=["id", "date", "period_start", "period_end", "total_invoiced", "is_paid"])
                df["date"] = pd.to_datetime(df["date"])
                return df
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching invoice history: {str(e)}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def get_overdue_invoices(user_id: int) -> List[dict]:
    """Get list of overdue invoices with error handling"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, invoice_date, due_date, total_invoiced
                FROM invoices
                WHERE user_id = %s AND NOT is_paid AND due_date < CURRENT_DATE
                ORDER BY due_date ASC
            """, (user_id,))

            return [dict(zip(["id", "invoice_date", "due_date", "total_invoiced"], row))
                   for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error fetching overdue invoices: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

# --------------------------
# Enhanced Display Functions
# --------------------------

def display_invoice(invoice: dict, tenant_info: dict, client_info: dict):
    """Display invoice summary with download option and error handling"""
    if not invoice:
        return

    try:
        billing_engine = BillingEngine()
        invoice_details = billing_engine.get_invoice_details(invoice['id'])
        
        tenant_id = st.session_state.tenant_id
        if not invoice_details:
            st.error("Failed to load invoice details")
            return
            
        pdf_bytes = generate_pdf_invoice(
            invoice_details=invoice_details,
            tenant_id=tenant_id
        )
        
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=f"invoice_{invoice['id']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
    except PDFGenerationError as e:
        st.error(f"Failed to generate invoice PDF: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error displaying invoice: {str(e)}")
        
def display_invoice_preview(invoice_id: int, tenant_info: dict, client_info: dict):
    """Display interactive invoice preview with error handling"""
    tenant_id = st.session_state.tenant_id
    print(f"tenant id: {tenant_id}")
    try:
        billing_engine = BillingEngine()
        invoice_details = billing_engine.get_invoice_details(invoice_id)
        if not invoice_details:
            st.error("Invoice not found")
            return
            
        pdf_bytes = generate_pdf_invoice(invoice_details=invoice_details, tenant_id=tenant_id)
        b64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600px"></iframe>',
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"Error generating invoice preview: {str(e)}")

# --------------------------
# Enhanced Helper Functions
# --------------------------

def get_client_info(user_id: int) -> dict:
    """Get client information with error handling"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT first_name || ' ' || last_name, company_name, email
                FROM users WHERE id = %s
            """, (user_id,))
            row = cursor.fetchone()
            return {
                "name": row[0] if row else "",
                "address": row[1] if row else "",
                "email": row[2] if row else ""
            }
    except Exception as e:
        st.error(f"Error fetching client info: {str(e)}")
        return {
            "name": "",
            "address": "",
            "email": ""
        }
    finally:
        if conn:
            conn.close()

def get_tenant_info(tenant_id: int) -> dict:
    """Get tenant information with error handling"""
    conn = None
    try:
        conn = get_db_connection()
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
    except Exception as e:
        st.error(f"Error fetching tenant info: {str(e)}")
        return {
            "name": "",
            "address": "",
            "email": "",
            "phone": ""
        }
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    client_dashboard()