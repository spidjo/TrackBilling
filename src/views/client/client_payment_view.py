# src/views/client_payment_view.py

import streamlit as st
import os
from datetime import datetime
from db.database import get_db_connection
from utils.session_guard import require_login
from pathlib import Path

def client_payment_view():
    st.set_page_config(page_title="💰 My Payments", layout="wide")
    require_login('client')

    user = st.session_state.get("user")
    if not user:
        st.stop()

    user_id = st.session_state.username
    st.title("💳 My Payments")

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Get unpaid invoices
    cursor.execute("""
        SELECT id, invoice_date, total_amount
        FROM invoices
        WHERE user_id = ? AND is_paid = 0
        ORDER BY invoice_date DESC
    """, (user_id,))
    invoices = cursor.fetchall()

    if not invoices:
        st.info("🎉 No unpaid invoices found.")
        return

    for invoice_id, invoice_date, amount in invoices:
        st.subheader(f"🧾 Invoice #{invoice_id} — {invoice_date} — R{amount:.2f}")

        with st.expander("💸 Submit Payment"):
            with st.form(f"payment_form_{invoice_id}", clear_on_submit=True):
                payment_method = st.selectbox("Payment Method", ["Bank Transfer", "EFT", "Other"])
                payment_date = st.date_input("Payment Date", datetime.today())
                receipt_file = st.file_uploader("Upload Proof (PDF/Image)", type=["pdf", "png", "jpg"])
                submitted = st.form_submit_button("Submit Payment")

                if submitted:
                    if not receipt_file:
                        st.warning("📎 Please upload a receipt.")
                    else:
                        # Save file
                        save_dir = Path("uploaded_receipts")
                        save_dir.mkdir(exist_ok=True)
                        filename = f"receipt_{invoice_id}_{user['id']}_{receipt_file.name}"
                        file_path = save_dir / filename

                        with open(file_path, "wb") as f:
                            f.write(receipt_file.read())

                        # Insert payment record
                        cursor.execute("""
                            INSERT INTO payments (user_id, invoice_id, amount, payment_date, payment_method, receipt_path, is_verified)
                            VALUES (?, ?, ?, ?, ?, ?, 0)
                        """, (
                            user["id"],
                            invoice_id,
                            amount,
                            payment_date.strftime("%Y-%m-%d"),
                            payment_method,
                            str(file_path)
                        ))

                        conn.commit()
                        st.success("✅ Payment submitted and pending verification.")

    conn.close()
