# src/views/admin/billing_admin.py
import streamlit as st
import psycopg2.extras
from datetime import datetime
from billing_engine import generate_invoices   
from db.database import get_db_connection
from auto_generate_invoices import auto_generate_invoices
from utils.pdf_generator import generate_pdf_invoice


def billing_admin():
    # Session validation
    if st.session_state.get("role") not in ["admin", "superadmin"]:
        st.error("⛔ You don't have permission to access this page.")
        st.stop()

    st.title("🧾 Billing Administration")
    st.caption("Manage tenant billing and invoices")
    
    tenant_id = st.session_state.get("tenant_id")
    now = datetime.now()
    default_period = now.strftime("%Y-%m")

    # Tab organization for better UX
    tab1, tab2, tab3 = st.tabs(["Generate Invoices", "Auto-Billing", "Invoice History"])

    with tab1:
        st.subheader("📅 Manual Invoice Generation")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            billing_period = st.text_input(
                "Billing Period (YYYY-MM)", 
                value=default_period,
                help="The period to generate invoices for"
            )
        with col2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            generate_btn = st.button(
                "🚀 Generate Invoices", 
                key="generate_btn",
                help="Generate invoices for the current tenant"
            )
        
        if generate_btn:
            with st.spinner("Generating invoices..."):
                try:
                    invoice_ids = generate_invoices(tenant_id, billing_period)
                    
                    if not invoice_ids:
                        st.warning("⚠️ No billable items found for this period.")
                        return
                    
                    st.success(f"✅ Successfully generated {len(invoice_ids)} invoice(s)")
                    
                    # PDF generation section
                    with st.expander("📄 Generate PDF Receipts", expanded=False):
                        for invoice_id in invoice_ids:
                            if st.button(f"Generate PDF for Invoice #{invoice_id}"):
                                try:
                                    invoice_details = get_invoice_details(invoice_id)
                                    generate_pdf_invoice(invoice_details)
                                    st.success(f"PDF generated for invoice #{invoice_id}")
                                except Exception as e:
                                    st.error(f"Failed to generate PDF: {str(e)}")
                                    if st.session_state.get("role") == "superadmin":
                                        st.exception(e)  # Show full trace for admins
                    
                except Exception as e:
                    st.error(f"❌ Invoice generation failed: {str(e)}")
                    st.exception(e) if st.session_state.get("role") == "superadmin" else None

    with tab2:
        st.subheader("🤖 Automatic Billing")
        st.info("This will process all active subscriptions and generate invoices automatically.")
        
        if st.button("🌀 Run Auto-Billing Now", help="Process all active subscriptions"):
            with st.spinner("Processing auto-billing..."):
                try:
                    result = auto_generate_invoices()
                    if result.get("success"):
                        st.success(f"✅ Auto-billing completed. {result.get('count', 0)} invoices generated.")
                        st.balloons()
                    else:
                        st.warning("⚠️ Auto-billing completed with no new invoices.")
                except Exception as e:
                    st.error(f"❌ Auto-billing failed: {str(e)}")
                    st.exception(e) if st.session_state.get("role") == "superadmin" else None

    with tab3:
        st.subheader("📜 Recent Invoice History")
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id, 
                    invoice_date, 
                    total_amount, 
                    CASE WHEN is_paid THEN '✅ Paid' ELSE '❌ Unpaid' END as status, 
                    created_at,
                    pdf_generated
                FROM invoices
                WHERE tenant_id = %s
                ORDER BY created_at DESC
                LIMIT 20
            """, (tenant_id,))
            rows = cursor.fetchall()
            
            if not rows:
                st.info("ℹ️ No invoices found for this tenant.")
                return
                
            for inv in rows:
                current_invoice_id = inv[0]  # Store the invoice ID from the current row
                with st.expander(f"Invoice #{current_invoice_id} - {inv[1]}", expanded=False):
                    cols = st.columns([1,1,1,1])
                    cols[0].metric("Amount", f"R{inv[2]:.2f}")
                    cols[1].metric("Status", inv[3])
                    cols[2].metric("Created", inv[4].strftime("%Y-%m-%d"))
                    cols[3].metric("PDF", "✅ Generated" if inv[5] else "❌ Missing")
                    
                    # Action buttons
                    action_col1, action_col2 = st.columns([1,3])
                    with action_col1:
                        if st.button(f"📄 Generate PDF", key=f"pdf_{current_invoice_id}"):
                            try:
                                invoice_details = get_invoice_details(current_invoice_id)  # Use the stored invoice ID
                                generate_pdf_invoice(invoice_details)
                                st.success(f"PDF generated for invoice #{current_invoice_id}")  # Use the stored invoice ID
                            except Exception as e:
                                st.error(f"Failed to generate PDF: {str(e)}")
                                if st.session_state.get("role") == "superadmin":
                                    st.exception(e)  # Show full trace for admins
                    
        except Exception as e:
            st.error(f"Failed to load invoice history: {str(e)}")
        finally:
            if conn:
                conn.close()

def get_invoice_details(invoice_id):
    """
    Retrieves complete invoice details including customer, tenant, and line items
    Returns a dictionary with all data needed for PDF generation
    
    Structure:
    {
        "invoice_id": int,
        "invoice_number": str,
        "invoice_date": str,
        "period_start": str,
        "period_end": str,
        "is_paid": bool,
        "due_date": str,
        "tenant": {
            "id": int,
            "name": str,
            "company_name": str,
            "address": str,
            "email": str,
            "phone": str
        },
        "customer": {
            "user_id": int,
            "name": str,  # Combined first + last name
            "first_name": str,
            "last_name": str,
            "company_name": str,
            "email": str,
            "username": str
        },
        "items": [
            {
                "description": str,
                "quantity": float,
                "unit_price": float,
                "total_price": float,
                "date": str  # Added date field for PDF generator
            }
        ],
        "total_amount": float,
        "subtotal": float,
        "tax_amount": float,
        "payment_status": str,
        "created_at": str,
        "pdf_generated": bool,
        "notes": str
    }
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get basic invoice information with tenant and user details
        cursor.execute("""
            SELECT 
                i.id,
                i.period_start,
                i.period_end,
                i.invoice_date,
                i.total_amount,
                i.subtotal,
                i.tax_amount,
                i.is_paid,
                i.due_date,
                i.created_at,
                i.pdf_generated,
                i.notes,
                t.id,
                t.name,
                t.company_name,
                t.address,
                t.email,
                t.phone,
                u.id,
                u.first_name,
                u.last_name,
                u.company_name,
                u.email,
                u.username
            FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            JOIN users u ON i.user_id = u.id
            WHERE i.id = %s
        """, (invoice_id,))
        
        invoice_data = cursor.fetchone()
        if not invoice_data:
            raise ValueError(f"Invoice with ID {invoice_id} not found")

        # Map the tuple results to named fields
        (invoice_id, period_start, period_end, invoice_date, total_amount, subtotal,
         tax_amount, is_paid, due_date, created_at, pdf_generated, notes,
         tenant_id, tenant_name, tenant_company, tenant_address, tenant_email, tenant_phone,
         user_id, first_name, last_name, user_company, user_email, username) = invoice_data

        # Get all invoice items
        cursor.execute("""
            SELECT 
                description,
                quantity,
                unit_price,
                total_price,
                created_at
            FROM invoice_items
            WHERE invoice_id = %s
            ORDER BY id
        """, (invoice_id,))
        
        items = [{
            "description": item[0],
            "quantity": float(item[1]),
            "unit_price": float(item[2]),
            "total_price": float(item[3]),
            "date": item[4].strftime("%Y-%m-%d") if item[4] else ""
        } for item in cursor.fetchall()]

        # Calculate payment status
        payment_status = "Paid" if is_paid else "Unpaid"
        
        # Format dates
        def format_date(date_obj):
            return date_obj.strftime("%Y-%m-%d") if date_obj else "N/A"

        # Prepare the result dictionary
        result = {
            "invoice_id": invoice_id,
            "invoice_number": f"INV-{invoice_id:05d}",
            "invoice_date": format_date(invoice_date),
            "period_start": format_date(period_start),
            "period_end": format_date(period_end),
            "is_paid": is_paid,
            "due_date": format_date(due_date),
            "tenant": {
                "id": tenant_id,
                "name": tenant_name,
                "company_name": tenant_company,
                "address": tenant_address,
                "email": tenant_email,
                "phone": tenant_phone or "N/A"
            },
            "customer": {
                "user_id": user_id,
                "name": f"{first_name} {last_name}",  # Combined name for PDF
                "first_name": first_name,
                "last_name": last_name,
                "company_name": user_company,
                "email": user_email,
                "username": username
            },
            "items": items,
            "total_amount": float(total_amount),
            "subtotal": float(subtotal),
            "tax_amount": float(tax_amount) if tax_amount else 0.0,
            "payment_status": payment_status,
            "created_at": format_date(created_at),
            "pdf_generated": pdf_generated,
            "notes": notes or ""
        }

        return result

    except Exception as e:
        raise Exception(f"Failed to fetch invoice details: {str(e)}")
    finally:
        if conn:
            conn.close()