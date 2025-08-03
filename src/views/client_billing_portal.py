import streamlit as st
from database import get_db_connection
from session import init_session_state
from billing_engine import get_invoice_summary
from utils.pdf_utils import generate_invoice_pdf

def get_payment_history(invoice_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT amount_paid, payment_date, payment_method, notes
        FROM payments
        WHERE invoice_id = ?
        ORDER BY payment_date DESC
    """, (invoice_id,))
    history = cursor.fetchall()
    conn.close()
    return history

def client_billing_portal():
    init_session_state()

    if not st.session_state.get("authenticated"):
        st.warning("🔒 Please log in to view your billing portal.")
        st.stop()

    user_id = st.session_state.username  # assuming username maps to user_id in your logic
    tenant_id = st.session_state.tenant_id

    st.subheader("📦 My Current Plan & Billing Summary")

    conn = get_db_connection()
    cursor = conn.cursor()

    tenant_info = {
        "name": "MzansiTel Communications",
        "address": "123 Tech Road, Cape Town, South Africa",
        "email": "billing@mzansitel.co.za",
        "phone": "+27 11 123 4567"
    }

    client_info = {
        "name": "John Doe",
        "address": "456 Client St, Johannesburg",
        "email": "john.doe@example.com"
    }
    # 1. Fetch active subscription and plan
    cursor.execute("""
        SELECT p.name, p.description, p.monthly_fee, p.included_units, p.overage_rate, s.start_date
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.user_id = ? AND s.is_active = 1
        ORDER BY s.start_date DESC LIMIT 1
    """, (user_id,))
    plan = cursor.fetchone()

    if not plan:
        st.warning("🚫 You are not currently subscribed to any plan.")
        conn.close()
        return

    plan_name, description, monthly_fee, included_units, overage_rate, start_date = plan

    st.markdown(f"**Plan Name:** `{plan_name}`")
    st.markdown(f"**Description:** {description or '_No description_'}")
    st.markdown(f"**Monthly Fee:** `${monthly_fee:.2f}`")
    st.markdown(f"**Included Units:** {included_units}")
    st.markdown(f"**Overage Rate:** `${overage_rate:.2f}` per unit overage")
    st.markdown(f"**Start Date:** {start_date}")

    st.divider()

    # 2. Show usage metrics
    st.subheader("📊 Recent Usage")
    cursor.execute("""
        SELECT metric_type, SUM(quantity) as total_usage
        FROM usage_metrics
        WHERE user_id = ? AND tenant_id = ?
        GROUP BY metric_type
        ORDER BY metric_type
    """, (user_id, tenant_id))
    usage_data = cursor.fetchall()

    if usage_data:
        for metric_type, total_usage in usage_data:
            overage = max(0, total_usage - included_units)
            overage_cost = overage * overage_rate
            st.markdown(f"- **{metric_type}**: {total_usage} used")
            if overage > 0:
                st.markdown(f"  - 🔺 *Overage*: {overage} units → `${overage_cost:.2f}`")
            else:
                st.markdown("  - ✅ Within included units.")
    else:
        st.info("No usage has been recorded yet.")

    st.divider()

    # 3. Show all invoices for this user
    st.subheader("🧾 Invoice History")

    cursor.execute("""
        SELECT id
        FROM invoices
        WHERE user_id = ?
        ORDER BY invoice_date DESC
    """, (user_id,))
    invoice_rows = cursor.fetchall()

    if not invoice_rows:
        st.info("No invoices found.")
    else:
        for invoice_row in invoice_rows:
            invoice_id = invoice_row[0]
            invoice, items = get_invoice_summary(invoice_id)

            with st.expander(f"📄 Invoice #{invoice_id} - {invoice['invoice_date']}"):
                st.markdown(f"**Status:** {invoice['is_paid'] and '✅ Paid' or '❌ Unpaid'}")
                st.markdown(f"**Total Amount:** R{invoice['total_amount']:.2f}")

                st.markdown("**📦 Invoice Items:**")
                for item in items:
                    st.markdown(f"- {item['description']}: {item['quantity']} × R{item['unit_price']:.2f}")

                # PDF Download
                pdf_bytes = generate_invoice_pdf(
                            invoice, items,
                            tenant_info=tenant_info,
                            client_info=client_info,
                            logo_path="src/assets/logo.png"
                            
                        )
                st.download_button(
                    label=f"📥 Download Invoice #{invoice['id']} as PDF",
                    data=pdf_bytes,
                    file_name=f"invoice_{invoice['id']}.pdf",
                    mime="application/pdf",
                    key=f"download_{invoice['id']}"
                )

                # Payment history
                st.markdown("**💳 Payment History:**")
                payments = get_payment_history(invoice_id)
                if payments:
                    for amt, date, payment_method, note in payments:
                        st.markdown(f"- R{amt:.2f} on `{date}` via `{payment_method}`" + (f" – _{note}_" if note else ""))
                else:
                    st.info("No payments recorded for this invoice.")

            
    # 3. Placeholder for invoice history
    st.subheader("🧾 Invoice History")
    st.info("Invoice records not implemented yet.")

    conn.close()
