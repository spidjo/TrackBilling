# src/views/client_usage_dashboard.py

import streamlit as st
from datetime import datetime
import os
import pandas as pd
from utils.session_guard import require_login
from db.database import get_db_connection
from billing_engine import estimate_invoice_for_user, finalize_invoice_for_user, get_client_info, get_tenant_info
from utils.pdf_utils import generate_invoice_pdf


def get_user_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (user_id,))
    user_row = cursor.fetchone()
    conn.close()
    return user_row[0] if user_row else None

def client_usage_dashboard():
    st.set_page_config(page_title="Usage Dashboard", layout="wide")
    require_login("client")

    user = st.session_state.get("user")
    if not user:
        st.stop()
 
    st.title("📊 My Usage Dashboard")

    conn = get_db_connection()
    cursor = conn.cursor()

    user_id = st.session_state.username 
    tenant_id = st.session_state.tenant_id

    # --- Fetch active subscription ---
    cursor.execute("""
        SELECT plan_id FROM subscriptions 
        WHERE user_id = ? AND is_active = 1
    """, (get_user_id(user_id),))
    row = cursor.fetchone()
    if not row:
        st.warning("No active subscription found.")
        conn.close()
        return

    plan_id = row[0]

    # --- Fetch plan metric limits ---
    cursor.execute("""
        SELECT um.name, pml.metric_limit
        FROM plan_metric_limits pml
        JOIN usage_metrics um ON pml.metric_id = um.id
        WHERE pml.plan_id = ?
    """, (plan_id,))
    limits = dict(cursor.fetchall())

    if not limits:
        st.warning(f"Your plan has no metric limits defined.")
        conn.close()
        return

    # --- Fetch usage for current month ---
    current_month = datetime.utcnow().strftime('%Y-%m')
    cursor.execute("""
        SELECT metric_name, SUM(usage_amount)
        FROM usage_records
        WHERE user_id = ?
          AND strftime('%Y-%m', usage_date) = ?
        GROUP BY metric_name
    """, (get_user_id(user_id), current_month))
    usage = dict(cursor.fetchall())

    # --- Display usage per metric ---
    for metric_name, limit in limits.items():
        used = usage.get(metric_name, 0)
        percent_used = min(int((used / limit) * 100), 100) if limit else 0

        st.subheader(f"🔹 {metric_name}")
        col1, col2 = st.columns([4, 1])

        with col1:
            st.progress(percent_used, text=f"{used} of {limit} {metric_name.lower()} used")

        with col2:
            if used > limit:
                st.error(f"Over by {used - limit}")
            else:
                st.success("Within limits")

    st.markdown("---")
    st.markdown("## 📄 Invoice Preview")

    st.subheader("💳 Invoice & Payment History")

    cursor.execute("""
        SELECT i.id, i.period_start, i.period_end, i.total_amount, 
            IFNULL(p.amount, 0), IFNULL(p.payment_date, '-'), 
            CASE 
                WHEN p.is_verified = 1 THEN '✅ Verified'
                WHEN p.id IS NOT NULL THEN '⏳ Pending Verification'
                ELSE '❌ Unpaid'
            END as status
        FROM invoices i
        LEFT JOIN payments p ON i.id = p.invoice_id
        WHERE i.user_id = ?
        ORDER BY i.period_start DESC
    """, (get_user_id(user_id),))

    rows = cursor.fetchall()

    if rows:
        df = pd.DataFrame(rows, columns=[
            "Invoice ID", "Period Start", "Period End", "Amount",
            "Paid Amount", "Payment Date", "Status"
        ])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No invoice or payment records found.")

    # --- Estimate invoice ---
    items, estimated_total = estimate_invoice_for_user(get_user_id(user_id), tenant_id)

    if not items:
        st.info("No invoice data available. Make sure you're subscribed and have usage records.")
        conn.close()
        return

    # --- Breakdown ---
    st.write("### Breakdown")
    for item in items:
        st.write(f"- **{item['description']}**: {item['quantity']} × R{item['unit_price']:.2f} = R{item['total_price']:.2f}")

    st.markdown(f"### 💰 Estimated Total: R{estimated_total:.2f}")

    # --- Generate PDF preview ---
    fake_invoice = {
        "id": 0,
        "invoice_date": datetime.now().strftime("%Y-%m-%d"),
        "period_start": datetime.now().replace(day=1).strftime("%Y-%m-%d"),
        "period_end": datetime.now().strftime("%Y-%m-%d"),
        "total_amount": estimated_total,
        "is_paid": 0
    }

    client_info = get_client_info(cursor, user_id)
    tenant_info = get_tenant_info(cursor, tenant_id)
    logo_path = f"assets/logos/{tenant_id}.png" if os.path.exists(f"assets/logos/{tenant_id}.png") else None

    pdf_bytes = generate_invoice_pdf(fake_invoice, items, tenant_info, client_info, logo_path)

    st.download_button(
        label="📥 Download PDF Preview",
        data=pdf_bytes,
        file_name=f"invoice_preview_{user_id}.pdf",
        mime="application/pdf"
    )

    # --- Finalize invoice ---
    if st.button("💳 Bill Now"):
        success, result = finalize_invoice_for_user(get_user_id(user_id), user["tenant_id"])
        if success:
            st.success(f"✅ Invoice #{result} created successfully.")
            st.rerun()
        else:
            st.error(f"❌ {result}")

    conn.close()
