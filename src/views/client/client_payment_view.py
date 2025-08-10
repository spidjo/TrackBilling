# src/views/client_payment_view.py
import streamlit as st
from datetime import datetime
from pathlib import Path
from db.database import get_db_connection
from utils.session_guard import require_login
from utils.ui_helpers import loading_spinner, show_toast

def client_payment_view():
    """Client payment portal with enhanced UX and performance optimizations"""
    # Page configuration
    st.set_page_config(
        page_title="My Payments",
        layout="wide",
        page_icon="💳"
    )
    require_login('client')

    if not st.session_state.get("user"):
        st.stop()

    # Initialize session state
    if 'refresh_data' not in st.session_state:
        st.session_state.refresh_data = False

    # UI Header
    with st.container():
        st.title("💳 My Payments")
        st.markdown("---")

    # Main content with loading spinner
    with loading_spinner("Loading payment information..."):
        conn = get_db_connection()
        cursor = conn.cursor()

        user_id = st.session_state.username
        db_user_id = get_user_id(user_id)

        if not db_user_id:
            st.error("User not found")
            conn.close()
            return

        # --- Unpaid Invoices Section ---
        st.subheader("📄 Unpaid Invoices", divider="gray")
        
        cursor.execute("""
            SELECT 
                i.id, 
                i.invoice_date, 
                i.total_amount,
                i.period_start,
                i.period_end,
                COALESCE(SUM(p.amount), 0) as paid_amount
            FROM invoices i
            LEFT JOIN payments p ON i.id = p.invoice_id
            WHERE i.user_id = %s AND i.is_paid = False
            GROUP BY i.id
            ORDER BY i.invoice_date DESC
        """, (db_user_id,))
        
        invoices = cursor.fetchall()

        if not invoices:
            st.success("🎉 You have no unpaid invoices!")
            conn.close()
            return

        # Display invoices in tabs for better organization
        tab_labels = [f"Invoice #{inv[0]} ({inv[1].strftime('%b %Y')})" for inv in invoices]
        tabs = st.tabs(tab_labels)

        for idx, (invoice_id, invoice_date, amount, period_start, period_end, paid_amount) in enumerate(invoices):
            with tabs[idx]:
                with st.container(border=True):
                    # Invoice summary
                    col1, col2, col3 = st.columns([2,1,1])
                    with col1:
                        st.markdown(f"**Invoice #** {invoice_id}")
                        st.caption(f"**Period:** {period_start.strftime('%b %d')} - {period_end.strftime('%b %d, %Y')}")
                    with col2:
                        st.metric("Total Amount", f"R{amount:.2f}")
                    with col3:
                        st.metric("Amount Paid", f"R{paid_amount:.2f}")

                    # Payment form
                    with st.expander("💸 Submit Payment", expanded=True):
                        with st.form(f"payment_form_{invoice_id}", clear_on_submit=True):
                            st.markdown("#### Payment Details")
                            
                            # Form columns
                            col1, col2 = st.columns(2)
                            with col1:
                                payment_method = st.selectbox(
                                    "Payment Method",
                                    ["Bank Transfer", "Credit Card", "EFT", "Other"],
                                    key=f"method_{invoice_id}"
                                )
                                payment_date = st.date_input(
                                    "Payment Date",
                                    datetime.today(),
                                    key=f"date_{invoice_id}"
                                )
                            with col2:
                                amount_paid = st.number_input(
                                    "Amount Paid",
                                    min_value=0.01,
                                    max_value=float(amount),
                                    value=float(amount),
                                    step=0.01,
                                    key=f"amount_{invoice_id}"
                                )
                                receipt_file = st.file_uploader(
                                    "Upload Proof (PDF/Image)",
                                    type=["pdf", "png", "jpg", "jpeg"],
                                    key=f"receipt_{invoice_id}"
                                )

                            # Form submission
                            submitted = st.form_submit_button(
                                "Submit Payment",
                                type="primary",
                                use_container_width=True
                            )

                            if submitted:
                                if not receipt_file:
                                    show_toast("Please upload a receipt", "warning")
                                else:
                                    try:
                                        # Save receipt file
                                        save_dir = Path("uploaded_receipts")
                                        save_dir.mkdir(exist_ok=True)
                                        filename = f"receipt_{invoice_id}_{user_id}_{datetime.now().timestamp()}.{receipt_file.name.split('.')[-1]}"
                                        file_path = save_dir / filename

                                        with open(file_path, "wb") as f:
                                            f.write(receipt_file.getbuffer())

                                        # Record payment
                                        cursor.execute("""
                                            INSERT INTO payments (
                                                user_id, 
                                                invoice_id, 
                                                amount, 
                                                payment_date, 
                                                payment_method, 
                                                receipt_path, 
                                                is_verified,
                                                notes
                                            )
                                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                        """, (
                                            db_user_id,
                                            invoice_id,
                                            amount_paid,
                                            payment_date.strftime("%Y-%m-%d"),
                                            payment_method,
                                            str(file_path),
                                            False,
                                            f"Payment submitted via client portal on {datetime.now().strftime('%Y-%m-%d')}"
                                        ))

                                        # Update invoice status if fully paid
                                        if amount_paid >= amount:
                                            cursor.execute("""
                                                UPDATE invoices
                                                SET is_paid = True
                                                WHERE id = %s
                                            """, (invoice_id,))

                                        conn.commit()
                                        show_toast("Payment submitted successfully! Pending verification.", "success")
                                        st.session_state.refresh_data = True
                                        st.rerun()

                                    except Exception as e:
                                        conn.rollback()
                                        show_toast(f"Payment failed: {str(e)}", "error")

        # --- Payment History Section ---
        st.divider()
        st.subheader("📋 Payment History", divider="gray")
        
        cursor.execute("""
            SELECT 
                p.id,
                p.invoice_id,
                p.amount,
                p.payment_date,
                p.payment_method,
                p.is_verified,
                p.notes
            FROM payments p
            WHERE p.user_id = %s
            ORDER BY p.payment_date DESC
            LIMIT 10
        """, (db_user_id,))
        
        payments = cursor.fetchall()

        if payments:
            # Convert to dataframe for better display
            df = pd.DataFrame(payments, columns=[
                "ID", "Invoice #", "Amount", "Date", "Method", "Verified", "Notes"
            ])
            
            # Format columns
            df['Amount'] = df['Amount'].apply(lambda x: f"R{x:.2f}")
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            df['Status'] = df['Verified'].apply(lambda x: "✅ Verified" if x else "⏳ Pending")
            
            # Display table
            st.dataframe(
                df[['Invoice #', 'Amount', 'Date', 'Method', 'Status']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Invoice #": st.column_config.NumberColumn(),
                    "Amount": st.column_config.TextColumn(),
                    "Date": "Payment Date",
                    "Method": "Payment Method",
                    "Status": st.column_config.TextColumn()
                }
            )
        else:
            st.info("No payment history found")

        conn.close()

def get_user_id(username):
    """Helper function to get database user ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()[0] if cursor.rowcount > 0 else None
    conn.close()
    return result