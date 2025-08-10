import streamlit as st
from datetime import date, timedelta
from utils.session_guard import require_login
from utils.report_utils import generate_tenant_billing_report_pdf, generate_superadmin_pdf_report
from utils.ui_helpers import display_loading_animation

def admin_tenant_billing_report():
    """Admin interface for generating billing reports with enhanced UX"""
    require_login("admin")
    st.set_page_config(page_title="🧾 Billing Analytics", layout="wide")
    
    user = st.session_state.get("user")
    tenant_id = user["tenant_id"]
    is_superadmin = user.get("role") == "superadmin"
    
    # Page header with dynamic title
    title = "📊 Tenant Billing Analytics" if not is_superadmin else "📈 Multi-Tenant Billing Dashboard"
    st.title(title)
    
    # Smart default date ranges
    today = date.today()
    default_start = today.replace(day=1)
    default_end = today
    
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            # Date selection form
            with st.form("report_params"):
                start_date = st.date_input(
                    "Start Date", 
                    value=default_start,
                    max_value=today,
                    help="Select the start of the reporting period"
                )
                end_date = st.date_input(
                    "End Date", 
                    value=default_end,
                    max_value=today,
                    min_value=start_date,
                    help="Select the end of the reporting period"
                )
                
                # Superadmin-specific filters
                if is_superadmin:
                    tenant_filter = st.multiselect(
                        "Filter Tenants",
                        options=get_tenant_options(),
                        default=[],
                        help="Select specific tenants to include"
                    )
                
                submitted = st.form_submit_button(
                    "Generate Report",
                    type="primary",
                    use_container_width=True
                )
        
        with col2:
            # Help section
            with st.expander("ℹ️ Report Guide", expanded=True):
                st.markdown("""
                **This report provides:**
                - 📅 Billing summary for selected period
                - 💰 Revenue and payment analytics
                - 👥 User activity metrics
                - 📈 Comparative performance data
                """)
                if is_superadmin:
                    st.markdown("**Superadmin Features:**")
                    st.markdown("- 🔍 Cross-tenant comparisons")
                    st.markdown("- 🏆 Performance benchmarking")
    
    # Report generation
    if submitted:
        with st.spinner("Compiling your report..."):
            try:
                # Display loading animation
                with display_loading_animation():
                    if is_superadmin:
                        pdf_bytes = generate_superadmin_pdf_report(
                            start_date, 
                            end_date,
                            tenant_filter if tenant_filter else None
                        )
                        filename = f"MultiTenant_Report_{start_date}_to_{end_date}.pdf"
                    else:
                        pdf_bytes = generate_tenant_billing_report_pdf(
                            tenant_id, 
                            start_date, 
                            end_date
                        )
                        filename = f"{user['tenant_name']}_Report_{start_date}_to_{end_date}.pdf"
                
                # Success UI
                st.success("✅ Report generated successfully!")
                
                # Download section
                with st.container():
                    st.download_button(
                        label="⬇️ Download Full Report",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                    
                    # Quick summary preview
                    with st.expander("🔍 Report Preview", expanded=True):
                        if is_superadmin:
                            display_superadmin_preview(start_date, end_date)
                        else:
                            display_tenant_preview(tenant_id, start_date, end_date)
            
            except Exception as e:
                st.error(f"⚠️ Report generation failed: {str(e)}")
                st.exception(e) if is_superadmin else None

def get_tenant_options():
    """Fetch tenant options for superadmin filter"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM tenants ORDER BY name")
        return [f"{row[1]} (ID: {row[0]})" for row in cursor.fetchall()]
    finally:
        conn.close()

def display_tenant_preview(tenant_id, start_date, end_date):
    """Display key metrics preview for single tenant"""
    # Fetch and display summary data
    # Implement your preview logic here
    pass

def display_superadmin_preview(start_date, end_date):
    """Display aggregated preview for superadmin"""
    # Fetch and display summary data
    # Implement your preview logic here
    pass