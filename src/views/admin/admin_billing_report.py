import streamlit as st
from datetime import date
from utils.session_guard import require_login
from utils.report_utils import generate_tenant_billing_report_pdf

def admin_tenant_billing_report():
    require_login("admin")
    st.set_page_config(page_title="🧾 Admin Billing Report", layout="wide")
    st.title("📥 Download Billing Report")
    user = st.session_state.get("user")
    tenant_id = user["tenant_id"]

    # Form to collect date range
    with st.form("billing_report_form"):
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start Date", date.today().replace(day=1))
        end_date = col2.date_input("End Date", date.today())
        submitted = st.form_submit_button("Generate PDF Report")

    # Generate and display the download button outside the form
    if submitted:
        pdf_bytes = generate_tenant_billing_report_pdf(tenant_id, start_date, end_date)
        st.success("✅ Report generated below.")
        st.download_button(
            label="📄 Download Report PDF",
            data=pdf_bytes,
            file_name=f"Tenant_Billing_Report_{start_date}_to_{end_date}.pdf",
            mime="application/pdf"
        )

