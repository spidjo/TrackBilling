import streamlit as st
from decimal import Decimal
from datetime import datetime, timedelta
from payment_logic import record_payment, get_invoice_payment_summary, PaymentStatus
from utils.session import init_session_state, validate_session
from db.database import get_db_connection

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
    
    .invoice-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
        border-left: 4px solid;
    }
    .invoice-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }
    .invoice-paid {
        border-left-color: var(--secondary);
    }
    .invoice-partial {
        border-left-color: var(--warning);
    }
    .invoice-unpaid {
        border-left-color: var(--danger);
    }
    .invoice-overdue {
        border-left-color: var(--danger);
        background-color: #FEF2F2;
    }
    
    .status-badge {
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }
    .status-paid {
        background-color: #ECFDF5;
        color: #065F46;
    }
    .status-partial {
        background-color: #FFFBEB;
        color: #92400E;
    }
    .status-unpaid {
        background-color: #FEF2F2;
        color: #991B1B;
    }
    .status-overdue {
        background-color: #F5F3FF;
        color: #5B21B6;
    }
    
    .payment-item {
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }
    .payment-item:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
    
    .progress-bar {
        height: 6px;
        background-color: #E5E7EB;
        border-radius: 3px;
        margin: 0.5rem 0;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background-color: var(--primary);
        border-radius: 3px;
        transition: width 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

def get_status_badge(status, is_overdue: bool = False):
    """Returns styled badge for payment status with improved design"""
    # Convert string status to PaymentStatus enum if needed
    if isinstance(status, str):
        try:
            status = PaymentStatus(status.lower())
        except ValueError:
            status = PaymentStatus.UNPAID
    
    status_map = {
        PaymentStatus.PAID: ("status-paid", "✅", "PAID"),
        PaymentStatus.PARTIAL: ("status-partial", "⏳", "PARTIAL"),
        PaymentStatus.UNPAID: ("status-unpaid", "❌", "UNPAID"),
        PaymentStatus.OVERDUE: ("status-overdue", "⚠️", "OVERDUE")
    }
    
    badge_class, icon, text = status_map.get(status, ("status-unpaid", "❓", "UNKNOWN"))
    
    if is_overdue and status != PaymentStatus.PAID:
        badge_class = "status-overdue"
        icon = "⚠️"
        text = "OVERDUE"
    
    return f"""
    <span class="status-badge {badge_class}">
        {icon} {text}
    </span>
    """

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"

def payment_admin():
    """Professional payment administration interface with enhanced UX"""
    # Initialize session and page config
    init_session_state()
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()

    st.set_page_config(
        page_title="💳 Payment Admin",
        layout="wide",
        page_icon="💳"
    )
    
    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">💳 Payment Administration</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # Initialize session state for selected invoice and toast
    if 'selected_invoice_id' not in st.session_state:
        st.session_state.selected_invoice_id = None
    if 'show_toast' not in st.session_state:
        st.session_state.show_toast = False
    
    # Get payment statistics
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_invoices,
                SUM(CASE WHEN payment_status = 'paid' THEN 1 ELSE 0 END) as paid_invoices,
                SUM(CASE WHEN payment_status = 'unpaid' THEN 1 ELSE 0 END) as unpaid_invoices,
                SUM(CASE WHEN payment_status = 'partial' THEN 1 ELSE 0 END) as partial_invoices,
                SUM(CASE WHEN due_date < CURRENT_DATE AND payment_status != 'paid' THEN 1 ELSE 0 END) as overdue_invoices
            FROM invoices
            WHERE tenant_id = %s
        """, (st.session_state.tenant_id,))
        stats = cursor.fetchone()
        total_invoices = stats["total_invoices"] if stats else 0
        paid_invoices = stats["paid_invoices"] if stats else 0
        unpaid_invoices = stats["unpaid_invoices"] if stats else 0
        partial_invoices = stats["partial_invoices"] if stats else 0
        overdue_invoices = stats["overdue_invoices"] if stats else 0
    finally:
        conn.close()

    # Display payment statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card metric-neutral">
            <h3>Total Invoices</h3>
            <h2>{total_invoices:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card metric-positive">
            <h3>Paid Invoices</h3>
            <h2>{paid_invoices:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card metric-warning">
            <h3>Partial Payments</h3>
            <h2>{partial_invoices:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card metric-negative">
            <h3>Overdue Invoices</h3>
            <h2>{overdue_invoices:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
    # Record Payment Section
    with st.expander("📝 Record Payment", expanded=True):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get unpaid invoices with payment summary
        cursor.execute("""
            SELECT 
                i.id, i.tenant_id, i.invoice_date, i.due_date, 
                i.total_invoiced, i.payment_status,
                t.name as tenant_name, u.username,
                COALESCE(SUM(p.amount), 0) as paid_amount
            FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            JOIN users u ON i.user_id = u.id
            LEFT JOIN payments p ON p.invoice_id = i.id
            WHERE i.payment_status != 'paid' AND i.tenant_id = %s
            GROUP BY i.id, t.name, u.username
            ORDER BY i.due_date ASC, i.invoice_date DESC
            LIMIT 50
        """, (st.session_state.tenant_id,))
        invoices = cursor.fetchall()
        conn.close()

        if not invoices:
            st.success("🎉 All invoices are paid!")
            return

        # Invoice selection with improved UX
        st.markdown("""
        <div class="section-header">
            <div class="icon">📋</div>
            <h2>Select Invoice</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Get the index of the previously selected invoice if it exists
        selected_index = 0
        if st.session_state.selected_invoice_id:
            for i, inv in enumerate(invoices):
                if inv[0] == st.session_state.selected_invoice_id:
                    selected_index = i
                    break
        
        # Enhanced invoice selector with search capability
        search_col, select_col = st.columns([1, 3])
        with search_col:
            search_term = st.text_input("Search invoices", placeholder="Search by ID, tenant...")
        
        filtered_invoices = invoices
        if search_term:
            filtered_invoices = [
                inv for inv in invoices 
                if (search_term.lower() in str(inv[0]).lower() or  # invoice ID
                    search_term.lower() in inv[6].lower() or  # tenant name
                    search_term.lower() in inv[7].lower())  # username
            ]
            if not filtered_invoices:
                st.info("No invoices match your search")
                return
        
        with select_col:
            selected_invoice = st.selectbox(
                "Available Invoices",
                filtered_invoices,
                index=selected_index if filtered_invoices[selected_index] in filtered_invoices else 0,
                format_func=lambda x: (
                    f"Invoice #{x[0]} • {x[6]} • "
                    f"Total: {format_currency(x[4])} • Paid: {format_currency(x[8])} • "
                    f"Due: {x[3].strftime('%Y-%m-%d') if x[3] else 'No due date'}"
                ),
                help="Select an invoice to record payment for",
                key="invoice_selectbox",
                label_visibility="collapsed"
            )
        
        selected_invoice_id = selected_invoice[0]
        st.session_state.selected_invoice_id = selected_invoice_id
        
        # Get detailed payment summary
        try:
            summary = get_invoice_payment_summary(selected_invoice_id)
            # Determine display status
            display_status = summary['payment_status']
            if summary['is_overdue'] and display_status != PaymentStatus.PAID.value:
                display_status += " (OVERDUE)"
        except Exception as e:
            st.error(f"Failed to get invoice details: {str(e)}")
            return
        
        # Display invoice summary with enhanced visualization
        container_class = "invoice-card"
        if summary['is_overdue']:
            container_class += " invoice-overdue"
        elif summary['payment_status'] == PaymentStatus.PARTIAL.value:
            container_class += " invoice-partial"
        elif summary['payment_status'] == PaymentStatus.PAID.value:
            container_class += " invoice-paid"
        else:
            container_class += " invoice-unpaid"
            
        with st.container():
            st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
            
            # Header with invoice info
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"<h3 style='margin: 0; color: #1F2937;'>Invoice #{selected_invoice_id}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin: 0.25rem 0 0; color: #6B7280; font-size: 0.9rem;'>Tenant: {selected_invoice[6]} • Issued: {selected_invoice[2].strftime('%Y-%m-%d') if selected_invoice[2] else 'No date'}</p>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(get_status_badge(summary['payment_status'], summary['is_overdue']), unsafe_allow_html=True)
            
            # Payment metrics with visual indicators
            cols = st.columns(3)
            with cols[0]:
                st.markdown(f"""
                <div style="margin-bottom: 0.5rem; color: #6B7280; font-size: 0.9rem;">
                    Total Amount
                </div>
                <h3 style="margin: 0; color: #1F2937;">
                    {format_currency(summary['total_amount'])}
                </h3>
                """, unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(f"""
                <div style="margin-bottom: 0.5rem; color: #6B7280; font-size: 0.9rem;">
                    Paid Amount
                </div>
                <h3 style="margin: 0; color: #10B981;">
                    {format_currency(summary['paid_amount'])}
                </h3>
                """, unsafe_allow_html=True)
            
            with cols[2]:
                balance_color = "#EF4444" if summary['is_overdue'] else "#1F2937"
                st.markdown(f"""
                <div style="margin-bottom: 0.5rem; color: #6B7280; font-size: 0.9rem;">
                    Balance Due
                </div>
                <h3 style="margin: 0; color: {balance_color};">
                    {format_currency(summary['remaining_balance'])}
                </h3>
                """, unsafe_allow_html=True)
            
            # Due date indicator with visual urgency
            if summary['due_date']:
                days_overdue = (datetime.now().date() - summary['due_date']).days if summary['is_overdue'] else 0
                st.markdown(f"""
                <div style="margin-top: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                    <div style="font-size: 0.9rem; color: #6B7280;">
                        Due Date: 
                        <span style="color: {'#EF4444' if summary['is_overdue'] else '#10B981'}; font-weight: 500;">
                            {summary['due_date'].strftime('%Y-%m-%d')}{f' ({days_overdue} days overdue)' if summary['is_overdue'] else ''}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)  
                
        # Payment details form with enhanced UX
        st.markdown("""
        <div class="section-header">
            <div class="icon">💳</div>
            <h2>Payment Details</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form(key="payment_form"):
            # Calculate max payment amount safely
            max_payment = float(summary['remaining_balance'] + summary['credit_amount'])
            min_value = 0.01 if max_payment >= 0.01 else 0.0
            
            # Amount input with visual guidance
            amount_col, method_col = st.columns([1, 1])
            with amount_col:
                amount = st.number_input(
                    "Amount Paid", 
                    min_value=min_value,
                    max_value=max_payment if max_payment >= 0.01 else 0.0,
                    value=float(min(
                        max(summary['remaining_balance'], Decimal('0')),
                        summary['total_amount']
                    )),
                    step=0.01,
                    format="%.2f",
                    help=f"Maximum payment allowed: {format_currency(max_payment)}"
                )
                # Visual payment amount helper
                if amount > 0:
                    payment_percent = (amount / float(summary['total_amount'])) * 100
                    st.markdown(f"""
                    <div style="margin-top: 0.5rem; margin-bottom: 1rem;">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {payment_percent}%;"></div>
                        </div>
                        <div style="font-size: 0.75rem; color: #6B7280; text-align: right;">
                            {payment_percent:.0f}% of invoice total
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            with method_col:
                method = st.selectbox(
                    "Payment Method",
                    ["Bank Transfer", "Credit Card", "Cash", "Check", "Other"],
                    index=0
                )
            
            # Enhanced notes field
            notes = st.text_area(
                "Payment Notes",
                placeholder="Add any relevant notes about this payment...",
                help="Optional reference information for this payment"
            )
            
            # Disable button if balance is <= 0
            disable_button = summary['remaining_balance'] <= 0
            
            # Form submission with visual feedback
            submitted = st.form_submit_button(
                "💾 Record Payment",
                type="primary",
                use_container_width=True,
                disabled=disable_button,
                help="Invoice already paid" if disable_button else "Save this payment record"
            )

        # Form submission handling with improved feedback
        if submitted and not disable_button:
            try:
                with st.spinner("Processing payment..."):
                    result = record_payment(
                        selected_invoice_id, 
                        Decimal(str(amount)), 
                        method.lower().replace(" ", "_"), 
                        notes
                    )
                    if result['success']:
                        st.session_state.show_toast = True
                        st.session_state.toast_message = (
                            f"✅ Payment recorded. New status: {result['new_status'].name.upper()}"
                        )
                        st.session_state.toast_type = "success"
                        # Force a rerun to show updated data while maintaining selection
                        st.rerun()
            except Exception as e:
                st.session_state.show_toast = True
                st.session_state.toast_message = f"❌ Error recording payment: {str(e)}"
                st.session_state.toast_type = "error"
                st.rerun()

    # Payment History Section with enhanced visualization
    with st.expander("📜 Payment History", expanded=False):
        st.markdown("""
        <div class="section-header">
            <div class="icon">🕒</div>
            <h2>Recent Payments</h2>
        </div>
        """, unsafe_allow_html=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id, p.amount, p.payment_method, p.payment_date, 
                i.id as invoice_id, t.name as tenant_name,
                i.total_invoiced, i.payment_status,
                (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE invoice_id = i.id) as paid_amount,
                p.notes
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.tenant_id = %s
            ORDER BY p.payment_date DESC
            LIMIT 15
        """, (st.session_state.tenant_id,))
        recent_payments = cursor.fetchall()
        conn.close()
        
        if recent_payments:
            # Summary stats
            total_payments = len(recent_payments)
            total_amount = sum(float(p[1]) for p in recent_payments)
            
            cols = st.columns(4)
            cols[0].metric("Total Payments", total_payments)
            cols[1].metric("Total Amount", format_currency(total_amount))
            cols[2].metric("Avg. Payment", format_currency(total_amount/total_payments) if total_payments > 0 else format_currency(0))
            
            # Payment list with enhanced visualization
            for payment in recent_payments:
                with st.container():
                    st.markdown('<div class="payment-item">', unsafe_allow_html=True)
                    
                    # Prepare data
                    payment_method = payment[2].replace('_', ' ').title()
                    payment_date = payment[3].strftime('%Y-%m-%d %H:%M') if payment[3] else 'No date'
                    balance = payment[6] - payment[8]
                    
                    # Create columns for layout
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Invoice and tenant info
                        st.markdown(f"**#{payment[4]} • {payment[5]}**")
                        
                        # Payment method and date
                        st.caption(f"**{payment_method}** • {payment_date}")
                        
                        # Payment notes if available
                        if payment[9]:
                            with st.expander("📝 View Notes", expanded=False):
                                st.write(payment[9])
                    
                    with col2:
                        # Payment amount and balance
                        st.markdown(f"**{format_currency(payment[1])}**")
                        st.caption(f"Balance: {format_currency(balance)}")
                    
                    # Status badge
                    st.markdown(get_status_badge(payment[7]), unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Divider between items
                    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        else:
            st.info("No recent payments found")

    # Show toast after successful payment
    if st.session_state.get('show_toast', False):
        if st.session_state.toast_type == "success":
            st.toast(st.session_state.toast_message, icon="✅")
        else:
            st.error(st.session_state.toast_message)
        # Clear the toast state
        st.session_state.show_toast = False

if __name__ == "__main__":
    payment_admin()