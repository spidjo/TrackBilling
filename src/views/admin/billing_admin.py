import streamlit as st
from datetime import datetime
from billing_engine import BillingEngine
from db.database import get_db_connection
from auto_generate_invoices import auto_generate_invoices
from utils.pdf_generator import generate_pdf_invoice
import tempfile
import os

# Apply the same custom CSS as admin_dashboard.py
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
    
    .metric-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
        border-top: 4px solid;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }
    .metric-positive {
        border-top-color: var(--secondary);
    }
    .metric-neutral {
        border-top-color: var(--info);
    }
    .metric-negative {
        border-top-color: var(--danger);
    }
    .metric-warning {
        border-top-color: var(--warning);
    }
    
    .alert-card {
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-left: 4px solid;
    }
    .alert-danger {
        border-left-color: var(--danger);
        background-color: #FEE2E2;
    }
    .alert-warning {
        border-left-color: var(--warning);
        background-color: #FEF3C7;
    }
    .alert-info {
        border-left-color: var(--info);
        background-color: #DBEAFE;
    }
    .alert-success {
        border-left-color: var(--secondary);
        background-color: #D1FAE5;
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
    
    .invoice-card {
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-left: 4px solid var(--info);
    }
</style>
""", unsafe_allow_html=True)

def billing_admin():
    # Session validation
    if st.session_state.get("role") not in ["admin", "superadmin"]:
        st.error("⛔ You don't have permission to access this page.")
        st.stop()

    # Page configuration
    st.set_page_config(
        page_title="Billing Administration",
        layout="wide",
        page_icon="🧾"
    )

    # Enhanced header matching admin_dashboard.py style
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">🧾 Billing Administration</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    tenant_id = st.session_state.get("tenant_id")
    now = datetime.now()
    default_period = now.strftime("%Y-%m")

    # Initialize the billing engine
    billing_engine = BillingEngine()

    # Organize tabs with icons
    tab1, tab2, tab3 = st.tabs([
        "📅 Generate Invoices", 
        "🤖 Auto-Billing", 
        "📜 Invoice History"
    ])

    # -------------------------
    # Tab 1: Manual Invoice Generation
    # -------------------------
    with tab1:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📅</div>
            <h2>Manual Invoice Generation</h2>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])
        with col1:
            billing_period = st.text_input(
                "Billing Period (YYYY-MM)*",
                value=default_period,
                help="The period to generate invoices for",
                key="billing_period_input"
            )
        with col2:
            st.write("")  # spacer
            st.write("")
            generate_btn = st.button(
                "🚀 Generate Invoices",
                key="generate_btn",
                help="Generate invoices for the current tenant",
                type="primary",
                use_container_width=True
            )

        if generate_btn:
            with st.spinner("Generating invoices..."):
                try:
                    # Validate billing period format
                    try:
                        datetime.strptime(billing_period + "-01", "%Y-%m-%d")
                    except ValueError:
                        st.error("❌ Invalid billing period format. Please use YYYY-MM format.")
                        st.stop()

                    # Generate invoices - this now happens in its own transaction
                    invoice_ids = billing_engine.generate_invoices(tenant_id, billing_period)

                    if not invoice_ids:
                        st.markdown("""
                        <div class="alert-card alert-warning">
                            <p><strong>⚠️ No billable items found for this period.</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="alert-card alert-success">
                            <p><strong>✅ Successfully generated {len(invoice_ids)} invoice(s)</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.balloons()

                        # Show generated invoices
                        st.markdown("""
                        <div class="section-header">
                            <div class="icon">📄</div>
                            <h2>Generated Invoices</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        for invoice_id in invoice_ids:
                            with st.expander(f"Invoice #{invoice_id}", expanded=False):
                                _handle_invoice_pdf_generation(invoice_id)

                except Exception as e:
                    st.markdown(f"""
                    <div class="alert-card alert-danger">
                        <p><strong>❌ Invoice generation failed:</strong> {str(e)}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.session_state.get("role") == "superadmin":
                        st.exception(e)

    # -------------------------
    # Tab 2: Automatic Billing
    # -------------------------
    with tab2:
        st.markdown("""
        <div class="section-header">
            <div class="icon">🤖</div>
            <h2>Automatic Billing</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="alert-card alert-info">
            <p>This will process all active subscriptions and generate invoices automatically.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🌀 Run Auto-Billing Now", 
                    help="Process all active subscriptions",
                    type="primary",
                    use_container_width=True):
            with st.spinner("Processing auto-billing..."):
                try:
                    result = auto_generate_invoices()
                    success = result.get("success", False)
                    count = result.get("count", 0)
                    errors = result.get("errors", [])
                    
                    if success and count > 0:
                        st.markdown(f"""
                        <div class="alert-card alert-success">
                            <p><strong>✅ Auto-billing completed. {count} invoices generated.</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.balloons()
                        if errors:
                            with st.expander("⚠️ View Errors", expanded=False):
                                for error in errors:
                                    st.error(error)
                    elif success and count == 0:
                        st.markdown("""
                        <div class="alert-card alert-info">
                            <p><strong>ℹ️ Auto-billing completed with no new invoices.</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div class="alert-card alert-danger">
                            <p><strong>❌ Auto-billing failed. Check server logs for details.</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                        if errors:
                            with st.expander("❌ View Errors", expanded=True):
                                for error in errors:
                                    st.error(error)
                except Exception as e:
                    st.markdown(f"""
                    <div class="alert-card alert-danger">
                        <p><strong>❌ Auto-billing failed:</strong> {str(e)}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.session_state.get("role") == "superadmin":
                        st.exception(e)

    # -------------------------
    # Tab 3: Recent Invoice History
    # -------------------------
    with tab3:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📜</div>
            <h2>Recent Invoice History</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox(
                "Filter by Status*",
                ["All", "Paid", "Unpaid"],
                index=0
            )
        with col2:
            date_filter = st.selectbox(
                "Filter by Date Range*",
                ["Last 30 days", "Last 90 days", "This year", "All time"],
                index=0
            )
        with col3:
            st.write("")  # Spacer for layout
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Build query based on filters
            query = """
                SELECT 
                    id, 
                    invoice_date, 
                    total_invoiced, 
                    is_paid,
                    created_at,
                    pdf_generated
                FROM invoices
                WHERE tenant_id = %s
            """
            params = [tenant_id]
            
            # Add status filter
            if status_filter == "Paid":
                query += " AND is_paid = TRUE"
            elif status_filter == "Unpaid":
                query += " AND is_paid = FALSE"
            
            # Add date filter
            if date_filter == "Last 30 days":
                query += " AND invoice_date >= CURRENT_DATE - INTERVAL '30 days'"
            elif date_filter == "Last 90 days":
                query += " AND invoice_date >= CURRENT_DATE - INTERVAL '90 days'"
            elif date_filter == "This year":
                query += " AND invoice_date >= DATE_TRUNC('year', CURRENT_DATE)"
            
            query += " ORDER BY invoice_date DESC LIMIT 50"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                st.markdown("""
                <div class="alert-card alert-info">
                    <p><strong>ℹ️ No invoices found matching your criteria.</strong></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="alert-card alert-info">
                    <p><strong>Showing {len(rows)} most recent invoices</strong></p>
                </div>
                """, unsafe_allow_html=True)
                
                for inv in rows:
                    current_invoice_id = inv[0]
                    with st.container(border=True):
                        cols = st.columns([1, 1, 1, 1])
                        cols[0].metric("Amount", f"R{inv[2]:.2f}")
                        cols[1].metric("Status", "✅ Paid" if inv[3] else "❌ Unpaid")
                        cols[2].metric("Invoice Date", inv[1].strftime("%Y-%m-%d") if inv[1] else "N/A")
                        cols[3].metric("PDF", "✅ Generated" if inv[5] else "❌ Missing")

                        # Action buttons
                        action_col1, action_col2 = st.columns([1, 3])
                        with action_col1:
                            if st.button(
                                "📄 Generate PDF", 
                                key=f"pdf_{current_invoice_id}",
                                use_container_width=True
                            ):
                                _handle_invoice_pdf_generation(current_invoice_id)

        except Exception as e:
            st.markdown(f"""
            <div class="alert-card alert-danger">
                <p><strong>Failed to load invoice history:</strong> {str(e)}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.get("role") == "superadmin":
                st.exception(e)
        finally:
            if conn:
                conn.close()

def _handle_invoice_pdf_generation(invoice_id):
    """Helper function to handle PDF generation and download for an invoice."""
    try:
        with st.spinner("Generating PDF..."):
            billing_engine = BillingEngine()
            invoice_details = billing_engine.get_invoice_details(invoice_id)
           
            # Generate to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tenant = invoice_details.get("tenant")
                tenant_id = tenant.get("id") if tenant else None
                pdf_bytes = generate_pdf_invoice(invoice_details, tenant_id=tenant_id)
                tmp.write(pdf_bytes)
                tmp_path = tmp.name
            
            _mark_pdf_generated(invoice_id)
            
            # Display download button
            with open(tmp_path, "rb") as f:
                pdf_data = f.read()
                st.download_button(
                    label=f"⬇️ Download Invoice #{invoice_id}",
                    data=pdf_data,
                    file_name=f"invoice_{invoice_id}.pdf",
                    mime="application/pdf",
                    key=f"download_{invoice_id}",
                    use_container_width=True
                )
            
            # Clean up
            os.unlink(tmp_path)
            
    except Exception as e:
        st.markdown(f"""
        <div class="alert-card alert-danger">
            <p><strong>Failed to generate PDF:</strong> {str(e)}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.get("role") == "superadmin":
            st.exception(e)

def _mark_pdf_generated(invoice_id):
    """Mark invoice.pdf_generated = TRUE and update updated_at."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE invoices SET pdf_generated = TRUE, updated_at = NOW() WHERE id = %s",
                (invoice_id,)
            )
        conn.commit()
    except Exception as e:
        st.markdown(f"""
        <div class="alert-card alert-danger">
            <p><strong>Failed to update PDF status:</strong> {str(e)}</p>
        </div>
        """, unsafe_allow_html=True)
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    billing_admin()