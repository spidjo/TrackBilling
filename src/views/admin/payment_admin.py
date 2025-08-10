import streamlit as st
from datetime import datetime
from payment_logic import record_payment
from db.database import get_db_connection

def payment_admin():
    st.set_page_config(page_title="💳 Payment Admin", layout="centered")
    st.title("💳 Payment Administration")
    
    # Custom styling
    st.markdown("""
    <style>
        .invoice-card {
            border-left: 4px solid #4CAF50;
            padding: 1rem;
            margin: 0.5rem 0;
            background-color: #f8f9fa;
            border-radius: 0 8px 8px 0;
        }
        .paid-badge {
            background-color: #4CAF50;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            display: inline-block;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.expander("➕ Record Manual Payment", expanded=True):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get unpaid invoices with more details
        cursor.execute("""
            SELECT i.id, i.tenant_id, i.invoice_date, i.total_amount, 
                   t.name as tenant_name, u.username
            FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            JOIN users u ON i.user_id = u.id
            WHERE i.is_paid = False
            ORDER BY i.invoice_date DESC
            LIMIT 50
        """)
        invoices = cursor.fetchall()
        conn.close()

        if not invoices:
            st.success("🎉 All invoices are paid!")
            return

        # Improved invoice selection
        st.subheader("Select Invoice", divider="gray")
        selected_invoice = st.selectbox(
            "Unpaid Invoices",
            invoices,
            format_func=lambda x: f"Invoice #{x[0]} • {x[4]} • R{x[3]:.2f} • {x[2].strftime('%Y-%m-%d') if x[2] else 'No date'} • {x[5]}",
            help="Select an invoice to record payment for"
        )
        selected_invoice_id = selected_invoice[0]
        
        # Display invoice summary with null checks
        with st.container(border=True):
            cols = st.columns([1,1,1])
            with cols[0]:
                st.metric("Invoice Amount", f"R{selected_invoice[3]:.2f}")
            with cols[1]:
                st.metric("Tenant", selected_invoice[4])
            with cols[2]:
                invoice_date = selected_invoice[2]
                display_date = invoice_date.strftime('%Y-%m-%d') if invoice_date else "No date"
                st.metric("Issued On", display_date)
        
        # Payment details form
        st.subheader("Payment Details", divider="gray")
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input(
                "Amount Paid", 
                min_value=0.0, 
                value=float(selected_invoice[3]),
                step=0.01,
                format="%.2f",
                help="Enter the actual amount received"
            )
        with col2:
            method = st.selectbox(
                "Payment Method",
                ["Bank Transfer", "Credit Card", "Cash", "Other"],
                index=0,
                help="Select payment method used"
            )
        
        notes = st.text_area(
            "Payment Notes",
            placeholder="Enter any payment reference or notes...",
            help="Optional payment details or reference"
        )
        
        # Form submission
        if st.button(
            "💾 Record Payment",
            type="primary",
            use_container_width=True,
            help="Save this payment record"
        ):
            if amount <= 0:
                st.error("Amount must be greater than zero")
            else:
                with st.spinner("Recording payment..."):
                    try:
                        record_payment(
                            selected_invoice_id, 
                            amount, 
                            method.lower().replace(" ", "_"), 
                            notes
                        )
                        st.toast("✅ Payment recorded successfully", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error recording payment: {str(e)}")

    # Recent payments section with null checks
    with st.expander("📋 Recent Payment History", expanded=False):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.amount, p.payment_method, p.payment_date, 
                   i.id as invoice_id, t.name as tenant_name
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            JOIN tenants t ON i.tenant_id = t.id
            ORDER BY p.payment_date DESC
            LIMIT 10
        """)
        recent_payments = cursor.fetchall()
        conn.close()
        
        if recent_payments:
            for payment in recent_payments:
                with st.container():
                    cols = st.columns([1,2,1,1])
                    with cols[0]:
                        st.markdown(f"**#{payment[4]}**")
                    with cols[1]:
                        st.markdown(f"{payment[5]}")
                    with cols[2]:
                        st.markdown(f"R{payment[1]:.2f}")
                    with cols[3]:
                        payment_date = payment[3]
                        display_date = payment_date.strftime('%Y-%m-%d') if payment_date else "No date"
                        st.markdown(display_date)
                    st.caption(f"Method: {payment[2].replace('_', ' ').title()}")
                    st.divider()
        else:
            st.info("No recent payments found")