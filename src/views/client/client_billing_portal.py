# src/views/client/client_billing_portal.py
import streamlit as st
from datetime import datetime
from db.database import get_db_connection
from utils.session import init_session_state, validate_session
from utils.ui_helpers import show_toast, loading_spinner, format_date
from billing_engine import BillingEngine 
from utils.pdf_utils import generate_invoice_pdf
from utils.pdf_generator import generate_pdf_invoice


# Custom CSS for professional styling matching admin dashboard
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
    
    .invoice-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-left: 4px solid var(--info);
        transition: all 0.3s ease;
    }
    .invoice-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }
    .invoice-paid {
        border-left-color: var(--secondary);
    }
    .invoice-unpaid {
        border-left-color: var(--danger);
    }
</style>
""", unsafe_allow_html=True)

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"

def client_billing_portal():
    """Enhanced Client billing portal with professional UX matching admin dashboard."""
    
    # Initialize page config first to prevent resizing
    st.set_page_config(
        page_title="My Billing Portal",
        layout="wide",
        page_icon="💳"
    )
    
    init_session_state()
    
    # Session validation with redirect
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()

    # Check if we're showing a payment modal
    if st.session_state.get("current_invoice"):
        show_payment_modal()
        return  # Stop rendering the rest of the page

    user_id = st.session_state.user_id
    tenant_id = st.session_state.tenant_id

    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">💳 My Billing Portal</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            <button onclick="window.location.reload()" style="background-color: #4F46E5; color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; cursor: pointer;">Refresh Data</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        billing_engine = BillingEngine()

        # --- Get tenant name if not in session state
        if 'tenant_name' not in st.session_state:
            with loading_spinner("Loading organization info..."):
                cursor.execute("SELECT name FROM tenants WHERE id = %s", (tenant_id,))
                result = cursor.fetchone()
                st.session_state.tenant_name = result[0] if result else "My Company"

        # --- Current Plan Section
        st.markdown("""
        <div class="section-header">
            <div class="icon">📦</div>
            <h2>Current Subscription Plan</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with loading_spinner("Loading subscription details..."):
            cursor.execute("""
                SELECT p.name, p.description, p.monthly_fee, p.included_units, 
                       p.overage_rate, s.start_date, p.billing_cycle
                FROM subscriptions s
                JOIN plans p ON s.plan_id = p.id
                WHERE s.user_id = %s AND s.is_active
                ORDER BY s.start_date DESC LIMIT 1
            """, (user_id,))
            plan = cursor.fetchone()

        if not plan:
            st.warning("You don't have an active subscription")
            return

        plan_name, description, monthly_fee, included_units, overage_rate, start_date, billing_cycle = plan
        
        # Plan details in cards
        cols = st.columns(3)
        with cols[0]:
            st.markdown(f"""
            <div class="metric-card metric-positive">
                <h3>Plan Name</h3>
                <h2>{plan_name}</h2>
                <p style="color: #6B7280; margin-top: 0.5rem;">{description or 'No description'}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Monthly Fee</h3>
                <h2>{format_currency(monthly_fee)}</h2>
                <p style="color: #6B7280; margin-top: 0.5rem;">Billing Cycle: {billing_cycle.capitalize()}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[2]:
            st.markdown(f"""
            <div class="metric-card metric-warning">
                <h3>Included Units</h3>
                <h2>{included_units:,}</h2>
                <p style="color: #6B7280; margin-top: 0.5rem;">Overage Rate: {format_currency(overage_rate)}/unit</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="text-align: center; color: #6B7280; margin-bottom: 1.5rem;">
            Active since: {format_date(start_date)}
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # --- Usage Metrics Section
        st.markdown("""
        <div class="section-header">
            <div class="icon">📊</div>
            <h2>Current Period Usage</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with loading_spinner("Loading usage data..."):
            cursor.execute("""
                SELECT m.name, SUM(u.usage_amount) as total_usage
                FROM usage_records u
                JOIN usage_metrics m ON u.metric_id = m.id
                WHERE u.user_id = %s AND u.tenant_id = %s
                AND u.usage_date BETWEEN date_trunc('month', CURRENT_DATE) AND CURRENT_DATE
                GROUP BY m.name
                ORDER BY m.name
            """, (user_id, tenant_id))
            usage_data = cursor.fetchall()

        if usage_data:
            for metric_type, total_usage in usage_data:
                with st.expander(f"🔹 {metric_type}", expanded=True):
                    overage = max(0, total_usage - included_units)
                    progress = min(total_usage / included_units, 1) if included_units > 0 else 0
                    progress_color = "#EF4444" if progress > 0.9 else "#10B981" if progress < 0.7 else "#F59E0B"
                    
                    st.markdown(f"""
                    <div style="margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="font-weight: 600;">Usage Progress</span>
                            <span style="color: {progress_color}; font-weight: 600;">{progress:.0%}</span>
                        </div>
                        <div style="height: 8px; background-color: #E5E7EB; border-radius: 4px; overflow: hidden;">
                            <div style="height: 100%; width: {progress * 100}%; background-color: {progress_color}; border-radius: 4px;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-top: 0.5rem; color: #6B7280;">
                            <span>{total_usage:,} of {included_units:,} units</span>
                            <span>{total_usage:,} units used</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if overage > 0:
                        overage_cost = overage * overage_rate
                        st.markdown(f"""
                        <div class="alert-card alert-warning">
                            <h4>⚠️ Overage Detected</h4>
                            <p>Additional {overage:,} units at {format_currency(overage_rate)}/unit</p>
                            <p style="font-weight: 600; margin-top: 0.5rem;">Overage Cost: {format_currency(overage_cost)}</p>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("No usage recorded for current period")

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # --- Invoice History Section
        st.markdown("""
        <div class="section-header">
            <div class="icon">🧾</div>
            <h2>Invoice History</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with loading_spinner("Loading invoices..."):
            cursor.execute("""
                SELECT id, invoice_date, total_invoiced, is_paid, period_start, period_end, due_date
                FROM invoices
                WHERE user_id = %s
                ORDER BY invoice_date DESC
                LIMIT 12
            """, (user_id,))
            invoices = cursor.fetchall()

        if not invoices:
            st.info("No invoices found")
        else:
            # Summary stats
            paid_count = sum(1 for inv in invoices if inv[3])
            total_owed = sum(inv[2] for inv in invoices if not inv[3])
            overdue_count = sum(1 for inv in invoices if not inv[3] and inv[6] and inv[6] < datetime.now().date())
            
            stat_cols = st.columns(3)
            stat_cols[0].markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Total Invoices</h3>
                <h2>{len(invoices)}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            stat_cols[1].markdown(f"""
            <div class="metric-card metric-positive">
                <h3>Paid Invoices</h3>
                <h2>{paid_count}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            stat_cols[2].markdown(f"""
            <div class="metric-card metric-{'danger' if total_owed > 0 else 'positive'}">
                <h3>Amount Owed</h3>
                <h2>{format_currency(total_owed)}</h2>
            </div>
            """, unsafe_allow_html=True)

            # Invoice details
            for inv in invoices:
                inv_id, inv_date, amount, is_paid, period_start, period_end, due_date = inv
                is_overdue = not is_paid and due_date and due_date < datetime.now().date()
                
                invoice_class = "invoice-paid" if is_paid else "invoice-unpaid" if is_overdue else "invoice-card"
                
                st.markdown(f"""
                <div class="{invoice_class}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                        <div>
                            <h3 style="margin: 0; color: #1F2937;">Invoice #{inv_id}</h3>
                            <p style="color: #6B7280; margin: 0.25rem 0;">Period: {format_date(period_start)} to {format_date(period_end)}</p>
                            <p style="color: #6B7280; margin: 0;">Issued: {format_date(inv_date)}</p>
                        </div>
                        <div style="text-align: right;">
                            <span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; 
                                background-color: {'#D1FAE5' if is_paid else '#FEE2E2' if is_overdue else '#DBEAFE'}; 
                                color: {'#065F46' if is_paid else '#991B1B' if is_overdue else '#1E40AF'};
                                font-weight: 600; font-size: 0.875rem;">
                                {'🟢 Paid' if is_paid else '🔴 Overdue' if is_overdue else '🟡 Pending'}
                            </span>
                            <h2 style="margin: 0.5rem 0 0 0; color: #1F2937;">{format_currency(amount)}</h2>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Action buttons
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if not is_paid:
                        if st.button(
                            "💳 Pay Now", 
                            key=f"pay_{inv_id}",
                            use_container_width=True,
                            type="primary" if is_overdue else "secondary"
                        ):
                            st.session_state.current_invoice = inv_id
                            st.rerun()
                
                with col2:
                    # PDF download
                    # client_info = billing_engine.get_client_info(cursor, user_id)
                    invoice_details = billing_engine.get_invoice_details(inv_id)

                    pdf_bytes = generate_pdf_invoice(invoice_details=invoice_details, tenant_id=st.session_state.tenant_id)
                    st.download_button(
                        label="📄 Download PDF",
                        data=pdf_bytes,
                        file_name=f"invoice_{inv_id}.pdf",
                        mime="application/pdf",
                        key=f"dl_{inv_id}",
                        use_container_width=True
                    )
                
                with col3:
                    if is_overdue:
                        st.markdown("""
                        <div class="alert-card alert-danger">
                            <p style="margin: 0; font-size: 0.875rem;">⚠️ This invoice is overdue. Please pay immediately to avoid service interruption.</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"An error occurred while loading billing data: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def show_payment_modal():
    """Enhanced payment modal with professional styling"""
    # Clear other content
    st.markdown("""
        <style>
            div[data-testid="stAppViewBlockContainer"] > div:first-child {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Modal content in container
    with st.container():
        st.markdown("---")
        st.markdown(f"""
        <div class="section-header">
            <div class="icon">💳</div>
            <h2>Payment for Invoice #{st.session_state.current_invoice}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            billing_engine = BillingEngine()

            # Get invoice details
            invoice, items = billing_engine.get_invoice_summary(st.session_state.current_invoice)

            if not invoice:
                st.error("Invoice not found")
                st.session_state.pop("current_invoice")
                st.rerun()

            # Display invoice summary
            with st.container(border=True):
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"""
                    <div style="padding: 1rem;">
                        <h3 style="color: #1F2937; margin-bottom: 1rem;">Invoice Summary</h3>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: #6B7280;">Amount Due:</span>
                            <span style="font-weight: 600;">{format_currency(invoice['total_invoiced'])}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: #6B7280;">Due Date:</span>
                            <span style="font-weight: 600; color: {'#EF4444' if invoice.get('due_date') and invoice['due_date'] < datetime.now().date() else '#1F2937'}">
                                {format_date(invoice.get('due_date')) or 'N/A'}
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with cols[1]:
                    if items:
                        st.markdown("""
                        <div style="padding: 1rem;">
                            <h4 style="color: #1F2937; margin-bottom: 0.5rem;">Invoice Items</h4>
                        """, unsafe_allow_html=True)
                        for item in items:
                            st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: 0.875rem;">
                                <span>{item.get('description', 'N/A')}</span>
                                <span>{format_currency(item.get('amount', 0))}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)

            # Payment form
            with st.form("payment_form", border=True):
                st.markdown("""
                <div style="padding: 1rem;">
                    <h3 style="color: #1F2937; margin-bottom: 1rem;">Payment Details</h3>
                """, unsafe_allow_html=True)
                
                amount = st.number_input(
                    "Payment Amount",
                    min_value=0.01,
                    value=float(invoice['total_invoiced']),
                    step=0.01,
                    format="%.2f"
                )
                
                payment_method = st.selectbox(
                    "Payment Method",
                    ["Credit Card", "Bank Transfer", "Other"],
                    index=0
                )
                
                reference = st.text_input("Payment Reference")
                
                submitted = st.form_submit_button(
                    "Submit Payment",
                    type="primary",
                    use_container_width=True
                )
                
                if submitted:
                    try:
                        # Process payment
                        cursor.execute("""
                            INSERT INTO payments (
                                invoice_id, 
                                amount, 
                                payment_method, 
                                notes,
                                payment_date
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            st.session_state.current_invoice,
                            amount,
                            payment_method,
                            f"Reference: {reference}" if reference else None,
                            datetime.utcnow().date()
                        ))
                        conn.commit()
                        show_toast("✅ Payment processed successfully!", "success")
                        st.session_state.pop("current_invoice")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Payment failed: {str(e)}")
                        conn.rollback()

            # Back button
            if st.button(
                "← Back to Invoices",
                use_container_width=True
            ):
                st.session_state.pop("current_invoice")
                st.rerun()

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        finally:
            if conn:
                conn.close()
        st.markdown("---")

if __name__ == "__main__":
    client_billing_portal()