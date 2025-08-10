# src/views/client/client_billing_portal.py
import streamlit as st
from datetime import datetime
from db.database import get_db_connection
from utils.session import init_session_state
from utils.ui_helpers import show_toast, loading_spinner
from billing_engine import get_invoice_summary
from utils.pdf_utils import generate_invoice_pdf

def get_tenant_name(cursor, tenant_id):
    """Helper function to get tenant name"""
    cursor.execute("SELECT name FROM tenants WHERE id = %s", (tenant_id,))
    result = cursor.fetchone()
    return result[0] if result else "My Company"

def client_billing_portal():
    """Client billing portal with enhanced UX and performance optimizations"""
    init_session_state()

    if not st.session_state.get("authenticated"):
        st.warning("🔒 Please log in to view your billing portal")
        st.stop()

    # Check if we're showing a payment modal
    if st.session_state.get("current_invoice"):
        show_payment_modal()
        return  # Stop rendering the rest of the page

    user_id = st.session_state.username  
    tenant_id = st.session_state.tenant_id

    # Page configuration
    st.set_page_config(
        page_title="My Billing Portal",
        layout="centered",
        page_icon="💳"
    )

    with st.container():
        st.title("💳 My Billing Portal")
        st.markdown("---")

    # Database connection and data loading
    with loading_spinner("Loading your billing information..."):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user ID
        cursor.execute("SELECT id FROM users WHERE username = %s", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            st.error("User not found")
            conn.close()
            st.stop()
        db_user_id = user_row[0]

        # Get tenant name if not in session state
        if 'tenant_name' not in st.session_state:
            st.session_state.tenant_name = get_tenant_name(cursor, tenant_id)

        # Get active subscription
        cursor.execute("""
            SELECT p.name, p.description, p.monthly_fee, p.included_units, 
                   p.overage_rate, s.start_date, p.billing_cycle
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.user_id = %s AND s.is_active
            ORDER BY s.start_date DESC LIMIT 1
        """, (db_user_id,))
        plan = cursor.fetchone()

    # Current Plan Section
    with st.container(border=True):
        st.subheader("📦 Current Subscription Plan")
        
        if not plan:
            st.warning("You don't have an active subscription")
            conn.close()
            return

        plan_name, description, monthly_fee, included_units, overage_rate, start_date, billing_cycle = plan
        
        # Plan details in columns
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Plan Name", plan_name)
            st.markdown(f"**Description:** {description or 'No description'}")
            st.markdown(f"**Billing Cycle:** {billing_cycle.capitalize()}")
            
        with col2:
            st.metric("Monthly Fee", f"R{monthly_fee:.2f}")
            st.markdown(f"**Included Units:** {included_units:,}")
            st.markdown(f"**Overage Rate:** R{overage_rate:.2f}/unit")
        
        st.caption(f"Plan active since: {start_date.strftime('%d %b %Y')}")

    st.divider()

    # Usage Metrics Section
    with st.container(border=True):
        st.subheader("📊 Current Period Usage")
        
        with loading_spinner("Loading usage data..."):
            cursor.execute("""
                SELECT m.name, SUM(u.usage_amount) as total_usage
                FROM usage_records u
                JOIN usage_metrics m ON u.metric_id = m.id
                WHERE u.user_id = %s AND u.tenant_id = %s
                AND u.usage_date BETWEEN date_trunc('month', CURRENT_DATE) AND CURRENT_DATE
                GROUP BY m.name
                ORDER BY m.name
            """, (db_user_id, tenant_id))
            usage_data = cursor.fetchall()

        if usage_data:
            for metric_type, total_usage in usage_data:
                overage = max(0, total_usage - included_units)
                progress = min(total_usage / included_units, 1) if included_units > 0 else 0
                
                st.write(f"**{metric_type}**")
                st.progress(progress)
                st.caption(f"{total_usage:,} of {included_units:,} units ({progress:.0%})")
                
                if overage > 0:
                    overage_cost = overage * overage_rate
                    st.warning(f"🔺 Overage: {overage:,} units (R{overage_cost:.2f})")
        else:
            st.info("No usage recorded for current period")

    st.divider()

    # Invoice History Section
    st.subheader("🧾 Invoice History")
    
    with loading_spinner("Loading invoices..."):
        cursor.execute("""
            SELECT id, invoice_date, total_amount, is_paid, period_start, period_end
            FROM invoices
            WHERE user_id = %s
            ORDER BY invoice_date DESC
            LIMIT 12
        """, (db_user_id,))
        invoices = cursor.fetchall()

    if not invoices:
        st.info("No invoices found")
    else:
        # Summary stats
        paid_count = sum(1 for inv in invoices if inv[3])
        total_owed = sum(inv[2] for inv in invoices if not inv[3])
        
        stat_cols = st.columns(3)
        stat_cols[0].metric("Total Invoices", len(invoices))
        stat_cols[1].metric("Paid Invoices", paid_count)
        stat_cols[2].metric("Amount Owed", f"R{total_owed:.2f}")

        # Invoice details
        for inv in invoices:
            inv_id, inv_date, amount, is_paid, period_start, period_end = inv
            
            with st.expander(f"Invoice #{inv_id} - {inv_date.strftime('%d %b %Y')}"):
                # Status badge
                status = st.empty()
                if is_paid:
                    status.success(f"✅ Paid - R{amount:.2f}")
                else:
                    status.error(f"❌ Unpaid - R{amount:.2f}")
                
                # Period info
                st.caption(f"Billing Period: {period_start.strftime('%d %b')} to {period_end.strftime('%d %b %Y')}")
                
                # Invoice items
                with loading_spinner("Loading invoice details..."):
                    _, items = get_invoice_summary(inv_id)
                
                if items:
                    st.write("**Invoice Items:**")
                    for item in items:
                        st.markdown(f"- {item['description']}: {item['quantity']} × R{item['unit_price']:.2f}")
                
                # Payment actions
                col1, col2 = st.columns([1,2])
                with col1:
                    if not is_paid:
                        if st.button("💳 Pay Now", key=f"pay_{inv_id}"):
                            st.session_state.current_invoice = inv_id
                            st.rerun()
                
                with col2:
                    # PDF download
                    client_info = {
                        "name": f"{st.session_state.user.get('first_name', '')} {st.session_state.user.get('last_name', '')}".strip(),
                        "email": st.session_state.user.get("email", "")
                    }
                    pdf_bytes = generate_invoice_pdf(
                        {
                            "id": inv_id,
                            "invoice_date": inv_date.strftime('%Y-%m-%d'),
                            "period_start": period_start.strftime('%Y-%m-%d'),
                            "period_end": period_end.strftime('%Y-%m-%d'),
                            "total_amount": amount
                        },
                        items or [],
                        tenant_info={"name": st.session_state.tenant_name},
                        client_info=client_info
)
                    st.download_button(
                        label="📄 Download PDF",
                        data=pdf_bytes,
                        file_name=f"invoice_{inv_id}.pdf",
                        mime="application/pdf",
                        key=f"dl_{inv_id}"
                    )

    conn.close()

def show_payment_modal():
    """Custom modal implementation for payment processing"""
    # Clear other content
    st.markdown("""
        <style>
            div[data-testid="stAppViewBlockContainer"] > div:first-child {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Modal content
    with st.container():
        st.markdown("---")
        st.subheader(f"💳 Payment for Invoice #{st.session_state.current_invoice}")
        
        # Display invoice summary
        conn = get_db_connection()
        cursor = conn.cursor()
        invoice, items = get_invoice_summary(st.session_state.current_invoice)
        
        if invoice:
            st.markdown(f"**Amount Due:** R{invoice['total_amount']:.2f}")
            st.markdown(f"**Due Date:** {invoice.get('due_date', 'N/A')}")
        
        # Payment form
        with st.form("payment_form"):
            amount = st.number_input(
                "Payment Amount",
                min_value=0.01,
                value=float(invoice['total_amount']) if invoice else 0.00,
                step=0.01
            )
            payment_method = st.selectbox(
                "Payment Method",
                ["Credit Card", "Bank Transfer", "Other"]
            )
            reference = st.text_input("Payment Reference")
            
            submitted = st.form_submit_button("Submit Payment")
            if submitted:
                try:
                    # Process payment (example - implement your actual payment processing)
                    cursor.execute("""
                        INSERT INTO payments (invoice_id, amount, payment_method, notes)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        st.session_state.current_invoice,
                        amount,
                        payment_method,
                        f"Reference: {reference}" if reference else None
                    ))
                    conn.commit()
                    show_toast("Payment processed successfully!", "success")
                    st.session_state.pop("current_invoice")
                    st.rerun()
                except Exception as e:
                    st.error(f"Payment failed: {str(e)}")
        
        if st.button("← Back to Invoices"):
            st.session_state.pop("current_invoice")
            st.rerun()
        
        st.markdown("---")
        conn.close()