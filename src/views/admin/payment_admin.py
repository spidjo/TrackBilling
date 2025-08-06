
import streamlit as st
from payment_logic import record_payment
from db.database import get_db_connection

def payment_admin():
    st.subheader("💳 Record Manual Payment")

    conn = get_db_connection()
    cursor = conn.cursor()
    invoices = cursor.execute("""
        SELECT id, tenant_id, invoice_date, total_amount, case when is_paid = 1 then 'Paid' else 'Unpaid' end as status
        FROM invoices
        WHERE status != 'paid'
        ORDER BY invoice_date DESC
    """).fetchall()
    conn.close()

    if not invoices:
        st.info("No unpaid invoices.")
        return

    options = {f"Invoice {i[0]} – {i[2]} (R{i[3]})": i[0] for i in invoices}
    selected = st.selectbox("Select Unpaid Invoice", list(options.keys()))
    selected_invoice_id = options[selected]

    amount = st.number_input("Amount Paid", min_value=0.0, step=1.0)
    method = st.selectbox("Payment Method", ["manual", "eft", "credit_card"])
    notes = st.text_area("Notes (optional)")

    if st.button("💾 Record Payment"):
        record_payment(selected_invoice_id, amount, method, notes)
        st.success("✅ Payment recorded.")
        st.rerun()
