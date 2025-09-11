# src/views/client_payment_view.py
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from db.database import get_db_connection 
from utils.session import init_session_state, validate_session
from utils.ui_helpers import loading_spinner, show_toast

# Custom CSS for professional styling consistent with admin dashboard
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
    
    .invoice-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
        border-left: 4px solid;
    }
    .invoice-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }
    .invoice-unpaid {
        border-left-color: var(--warning);
    }
    .invoice-partial {
        border-left-color: var(--info);
    }
    .invoice-paid {
        border-left-color: var(--secondary);
    }
    
    .payment-form-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-top: 4px solid var(--primary);
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
    
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
        display: inline-block;
    }
    .status-verified {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .status-pending {
        background-color: #FEF3C7;
        color: #92400E;
    }
</style>
""", unsafe_allow_html=True)

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"

def client_payment_view():
    """Client payment portal with enhanced UX and professional styling"""
    init_session_state()
    
    # Session validation with redirect
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()
        
    # Page configuration
    st.set_page_config(
        page_title="My Payments",
        layout="wide",
        page_icon="💳"
    )
    
    # Initialize session state
    if 'refresh_data' not in st.session_state:
        st.session_state.refresh_data = False

    # UI Header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">💳 My Payments</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">{datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            <button onclick="window.location.reload()" style="background-color: #4F46E5; color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; cursor: pointer;">Refresh</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # Main content with loading spinner
    with loading_spinner("Loading payment information..."):
        conn = get_db_connection()
        cursor = conn.cursor()

        # Direct session user_id storage
        user_id = st.session_state.user_id  

        if not user_id:
            st.error("User not found")
            conn.close()
            return

        # --- Unpaid Invoices Section ---
        st.markdown("""
        <div class="section-header">
            <div class="icon">📄</div>
            <h2>Unpaid Invoices</h2>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT 
                i.id, 
                i.invoice_date, 
                i.total_invoiced,
                i.period_start,
                i.period_end,
                i.due_date,
                COALESCE(SUM(p.amount), 0) as paid_amount
            FROM invoices i
            LEFT JOIN payments p ON i.id = p.invoice_id
            WHERE i.user_id = %s AND i.is_paid = False
            GROUP BY i.id
            ORDER BY i.invoice_date DESC
        """, (user_id,))
        
        invoices = cursor.fetchall()

        if not invoices:
            st.markdown("""
            <div style="text-align: center; padding: 2rem; background-color: #D1FAE5; border-radius: 12px;">
                <h3 style="color: #065F46; margin-bottom: 1rem;">🎉 All Caught Up!</h3>
                <p style="color: #065F46;">You have no unpaid invoices at this time.</p>
            </div>
            """, unsafe_allow_html=True)
            conn.close()
            return

        # Display invoices in expandable cards for better organization
        for idx, (invoice_id, invoice_date, amount, period_start, period_end, due_date, paid_amount) in enumerate(invoices):
            # Determine invoice status
            balance_due = amount - paid_amount
            is_overdue = due_date and due_date < datetime.now().date()
            status_class = "invoice-unpaid"
            if paid_amount > 0:
                status_class = "invoice-partial"
            
            with st.container():
                st.markdown(f'<div class="invoice-card {status_class}">', unsafe_allow_html=True)
                
                # Invoice summary
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.markdown(f"**Invoice #** {invoice_id}")
                    st.caption(f"**Period:** {period_start.strftime('%b %d, %Y')} - {period_end.strftime('%b %d, %Y')}")
                    if due_date:
                        overdue_text = " ⚠️ Overdue" if is_overdue else ""
                        st.caption(f"**Due Date:** {due_date.strftime('%b %d, %Y')}{overdue_text}")
                
                with col2:
                    st.metric("Total Amount", format_currency(amount))
                
                with col3:
                    st.metric("Amount Paid", format_currency(paid_amount))
                
                with col4:
                    st.metric("Balance Due", format_currency(balance_due), 
                              delta=f"{-balance_due:.2f}" if balance_due < amount else None,
                              delta_color="inverse" if balance_due > 0 else "normal")
                
                # Payment form in expander
                with st.expander("💳 Submit Payment", expanded=False):
                    with st.form(f"payment_form_{invoice_id}", clear_on_submit=True):
                        st.markdown("#### Payment Details")
                        
                        # Form columns
                        col1, col2 = st.columns(2)
                        with col1:
                            payment_method = st.selectbox(
                                "Payment Method",
                                ["Bank Transfer", "Credit Card", "EFT", "Cash", "Other"],
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
                                # min_value=0.01,
                                max_value=float(balance_due),
                                value=float(balance_due),
                                step=1.00,
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
                                        user_id,
                                        invoice_id,
                                        amount_paid,
                                        payment_date.strftime("%Y-%m-%d"),
                                        payment_method,
                                        str(file_path),
                                        False,
                                        f"Payment submitted via client portal on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                                    ))

                                    # Update invoice status if fully paid
                                    if amount_paid >= balance_due:
                                        cursor.execute("""
                                            UPDATE invoices
                                            SET is_paid = True, paid_date = %s
                                            WHERE id = %s
                                        """, (datetime.now().strftime("%Y-%m-%d"), invoice_id))

                                    conn.commit()
                                    show_toast("Payment submitted successfully! Pending verification.", "success")
                                    st.session_state.refresh_data = True
                                    st.rerun()

                                except Exception as e:
                                    conn.rollback()
                                    show_toast(f"Payment failed: {str(e)}", "error")
                
                st.markdown('</div>', unsafe_allow_html=True)

        # --- Payment History Section ---
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="section-header">
            <div class="icon">📋</div>
            <h2>Payment History</h2>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT 
                p.id,
                p.invoice_id,
                p.amount,
                p.payment_date,
                p.payment_method,
                p.is_verified,
                p.notes,
                i.total_invoiced
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            WHERE p.user_id = %s
            ORDER BY p.payment_date DESC
            LIMIT 20
        """, (user_id,))
        
        payments = cursor.fetchall()

        if payments:
            # Convert to dataframe for better display
            df = pd.DataFrame(payments, columns=[
                "ID", "Invoice #", "Amount", "Date", "Method", "Verified", "Notes", "Invoice Total"
            ])
            
            # Format columns
            df['Amount'] = df['Amount'].apply(lambda x: f"R{x:.2f}")
            df['Invoice Total'] = df['Invoice Total'].apply(lambda x: f"R{x:.2f}")
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            df['Status'] = df['Verified'].apply(
                lambda x: '<span class="status-badge status-verified">✅ Verified</span>' if x 
                else '<span class="status-badge status-pending">⏳ Pending</span>'
            )
            
            # Display table
            st.markdown(df[['Invoice #', 'Amount', 'Invoice Total', 'Date', 'Method', 'Status']].to_html(
                escape=False, index=False, classes='dataframe', justify='left'), unsafe_allow_html=True)
            
            # Download option
            csv = df[['Invoice #', 'Amount', 'Date', 'Method', 'Verified']].to_csv(index=False)
            st.download_button(
                "Download Payment History",
                csv,
                file_name=f"payment_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No payment history found")

        conn.close()

def get_user_id(username):
    """Helper function to get database user ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()[0] if cursor.rowcount > 0 else None
    except Exception as e:
        st.error(f"Error fetching user ID: {e}")
    finally:
        conn.close()
    return result

if __name__ == "__main__":
    client_payment_view()