import streamlit as st
from db.database import get_db_connection
from utils.session import init_session_state
from billing_engine import get_invoice_summary, generate_invoice_for_user
from utils.pdf_utils import generate_invoice_pdf


def get_tenant_info(cursor, tenant_id):
    cursor.execute("SELECT name, address, email, phone FROM tenants WHERE id = ?", (tenant_id,))
    row = cursor.fetchone()
    if row:
        return {
            "name": row[0],
            "address": row[1],
            "email": row[2],
            "phone": row[3],
        }
    return {}

def get_client_info(cursor, user_id):
    cursor.execute("""
        SELECT first_name || ' ' || last_name AS name, company_name AS address, email
        FROM users WHERE id = ?
    """, (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            "name": row[0],
            "address": row[1],
            "email": row[2]
        }
    return {}

def get_user_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (user_id,))
    user_row = cursor.fetchone()
    conn.close()
    return user_row[0] if user_row else None
    
def get_payment_history(invoice_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT amount, payment_date, payment_method, notes
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

    user_id = st.session_state.username  
    tenant_id = st.session_state.tenant_id

    st.subheader("📦 My Current Plan & Billing Summary")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch active subscription and plan
    cursor.execute("""
        SELECT p.name, p.description, p.monthly_fee, p.included_units, p.overage_rate, s.start_date
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.user_id = ? AND s.is_active = 1
        ORDER BY s.start_date DESC LIMIT 1
    """, (get_user_id(user_id),))
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
        SELECT metric_name, SUM(usage_amount) as total_usage
        FROM usage_records
        WHERE user_id = ? AND tenant_id = ?
        GROUP BY metric_name
        ORDER BY metric_name
    """, (get_user_id(user_id), tenant_id))
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
    """, (get_user_id(user_id),))
    invoice_rows = cursor.fetchall()

    client_info = get_client_info(cursor=cursor, user_id=user_id)
    tenant_info = get_tenant_info(cursor=cursor, tenant_id=tenant_id)
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


    conn.close()
