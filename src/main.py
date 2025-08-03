# main.py

import streamlit as st
from views.admin_dashboard import admin_dashboard
from views.billing_admin import billing_admin
from views.auth_view import auth_view
from session import init_session_state
from views.client_billing_portal import client_billing_portal
from views.client_dashboard import client_dashboard
from views.payment_admin import payment_admin
from views.tenant_admin import manage_tenants
from views.tenant_assign_plan_view import assign_plans
from views.tenant_manager import tenant_manager
from views.upload_usage_csv import render_upload_usage_csv
from views.usage_dashboard import usage_dashboard
from views.reset_password_request import reset_password_request
from views.reset_password import reset_password


def main():
    st.set_page_config(page_title="SaaS Billing Platform", layout="wide")
    init_session_state()

    query_params = st.query_params  # ✅ use the new query param API

    # Route for password reset token page
    if "token" in query_params:
        reset_password()
        return

    # Route for password reset request page
    if "reset" in query_params:
        reset_password_request()
        return

    # Default login flow
    if not st.session_state.get("authenticated"):
        auth_view()
        return

    # Role-based routing (you can expand this)
    role = st.session_state.get("role")
    if role == "superadmin":
        st.sidebar.subheader("Admin Manager Panel")
        menu = st.sidebar.radio("Navigate", ["Platform Overview", "Analytics Dashboard", "Manage Tenants", "🧾 Billing Admin", "Payment Admin"])
        if menu == "Tenant Manager":
            tenant_manager()
        elif menu == "Platform Overview":
            from views.superadmin_dashboard import superadmin_dashboard
            superadmin_dashboard()
        elif menu == "🧾 Billing Admin":
            billing_admin()
        elif menu == "Payment Admin":
            payment_admin()
        elif menu == "Analytics Dashboard":
            from views.admin_analytics_dashboard import render_admin_analytics_dashboard
            render_admin_analytics_dashboard()
        else:
            st.write("Admin dashboard coming soon...")
    elif role == "admin":
        st.sidebar.subheader("Admin Panel")
        menu = st.sidebar.radio("Navigate", ["Dashboard", "Assign Plans", "Upload Usage CSV", "🧾 Billing Admin"])
        if menu == "Assign Plans":
            assign_plans()
        elif menu == "Dashboard":
            admin_dashboard()
        elif menu == "Upload Usage CSV":
            render_upload_usage_csv()
        elif menu == "🧾 Billing Admin":
            billing_admin()
        else:
            st.write("Admin dashboard coming soon...")
    elif role == "client":
        st.sidebar.subheader("Client Panel")
        menu = st.sidebar.radio("Navigate", ["Dashboard", "Billing Portal"])
        if menu == "Billing Portal":
            client_billing_portal()
        elif menu == "Dashboard":
            client_dashboard()
            # usage_dashboard()
        else:
            st.write("Dashboard coming soon...")
    else:
        st.error("Unauthorized role.")

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

if __name__ == "__main__":
    main()
