# src/views/client_usage_dashboard.py
import streamlit as st
import logging
from datetime import datetime, timedelta
import pandas as pd
import time
import plotly.express as px
from utils.session_guard import require_login
from db.database import get_db_connection  
from utils.ui_helpers import loading_spinner, show_toast, display_empty_state
from billing_engine import BillingEngine 
from utils.pdf_utils import generate_invoice_pdf
from utils.validation import validate_user_session, validate_db_connection
from typing import Optional, Tuple, List, Dict

# Constants
MAX_RETRIES = 3
DEFAULT_PLAN_NAME = "Free Plan"
DEFAULT_PLAN_DESC = "Basic access with limited features"

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

def client_usage_dashboard():
    """Client-facing usage dashboard with professional UX similar to admin dashboard"""
    try:
        # Page configuration with error handling
        try:
            st.set_page_config(
                page_title="Usage Dashboard", 
                layout="wide",
                page_icon="📊"
            )
        except st.errors.StreamlitAPIException:
            # Handle case where page config is already set
            pass

        # Secure access with session validation
        if not require_login("client"):
            st.error("🔒 Please log in to access this page.")
            st.stop()

        if not validate_user_session():
            st.error("Invalid session. Please log in again.")
            st.stop()

        # Initialize session state with defaults
        st.session_state.setdefault('refresh_data', False)
        st.session_state.setdefault('confirm_invoice', False)

        # Dashboard header with professional styling
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
            <h1 style="margin: 0; color: #1F2937;">📊 My Usage Dashboard</h1>
            <div style="margin-left: auto; display: flex; align-items: center;">
                <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
                <button style="background-color: #4F46E5; color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; cursor: pointer;" onclick="window.location.reload()">Refresh Data</button>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # Main dashboard content
        display_dashboard_content()

    except Exception as e:
        handle_dashboard_error(e)

def display_dashboard_content():
    """Display all dashboard components with proper error handling"""
    # Initialize billing engine with retry logic
    billing_engine = initialize_billing_engine()
    if not billing_engine:
        return

    # Get database connection with validation
    conn = get_db_connection_with_retry()
    if not conn:
        return

    try:
        with conn:
            with conn.cursor() as cursor:
                # Get user and tenant info with validation
                user_info = get_validated_user_info(cursor)
                if not user_info:
                    return

                db_user_id, tenant_id = user_info

                # Display summary metrics
                display_summary_metrics(cursor, db_user_id, tenant_id)
                
                st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

                # Tabs layout for better organization
                tab1, tab2, tab3 = st.tabs([
                    "📊 Usage Analytics", 
                    "🧾 Billing & Invoices", 
                    "📄 Current Period"
                ])

                with tab1:
                    # Display subscription info
                    display_subscription_info(cursor, db_user_id)

                    # Display usage metrics
                    display_usage_metrics(cursor, db_user_id)

                with tab2:
                    # Display invoice history
                    display_invoice_history(cursor, db_user_id)

                with tab3:
                    # Display current period estimate
                    display_current_period_estimate(billing_engine, cursor, db_user_id, tenant_id)

    except Exception as e:
        st.error(f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

def display_summary_metrics(cursor, db_user_id: int, tenant_id: str):
    """Display summary metrics cards similar to admin dashboard"""
    try:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Current plan
            cursor.execute("""
                SELECT p.name FROM subscriptions s
                JOIN plans p ON s.plan_id = p.id
                WHERE s.user_id = %s AND s.is_active
                ORDER BY s.start_date DESC LIMIT 1
            """, (db_user_id,))
            plan = cursor.fetchone()
            plan_name = plan[0] if plan else "No active plan"
            
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Current Plan</h3>
                <h2>{plan_name}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Monthly usage total
            current_month = datetime.utcnow().strftime('%Y-%m')
            cursor.execute("""
                SELECT COALESCE(SUM(ur.usage_amount), 0)
                FROM usage_records ur
                JOIN usage_metrics um ON ur.metric_id = um.id
                WHERE ur.user_id = %s AND TO_CHAR(ur.usage_date, 'YYYY-MM') = %s
            """, (db_user_id, current_month))
            monthly_usage = cursor.fetchone()[0]
            
            st.markdown(f"""
            <div class="metric-card metric-{'warning' if monthly_usage > 0 else 'neutral'}">
                <h3>Monthly Usage</h3>
                <h2>{monthly_usage:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # Outstanding balance
            cursor.execute("""
                SELECT COALESCE(SUM(total_invoiced - COALESCE((
                    SELECT SUM(amount) FROM payments WHERE invoice_id = i.id
                ), 0)), 0)
                FROM invoices i
                WHERE i.user_id = %s AND payment_status != 'paid'
            """, (db_user_id,))
            outstanding = cursor.fetchone()[0]
            
            st.markdown(f"""
            <div class="metric-card metric-{'danger' if outstanding > 0 else 'success'}">
                <h3>Outstanding Balance</h3>
                <h2>{format_currency(outstanding)}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            # Overdue invoices
            cursor.execute("""
                SELECT COUNT(*) FROM invoices 
                WHERE user_id = %s 
                AND due_date < CURRENT_DATE 
                AND payment_status != 'paid'
            """, (db_user_id,))
            overdue_invoices = cursor.fetchone()[0]
            
            st.markdown(f"""
            <div class="metric-card metric-{'danger' if overdue_invoices > 0 else 'success'}">
                <h3>Overdue Invoices</h3>
                <h2>{overdue_invoices}</h2>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error loading summary metrics: {str(e)}")

def initialize_billing_engine(retries: int = MAX_RETRIES) -> Optional[BillingEngine]:
    """Initialize billing engine with retry logic"""
    for attempt in range(retries):
        try:
            return BillingEngine()
        except Exception as e:
            if attempt == retries - 1:
                st.error(f"Failed to initialize billing system: {str(e)}")
                return None
            continue

def get_db_connection_with_retry(retries: int = MAX_RETRIES) -> Optional[object]:
    """Get database connection with retry logic"""
    for attempt in range(retries):
        try:
            conn = get_db_connection()  
            if validate_db_connection(conn):
                return conn
            else:
                conn.close()  # Close if validation fails
        except Exception as e:
            if attempt == retries - 1:
                st.error(f"Failed to connect to database after {retries} attempts: {str(e)}")
                return None
            time.sleep(1)  # Wait before retrying
            continue
    return None

def get_validated_user_info(cursor) -> Optional[Tuple[int, str]]:
    """Get and validate user information from session"""
    try:
        username = st.session_state.get("username")
        tenant_id = st.session_state.get("tenant_id")
        
        if not username or not tenant_id:
            st.error("Missing user information in session")
            return None

        db_user_id = get_user_id(username)
        if not db_user_id:
            st.error("User not found in database")
            return None

        return db_user_id, tenant_id
    except Exception as e:
        st.error(f"Error retrieving user info: {str(e)}")
        return None

def display_subscription_info(cursor, db_user_id: int):
    """Display current subscription information with fallback"""
    st.markdown("""
    <div class="section-header">
        <div class="icon">🔹</div>
        <h2>Current Subscription</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container(border=True):
        try:
            cursor.execute("""
                SELECT p.name, p.description, s.start_date, s.end_date
                FROM subscriptions s
                JOIN plans p ON s.plan_id = p.id
                WHERE s.user_id = %s AND s.is_active
                ORDER BY s.start_date DESC
                LIMIT 1
            """, (db_user_id,))
            plan = cursor.fetchone()

            if not plan:
                display_empty_state(
                    "No active subscription found",
                    "Please contact support to subscribe to a plan",
                    icon="⚠️"
                )
                return

            plan_name, plan_description, start_date, end_date = plan
            cols = st.columns([2, 1])
            
            with cols[0]:
                st.markdown(f"**Plan:** {plan_name}")
                if plan_description:
                    st.caption(plan_description)
                
            with cols[1]:
                st.caption(f"Start Date: {start_date.strftime('%Y-%m-%d')}")
                if end_date:
                    days_remaining = (end_date - datetime.now().date()).days
                    status = "active" if days_remaining > 0 else "expired"
                    st.caption(f"End Date: {end_date.strftime('%Y-%m-%d')} ({status})")
                    
                    if days_remaining <= 7 and days_remaining > 0:
                        st.markdown(f"""
                        <div class="alert-card alert-warning">
                            <strong>⚠️ Plan expires in {days_remaining} days</strong>
                        </div>
                        """, unsafe_allow_html=True)
                    elif days_remaining <= 0:
                        st.markdown(f"""
                        <div class="alert-card alert-danger">
                            <strong>❌ Plan has expired</strong>
                        </div>
                        """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error loading subscription info: {str(e)}")

def display_usage_metrics(cursor, db_user_id: int):
    """Display usage metrics with visualization enhancements"""
    st.markdown("""
    <div class="section-header">
        <div class="icon">📈</div>
        <h2>Current Usage</h2>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        current_month = datetime.utcnow().strftime('%Y-%m')
        cursor.execute("""
            SELECT 
                um.id,
                um.name, 
                um.description,
                pml.metric_limit, 
                COALESCE(SUM(ur.usage_amount), 0) as used,
                um.unit
            FROM plan_metric_limits pml
            JOIN usage_metrics um ON pml.metric_id = um.id
            LEFT JOIN usage_records ur ON ur.metric_id = um.id 
                AND ur.user_id = %s 
                AND TO_CHAR(ur.usage_date, 'YYYY-MM') = %s
            WHERE pml.plan_id = (
                SELECT plan_id FROM subscriptions 
                WHERE user_id = %s AND is_active
                ORDER BY start_date DESC LIMIT 1
            )
            GROUP BY um.id, um.name, um.description, pml.metric_limit, um.unit
            ORDER BY um.name
        """, (db_user_id, current_month, db_user_id))
        
        metrics = cursor.fetchall()

        if not metrics:
            display_empty_state(
                "No usage metrics available",
                "Your current plan doesn't have any usage metrics configured",
                icon="ℹ️"
            )
            return

        # Display metrics in responsive columns
        cols = st.columns(2)
        for i, (metric_id, metric_name, metric_desc, limit, used, unit) in enumerate(metrics):
            with cols[i % 2]:
                with st.container(border=True):
                    # Metric header with tooltip
                    if metric_desc:
                        st.markdown(f"**{metric_name}**  \n_{metric_desc}_")
                    else:
                        st.markdown(f"**{metric_name}**")
                    
                    # Calculate usage stats
                    percent_used = min((used / limit) * 100, 100) if limit > 0 else 0
                    remaining = max(limit - used, 0)
                    unit_display = f" {unit}" if unit else ""
                    
                    # Enhanced progress bar with status
                    st.progress(
                        percent_used / 100,
                        text=f"{used:,.2f}{unit_display} of {limit:,.2f}{unit_display} ({percent_used:.0f}%) used"
                    )
                    
                    # Usage status with color coding
                    if used > limit:
                        st.markdown(f"""
                        <div class="alert-card alert-danger">
                            <strong>❌ Over by {(used - limit):,.2f}{unit_display}</strong>
                        </div>
                        """, unsafe_allow_html=True)
                    elif percent_used > 90:
                        st.markdown(f"""
                        <div class="alert-card alert-warning">
                            <strong>⚠️ Critical: Only {remaining:,.2f}{unit_display} remaining</strong>
                        </div>
                        """, unsafe_allow_html=True)
                    elif percent_used > 75:
                        st.markdown(f"""
                        <div class="alert-card alert-warning">
                            <strong>⚠️ Warning: {remaining:,.2f}{unit_display} remaining</strong>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="alert-card alert-success">
                            <strong>✅ {remaining:,.2f}{unit_display} remaining</strong>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Add usage trend visualization if historical data exists
                    display_usage_trend(cursor, db_user_id, metric_id, metric_name, unit)

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading usage metrics: {str(e)}")

def display_usage_trend(cursor, user_id: int, metric_id: int, metric_name: str, unit: str):
    """Display usage trend visualization if data exists"""
    try:
        cursor.execute("""
            SELECT 
                TO_CHAR(usage_date, 'YYYY-MM') as month,
                SUM(usage_amount) as total_usage
            FROM usage_records
            WHERE user_id = %s AND metric_id = %s
            GROUP BY month
            ORDER BY month DESC
            LIMIT 6
        """, (user_id, metric_id))
        
        trend_data = cursor.fetchall()
        
        if len(trend_data) > 1:
            df = pd.DataFrame(trend_data, columns=['Month', 'Usage'])
            df['Month'] = pd.to_datetime(df['Month'])
            df = df.sort_values('Month')
            
            with st.expander(f"📊 {metric_name} Trend"):
                fig = px.line(
                    df,
                    x='Month',
                    y='Usage',
                    title=f"{metric_name} Usage Trend",
                    template="plotly_white",
                    line_shape="spline"
                )
                fig.update_layout(
                    hovermode="x unified",
                    xaxis_title="Month",
                    yaxis_title=f"Usage ({unit})" if unit else "Usage",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"Historical usage in {unit}" if unit else "Historical usage")
    except Exception as e:
        # Silently fail for trend data to not disrupt main flow
        pass

def display_invoice_history(cursor, db_user_id: int):
    """Display invoice history with enhanced visualization"""
    st.markdown("""
    <div class="section-header">
        <div class="icon">🧾</div>
        <h2>Invoice History</h2>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        cursor.execute("""
            SELECT 
                i.id, 
                i.id as invoice_number,
                i.period_start, 
                i.period_end, 
                i.total_invoiced,
                i.payment_status,
                COALESCE(SUM(p.amount), 0) as paid_amount,
                MAX(p.payment_date) as last_payment_date,
                BOOL_OR(p.is_verified) as is_verified
            FROM invoices i
            LEFT JOIN payments p ON i.id = p.invoice_id
            WHERE i.user_id = %s
            GROUP BY i.id
            ORDER BY i.period_start DESC
            LIMIT 12
        """, (db_user_id,))
        
        invoices = cursor.fetchall()

        if not invoices:
            display_empty_state(
                "No invoices found",
                "Your account doesn't have any invoices yet",
                icon="📄"
            )
            return

        # Enhanced dataframe with better formatting
        df = pd.DataFrame(invoices, columns=[
            "ID", "Invoice #", "Start Date", "End Date", "Total", 
            "Status", "Paid", "Last Payment", "Verified"
        ])
        
        # Format dates
        df['Start Date'] = pd.to_datetime(df['Start Date']).dt.strftime('%Y-%m-%d')
        df['End Date'] = pd.to_datetime(df['End Date']).dt.strftime('%Y-%m-%d')
        df['Last Payment'] = pd.to_datetime(df['Last Payment']).dt.strftime('%Y-%m-%d')
        
        # Store original numeric values before formatting
        df['_total_invoiced'] = df['Total']
        df['_paid_amount'] = df['Paid']
        
        # Format currency for display
        df['Total'] = df['Total'].apply(lambda x: format_currency(x))
        df['Paid'] = df['Paid'].apply(lambda x: format_currency(x))
        
        # Determine payment status using original numeric values
        def get_payment_status(row):
            paid_amount = row['_paid_amount']
            if row['Verified']:
                return "✅ Paid"
            elif paid_amount > 0:
                return "⏳ Partial"
            elif row['Status'] == 'void':
                return "❌ Void"
            else:
                return "❌ Unpaid"
        
        df['Payment Status'] = df.apply(get_payment_status, axis=1)
        
        # Display with enhanced features
        st.dataframe(
            df[['Invoice #', 'Start Date', 'End Date', 'Total', 'Paid', 'Payment Status']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Invoice #": st.column_config.NumberColumn("Invoice #", width="small"),
                "Start Date": st.column_config.DateColumn("Period Start"),
                "End Date": st.column_config.DateColumn("Period End"),
                "Total": st.column_config.TextColumn("Total Amount"),
                "Paid": st.column_config.TextColumn("Amount Paid"),
                "Payment Status": st.column_config.TextColumn("Status")
            }
        )
        
        # Add download buttons for each invoice
        with st.expander("Invoice Actions"):
            selected_invoice = st.selectbox(
                "Select invoice to download",
                df['Invoice #'],
                index=0,
                key="invoice_select"
            )
            
            if st.button("📥 Download Invoice PDF", use_container_width=True):
                download_invoice_pdf(cursor, df[df['Invoice #'] == selected_invoice].iloc[0]['ID'])

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading invoice history: {str(e)}")
        
def download_invoice_pdf(cursor, invoice_id: int):
    """Handle invoice PDF download"""
    try:
        with loading_spinner("Generating invoice PDF..."):
            # Initialize billing engine
            billing_engine = BillingEngine()
            
            # Get invoice data
            cursor.execute("""
                SELECT id, id as invoice_number, period_start, period_end, 
                       total_invoiced, payment_status, created_at,
                       user_id, tenant_id
                FROM invoices 
                WHERE id = %s
            """, (int(invoice_id),))
            
            invoice = cursor.fetchone()
            
            if not invoice:
                st.error("Invoice not found")
                return
                
            # Get line items
            cursor.execute("""
                SELECT description, quantity, unit_price, total_price 
                FROM invoice_items 
                WHERE invoice_id = %s
                ORDER BY id
            """, (int(invoice_id),))
            
            items = []
            for row in cursor.fetchall():
                items.append({
                    "description": str(row[0]),
                    "quantity": float(row[1]),
                    "unit_price": float(row[2]),
                    "total_price": float(row[3])
                })
            
            # Prepare invoice data with proper types
            invoice_dict = {
                "id": int(invoice[0]),
                "invoice_number": str(invoice[1]),
                "period_start": invoice[2].strftime('%Y-%m-%d') if invoice[2] else "",
                "period_end": invoice[3].strftime('%Y-%m-%d') if invoice[3] else "",
                "total_invoiced": float(invoice[4]),
                "payment_status": str(invoice[5]),
                "invoice_date": invoice[6].strftime('%Y-%m-%d') if invoice[6] else datetime.now().strftime('%Y-%m-%d'),
                "user_id": int(invoice[7]),
                "tenant_id": int(invoice[8])
            }
            
            try:
                # Get tenant and client info
                tenant_info = billing_engine.get_tenant_info(cursor, invoice_dict["tenant_id"])
                client_info = billing_engine.get_client_info(cursor, invoice_dict["user_id"])
                
                # Generate PDF
                pdf_bytes = generate_invoice_pdf(
                    invoice_dict, 
                    items,
                    tenant_info=tenant_info,
                    client_info=client_info
                )
                
                # Offer download
                st.download_button(
                    label="⬇️ Download Now",
                    data=pdf_bytes,
                    file_name=f"invoice_{invoice_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"download_{invoice_id}"
                )
            except Exception as e:
                st.error(f"Failed to generate PDF: {str(e)}")
                logging.error(f"PDF generation error: {str(e)}")
                
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        logging.error(f"Database error in download_invoice_pdf: {str(e)}")
                        
def display_current_period_estimate(billing_engine, cursor, db_user_id: int, tenant_id: str):
    """Display current period estimate with interactive features"""
    st.markdown("""
    <div class="section-header">
        <div class="icon">📄</div>
        <h2>Current Period Estimate</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container(border=True):
        try:
            # Get estimate with error handling
            items, estimated_total = billing_engine.estimate_invoice_for_user(db_user_id, tenant_id)
            
            if not items:
                display_empty_state(
                    "No estimated charges",
                    "No usage has been recorded for the current period",
                    icon="ℹ️"
                )
                return

            # Display breakdown in columns
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Breakdown**")
                for item in items:
                    cols = st.columns([3, 1, 1, 1])
                    cols[0].write(item['description'])
                    cols[1].write(f"{item['quantity']}")
                    cols[2].write(f"R{item['unit_price']:.2f}")
                    cols[3].write(f"**R{item['total_price']:.2f}**")
            
            with col2:
                st.markdown(f"""
                <div class="metric-card metric-neutral">
                    <h3>Estimated Total</h3>
                    <h2>{format_currency(estimated_total)}</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # PDF download button
                if st.button("📥 Download Estimate PDF", use_container_width=True):
                    download_estimate_pdf(billing_engine, cursor, items, estimated_total, tenant_id)
                
                # Finalize invoice button with confirmation dialog
                if st.button("💳 Generate Final Invoice", type="primary", use_container_width=True):
                    handle_invoice_generation(billing_engine, db_user_id, tenant_id)

        except Exception as e:
            st.error(f"Error generating estimate: {str(e)}")

def download_estimate_pdf(billing_engine, cursor, items: List[Dict], estimated_total: float, tenant_id: str):
    """Handle estimate PDF download"""
    try:
        with loading_spinner("Generating PDF..."):
            # Convert items to use proper types
            converted_items = []
            for item in items:
                converted_items.append({
                    'description': str(item['description']),
                    'quantity': float(item['quantity']),
                    'unit_price': float(item['unit_price']),
                    'total_price': float(item['total_price'])
                })
            
            # Create fake invoice with proper types
            fake_invoice = {
                "id": "ESTIMATE",
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "period_start": datetime.now().replace(day=1).strftime("%Y-%m-%d"),
                "period_end": datetime.now().strftime("%Y-%m-%d"),
                "total_invoiced": float(estimated_total),
                "is_paid": False,
                "user_id": st.session_state.get("user_id", 0),
                "tenant_id": int(tenant_id)
            }
            
            # Get tenant and client info
            tenant_info = billing_engine.get_tenant_info(cursor, fake_invoice["tenant_id"])
            client_info = billing_engine.get_client_info(cursor, fake_invoice["user_id"])
            
            pdf_bytes = generate_invoice_pdf(
                fake_invoice, 
                converted_items,
                tenant_info=tenant_info,
                client_info=client_info
            )
            
            current_month = datetime.now().strftime("%Y-%m")
            st.download_button(
                label="⬇️ Download Now",
                data=pdf_bytes,
                file_name=f"estimate_{current_month}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    except Exception as e:
        st.error(f"Failed to generate estimate PDF: {str(e)}")
                
def handle_invoice_generation(billing_engine, db_user_id: int, tenant_id: str):
    """Handle invoice generation with confirmation flow"""
    if not st.session_state.get("confirm_invoice", False):
        st.session_state.confirm_invoice = True
        st.markdown("""
        <div class="alert-card alert-warning">
            <h3>⚠️ Are you sure you want to generate a final invoice?</h3>
            <p>• This action cannot be undone</p>
            <p>• The invoice will be sent to your registered email</p>
            <p>• Payment will be due according to your terms</p>
        </div>
        """, unsafe_allow_html=True)
        
        cols = st.columns(2)
        with cols[0]:
            if st.button("✅ Yes, generate invoice", type="primary", use_container_width=True):
                st.session_state.confirm_invoice = False
                st.rerun()
        with cols[1]:
            if st.button("❌ Cancel", type="secondary", use_container_width=True):
                st.session_state.confirm_invoice = False
                st.rerun()
    else:
        with loading_spinner("Creating invoice..."):
            success, result = billing_engine.finalize_invoice_for_user(db_user_id, tenant_id)
            if success:
                show_toast(f"Invoice #{result} created successfully!", "success")
                st.session_state.refresh_data = True
                st.rerun()
            else:
                st.error(f"Error: {result}")

def get_user_id(username: str) -> Optional[int]:
    """Get database user ID with validation"""
    conn = None  # Initialize conn variable
    try:
        conn = get_db_connection()  
        if not conn:
            st.error("Failed to establish database connection")
            return None
            
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        st.error(f"Error retrieving user ID: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def handle_dashboard_error(error: Exception):
    """Handle dashboard errors gracefully"""
    st.markdown("""
    <div class="alert-card alert-danger">
        <h2>🚨 Dashboard Error</h2>
        <p>We encountered an unexpected error while loading your dashboard.</p>
        <p>Please try refreshing the page or contact support if the problem persists.</p>
    </div>
    """, unsafe_allow_html=True)
    st.error(f"Technical details: {str(error)}")
    st.stop()

if __name__ == "__main__":
    client_usage_dashboard()