import streamlit as st
from datetime import datetime
from billing_engine import generate_invoices  
from database import get_db_connection

def billing_admin():
    st.subheader("🧾 Billing Admin")

    if st.session_state.get("role") != "admin" and st.session_state.get("role") != "superadmin":
        st.warning("Access denied. Admins only.")
        st.stop()

    tenant_id = st.session_state.get("tenant_id")
    now = datetime.now()
    default_period = now.strftime("%Y-%m")

    st.markdown("### 📅 Generate Invoices")
    billing_period = st.text_input("Billing Period (YYYY-MM)", value=default_period)
    
    if st.button("Generate Invoices for Current Tenant"):
        try:
            invoice_ids = generate_invoices(tenant_id, billing_period)  # corrected function
            if isinstance(invoice_ids, (list, tuple, set)) and invoice_ids:
                st.success(f"✅ Generated {len(invoice_ids)} invoice(s).")
            elif isinstance(invoice_ids, list) and not invoice_ids:
                st.warning("ℹ️ No active subscriptions or usage found.")
            else:
                st.success(f"✅ Invoices generated.")
        except Exception as e:
            st.error(f"❌ Failed to generate invoices: {str(e)}")

    st.divider()
    st.markdown("### 💵 Recent Invoices")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, invoice_date, total_amount, case when is_paid = 1 then 'Paid' else 'Unpaid' end as status, created_at
        FROM invoices
        WHERE tenant_id = ?
        ORDER BY created_at DESC
        LIMIT 10
    """, (tenant_id,))
    rows = cursor.fetchall()
    conn.close()

    if rows:
        for inv in rows:
            st.markdown(f"- **Invoice #{inv[0]}** | {inv[1]} | 💰 R{inv[2]:.2f} | Status: `{inv[3]}` | 🕒 {inv[4]}")
    else:
        st.info("No invoices yet.")
