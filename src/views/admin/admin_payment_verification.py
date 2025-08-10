import streamlit as st
from db.database import get_db_connection
from utils.session_guard import require_login
from pathlib import Path
from utils.email_utils import send_email
from datetime import datetime

def admin_payment_verification():
    require_login('admin')
    
    st.set_page_config(
        page_title="🧾 Verify Payments", 
        layout="wide",
        page_icon="🧾"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
        .payment-card {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .verified-badge {
            background-color: #4CAF50;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
        }
    </style>
    """, unsafe_allow_html=True)

    user = st.session_state.get("user")
    tenant_id = user["tenant_id"]

    st.title("🧾 Payment Verification")
    st.caption("Review and verify pending payments from your tenants")

    # Status filter
    status_filter = st.radio(
        "Filter payments:",
        ["Pending Only", "All Payments"],
        horizontal=True,
        index=0
    )

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch payments based on filter
    query = """
        SELECT p.id, p.user_id, p.invoice_id, p.amount, p.payment_method,
               p.payment_date, p.receipt_path, u.username, i.invoice_date, p.is_verified
        FROM payments p
        JOIN users u ON p.user_id = u.id
        JOIN invoices i ON p.invoice_id = i.id
        WHERE u.tenant_id = %s
        {filter_condition}
        ORDER BY p.payment_date DESC
    """.format(
        filter_condition="AND p.is_verified = False" if status_filter == "Pending Only" else ""
    )

    cursor.execute(query, (tenant_id,))
    rows = cursor.fetchall()

    if not rows:
        st.success("✨ No payments found matching your criteria")
        conn.close()
        return

    st.info(f"Found {len(rows)} {'pending' if status_filter == 'Pending Only' else ''} payments")

    for payment in rows:
        (pid, uid, invoice_id, amount, method, date, receipt_path, username, invoice_date, is_verified) = payment

        with st.container():
            st.markdown(f"<div class='payment-card'>", unsafe_allow_html=True)
            
            col_header, col_status = st.columns([4, 1])
            with col_header:
                st.subheader(f"💼 Invoice #{invoice_id}")
            with col_status:
                if is_verified:
                    st.markdown("<span class='verified-badge'>✅ Verified</span>", unsafe_allow_html=True)

            # Payment details
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.metric("Amount", f"R{amount:.2f}")
                st.caption(f"Method: {method}")
            with col2:
                st.caption(f"👤 User: {username}")
                st.caption(f"📅 Invoice Date: {invoice_date.strftime('%Y-%m-%d')}")
                st.caption(f"⏰ Payment Date: {date.strftime('%Y-%m-%d %H:%M')}")
            with col3:
                if receipt_path and Path(receipt_path).exists():
                    with open(receipt_path, "rb") as f:
                        st.download_button(
                            "📥 Download Receipt", 
                            f, 
                            file_name=f"receipt_{invoice_id}_{Path(receipt_path).name}",
                            use_container_width=True
                        )
                else:
                    st.warning("Receipt missing")

            # Action buttons
            if not is_verified:
                col_verify, _ = st.columns([1, 3])
                with col_verify:
                    if st.button(
                        "✅ Verify Payment", 
                        key=f"verify_{pid}",
                        type="primary",
                        use_container_width=True
                    ):
                        try:
                            with st.spinner("Processing verification..."):
                                # Update payment status
                                cursor.execute(
                                    "UPDATE payments SET is_verified = TRUE, verified_at = %s WHERE id = %s",
                                    (datetime.now(), pid)
                                )
                                # Update invoice status
                                cursor.execute(
                                    "UPDATE invoices SET is_paid = TRUE, paid_at = %s WHERE id = %s",
                                    (datetime.now(), invoice_id)
                                )
                                conn.commit()

                                # Get user email
                                cursor.execute("SELECT email FROM users WHERE id = %s", (uid,))
                                client_email = cursor.fetchone()[0]

                                # Send confirmation email using the new utility function
                                success = send_payment_verified_email(
                                    to_email=client_email,
                                    username=username,
                                    amount=amount,
                                    invoice_id=invoice_id,
                                    invoice_date=invoice_date.strftime('%Y-%m-%d'),
                                    tenant_name=user["tenant_id"]
                                )

                                if success:
                                    st.toast(f"✅ Payment verified and confirmation sent to {client_email}", icon="✅")
                                    st.rerun()
                                else:
                                    st.error("Failed to send confirmation email")
                        except Exception as e:
                            st.error(f"Error verifying payment: {str(e)}")
                            conn.rollback()

            st.markdown("</div>", unsafe_allow_html=True)

    conn.close()