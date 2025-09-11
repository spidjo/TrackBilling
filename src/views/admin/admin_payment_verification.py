import streamlit as st
from db.database import get_db_connection
from utils.session import init_session_state, validate_session
from pathlib import Path
from utils.email_utils import send_email, send_payment_verified_email
from datetime import datetime
import pandas as pd


def get_tenant_name(tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM tenants WHERE id = %s", (tenant_id,))
    tenant = cursor.fetchone()
    conn.close()
    return tenant["name"] if tenant else "Unknown Tenant"

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"
    
def admin_payment_verification():
    init_session_state()
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()

    st.set_page_config(
        page_title="🧾 Verify Payments", 
        layout="wide",
        page_icon="🧾"
    )
    
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
        
        .payment-card {
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            background-color: white;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            transition: all 0.3s ease;
            border-top: 4px solid var(--info);
        }
        .payment-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
        }
        
        .verified-badge {
            background-color: var(--secondary);
            color: white;
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .pending-badge {
            background-color: var(--warning);
            color: white;
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
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

    tenant_id = st.session_state.tenant_id

    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">🧾 Payment Verification</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    st.caption("Review and verify pending payments from your tenants")

    # Status filter
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        status_filter = st.radio(
            "Filter payments:",
            ["Pending Only", "All Payments"],
            horizontal=True,
            index=0
        )
    
    with col3:
        # Summary stats
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get payment stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_payments,
                SUM(CASE WHEN p.is_verified = TRUE THEN 1 ELSE 0 END) as verified_count,
                SUM(CASE WHEN p.is_verified = FALSE THEN 1 ELSE 0 END) as pending_count
            FROM payments p
            JOIN users u ON p.user_id = u.id
            WHERE u.tenant_id = %s
        """, (tenant_id,))
        
        stats = cursor.fetchone()
        total_payments = stats["total_payments"] if stats else 0
        verified_count = stats["verified_count"] if stats else 0
        pending_count = stats["pending_count"] if stats else 0
        
        st.markdown(f"""
        <div style="display: flex; gap: 1rem; justify-content: flex-end;">
            <div style="text-align: center;">
                <div style="font-size: 0.9rem; color: #6B7280;">Total</div>
                <div style="font-size: 1.2rem; font-weight: bold;">{total_payments}</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 0.9rem; color: #6B7280;">Verified</div>
                <div style="font-size: 1.2rem; font-weight: bold; color: #10B981;">{verified_count}</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 0.9rem; color: #6B7280;">Pending</div>
                <div style="font-size: 1.2rem; font-weight: bold; color: #F59E0B;">{pending_count}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Fetch payments based on filter
    query = """
        SELECT p.id, p.user_id, p.invoice_id, p.amount, p.payment_method,
               p.payment_date, p.receipt_path, u.username, i.invoice_date, p.is_verified,
               p.verified_at, u.email
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

    # Display payments in a more organized way
    for payment in rows:
        (pid, uid, invoice_id, amount, method, date, receipt_path, username, 
         invoice_date, is_verified, verified_at, user_email) = payment

        with st.container():
            st.markdown(f"<div class='payment-card'>", unsafe_allow_html=True)
            
            col_header, col_status = st.columns([4, 1])
            with col_header:
                st.subheader(f"💼 Invoice #{invoice_id}")
                st.caption(f"Payment ID: {pid}")
            with col_status:
                if is_verified:
                    st.markdown("<span class='verified-badge'>✅ Verified</span>", unsafe_allow_html=True)
                    if verified_at:
                        st.caption(f"on {verified_at.strftime('%Y-%m-%d %H:%M')}")
                else:
                    st.markdown("<span class='pending-badge'>⏳ Pending</span>", unsafe_allow_html=True)

            # Payment details
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.metric("Amount", format_currency(amount))
                st.caption(f"Method: {method}")
            with col2:
                st.caption(f"👤 User: {username}")
                st.caption(f"📧 Email: {user_email}")
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

                                # Send confirmation email using the new utility function
                                success = send_payment_verified_email(
                                    to_email=user_email,
                                    username=username,
                                    amount=amount,
                                    invoice_id=invoice_id,
                                    invoice_date=invoice_date.strftime('%Y-%m-%d'),
                                    tenant_name=get_tenant_name(tenant_id)
                                )

                                if success:
                                    st.toast(f"✅ Payment verified and confirmation sent to {user_email}", icon="✅")
                                    st.rerun()
                                else:
                                    st.error("Failed to send confirmation email")
                        except Exception as e:
                            st.error(f"Error verifying payment: {str(e)}")
                            conn.rollback()

            st.markdown("</div>", unsafe_allow_html=True)

    conn.close()

if __name__ == "__main__":
    admin_payment_verification()