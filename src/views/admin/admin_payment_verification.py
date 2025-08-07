import streamlit as st
from db.database import get_db_connection
from utils.session_guard import require_login
from pathlib import Path
from utils.email_utils import send_email

def admin_payment_verification():
    require_login('admin')
    
    st.set_page_config(page_title="🧾 Verify Payments", layout="wide")
    st.title("🧾 Payment Verification")

    user = st.session_state.get("user")
    tenant_id = user["tenant_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch pending payments for this tenant
    cursor.execute("""
        SELECT p.id, p.user_id, p.invoice_id, p.amount, p.payment_method,
               p.payment_date, p.receipt_path, u.username, i.invoice_date
        FROM payments p
        JOIN users u ON p.user_id = u.id
        JOIN invoices i ON p.invoice_id = i.id
        WHERE p.is_verified = 0
        AND u.tenant_id = ?
        ORDER BY p.payment_date DESC
    """, (tenant_id,))
    rows = cursor.fetchall()

    print(f"Found {len(rows)} pending payments for tenant {tenant_id}")
    if not rows:
        st.success("✅ No pending payments.")
        return

    for payment in rows:
        (pid, uid, invoice_id, amount, method, date, receipt_path, username, invoice_date) = payment

        st.subheader(f"💼 Invoice #{invoice_id} by {username} — R{amount:.2f}")

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"📅 Payment Date: `{date}`")
            st.write(f"💳 Method: `{method}`")
            st.write(f"🧾 Invoice Date: `{invoice_date}`")
        with col2:
            if receipt_path and Path(receipt_path).exists():
                with open(receipt_path, "rb") as f:
                    st.download_button("📥 Download Receipt", f, file_name=Path(receipt_path).name)
            else:
                st.error("❌ Receipt file not found")

        # Action buttons
        colA, colB = st.columns([1, 3])
        with colA:
            if st.button("✅ Verify", key=f"verify_{pid}"):
                try:
                    # Mark payment as verified
                    cursor.execute("UPDATE payments SET is_verified = 1 WHERE id = ?", (pid,))
                    # Mark invoice as paid
                    cursor.execute("UPDATE invoices SET is_paid = 1 WHERE id = ?", (invoice_id,))
                    conn.commit()
                    st.success(f"✅ Payment {pid} verified and invoice marked paid.")
                    # Fetch client email
                    cursor.execute("SELECT email FROM users WHERE id = ?", (uid,))
                    client_email = cursor.fetchone()[0]

                    # Send confirmation email
                    email_subject = f"💰 Payment Verified for Invoice #{invoice_id}"
                    email_body = f"""
                    Hello {username},

                    ✅ Your payment of R{amount:.2f} for Invoice #{invoice_id} dated {invoice_date} has been verified and marked as paid.

                    Thank you for your payment!

                    Regards,  
                    Billing Team @ {user["tenant_id"]}
                    """

                    send_email('siphiwolu@gmail.com', email_subject, email_body)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    conn.close()
