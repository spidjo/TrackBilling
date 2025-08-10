# src/views/client_usage_dashboard.py
import streamlit as st
from datetime import datetime
import pandas as pd
from utils.session_guard import require_login
from db.database import get_db_connection
from utils.ui_helpers import loading_spinner, show_toast
from billing_engine import estimate_invoice_for_user, finalize_invoice_for_user, get_tenant_info, get_client_info
from utils.pdf_utils import generate_invoice_pdf

def client_usage_dashboard():
    """Client-facing usage dashboard with enhanced UX and performance"""
    # Page configuration
    st.set_page_config(
        page_title="Usage Dashboard", 
        layout="wide",
        page_icon="📊"
    )
    require_login("client")

    if not st.session_state.get("user"):
        st.stop()

    # Initialize session state
    if 'refresh_data' not in st.session_state:
        st.session_state.refresh_data = False

    # UI Header
    with st.container():
        st.title("📊 My Usage Dashboard")
        st.markdown("---")

    # Main content with loading spinner
    with loading_spinner("Loading your usage data..."):
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user and tenant info
        user_id = st.session_state.username
        tenant_id = st.session_state.tenant_id
        db_user_id = get_user_id(user_id)

        if not db_user_id:
            st.error("User not found")
            conn.close()
            return

        # --- Active Subscription Section ---
        with st.container(border=True):
            st.subheader("🔹 Current Subscription")
            cursor.execute("""
                SELECT p.name, p.description 
                FROM subscriptions s
                JOIN plans p ON s.plan_id = p.id
                WHERE s.user_id = %s AND s.is_active
            """, (db_user_id,))
            plan = cursor.fetchone()

            if not plan:
                st.warning("No active subscription found.")
                conn.close()
                return

            plan_name, plan_description = plan
            st.markdown(f"**Plan:** {plan_name}")
            if plan_description:
                st.caption(plan_description)

        # --- Usage Metrics Section ---
        st.markdown("## 📈 Current Usage")
        
        # Get current month usage
        current_month = datetime.utcnow().strftime('%Y-%m')
        cursor.execute("""
            SELECT um.name, pml.metric_limit, COALESCE(SUM(ur.usage_amount), 0) as used
            FROM plan_metric_limits pml
            JOIN usage_metrics um ON pml.metric_id = um.id
            LEFT JOIN usage_records ur ON ur.metric_id = um.id 
                AND ur.user_id = %s 
                AND TO_CHAR(ur.usage_date, 'YYYY-MM') = %s
            WHERE pml.plan_id = (SELECT plan_id FROM subscriptions WHERE user_id = %s AND is_active)
            GROUP BY um.name, pml.metric_limit
        """, (db_user_id, current_month, db_user_id))
        
        metrics = cursor.fetchall()

        if not metrics:
            st.info("No usage metrics defined for your plan.")
        else:
            # Display metrics in columns
            cols = st.columns(2)
            for i, (metric_name, limit, used) in enumerate(metrics):
                with cols[i % 2]:
                    with st.container(border=True):
                        st.markdown(f"**{metric_name}**")
                        
                        # Calculate usage percentage
                        percent_used = min((used / limit) * 100, 100) if limit > 0 else 0
                        remaining = max(limit - used, 0)
                        
                        # Progress bar with tooltip
                        st.progress(
                            percent_used / 100,
                            text=f"{used:,} of {limit:,} ({percent_used:.0f}%) used"
                        )
                        
                        # Usage status
                        if used > limit:
                            st.error(f"❌ Over by {used - limit:,}")
                        elif percent_used > 80:
                            st.warning(f"⚠️ Only {remaining:,} remaining")
                        else:
                            st.success(f"✅ {remaining:,} remaining")

        st.markdown("---")

        # --- Invoice History Section ---
        st.markdown("## 🧾 Invoice History")
        
        cursor.execute("""
            SELECT 
                i.id, 
                i.period_start, 
                i.period_end, 
                i.total_amount,
                COALESCE(SUM(p.amount), 0) as paid_amount,
                BOOL_OR(p.is_verified) as is_verified
            FROM invoices i
            LEFT JOIN payments p ON i.id = p.invoice_id
            WHERE i.user_id = %s
            GROUP BY i.id
            ORDER BY i.period_start DESC
            LIMIT 6
        """, (db_user_id,))
        
        invoices = cursor.fetchall()

        if not invoices:
            st.info("No invoices found for your account.")
        else:
            # Enhanced dataframe display
            df = pd.DataFrame(invoices, columns=[
                "ID", "Start Date", "End Date", "Total", "Paid", "Verified"
            ])
            
            # Format dates and amounts
            df['Start Date'] = pd.to_datetime(df['Start Date']).dt.strftime('%Y-%m-%d')
            df['End Date'] = pd.to_datetime(df['End Date']).dt.strftime('%Y-%m-%d')
            df['Total'] = df['Total'].apply(lambda x: f"R{x:,.2f}")
            df['Paid'] = df['Paid'].apply(lambda x: f"R{x:,.2f}")
            df['Status'] = df['Verified'].apply(
                lambda x: "✅ Paid" if x else "❌ Unpaid" if df.loc[df['Verified'] == x, 'Paid'].iloc[0] == "R0.00" else "⏳ Pending"
            )
            
            # Display with better formatting
            st.dataframe(
                df[['ID', 'Start Date', 'End Date', 'Total', 'Paid', 'Status']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("Invoice #"),
                    "Start Date": "Period Start",
                    "End Date": "Period End",
                    "Total": st.column_config.TextColumn("Total Amount"),
                    "Paid": st.column_config.TextColumn("Amount Paid"),
                    "Status": st.column_config.TextColumn("Payment Status")
                }
            )

        # --- Invoice Preview Section ---
        st.markdown("## 📄 Current Period Estimate")
        
        with st.expander("View estimated charges", expanded=True):
            items, estimated_total = estimate_invoice_for_user(db_user_id, tenant_id)
            
            if not items:
                st.info("No estimated charges for current period.")
            else:
                # Display breakdown in columns
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("**Breakdown**")
                    for item in items:
                        st.markdown(
                            f"- {item['description']}: "
                            f"{item['quantity']} × R{item['unit_price']:.2f} = "
                            f"**R{item['total_price']:.2f}**"
                        )
                
                with col2:
                    st.metric(
                        "Estimated Total", 
                        f"R{estimated_total:.2f}",
                        help="Based on current usage and plan rates"
                    )
                    
                    # PDF download button
                    if st.button("📥 Download Estimate PDF", use_container_width=True):
                        with loading_spinner("Generating PDF..."):
                            fake_invoice = {
                                "id": "ESTIMATE",
                                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                                "period_start": datetime.now().replace(day=1).strftime("%Y-%m-%d"),
                                "period_end": datetime.now().strftime("%Y-%m-%d"),
                                "total_amount": estimated_total,
                                "is_paid": False
                            }
                            
                            pdf_bytes = generate_invoice_pdf(
                                fake_invoice, 
                                items,
                                tenant_info=get_tenant_info(cursor, tenant_id),
                                client_info=get_client_info(cursor, user_id)
                            )
                            
                            st.download_button(
                                label="⬇️ Download Now",
                                data=pdf_bytes,
                                file_name=f"estimate_{current_month}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )

                # Finalize invoice button with confirmation
                if st.button("💳 Generate Final Invoice", type="primary", use_container_width=True):
                    if st.session_state.get("confirm_invoice", False):
                        with loading_spinner("Creating invoice..."):
                            success, result = finalize_invoice_for_user(db_user_id, tenant_id)
                            if success:
                                show_toast(f"Invoice #{result} created successfully!", "success")
                                st.session_state.refresh_data = True
                                st.rerun()
                            else:
                                st.error(f"Error: {result}")
                    else:
                        st.session_state.confirm_invoice = True
                        st.warning("Are you sure you want to generate a final invoice?")
                        if st.button("Yes, generate invoice", type="primary"):
                            st.session_state.confirm_invoice = False
                            st.rerun()

        conn.close()

def get_user_id(username):
    """Helper function to get database user ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()[0] if cursor.rowcount > 0 else None
    conn.close()
    return result