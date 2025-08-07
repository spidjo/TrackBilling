# main.py

import streamlit as st
from utils.session import init_session_state

# --- Auth views
from views.auth.auth_view import auth_view
from views.auth.reset_password import reset_password
from views.auth.reset_password_request import reset_password_request
from auth_manager import verify_token 

# --- SuperAdmin views
from views.superadmin.superadmin_dashboard import superadmin_dashboard
from views.superadmin.tenant_manager import tenant_manager
from views.superadmin.admin_analytics_dashboard import render_admin_analytics_dashboard
from views.superadmin.resend_log_view import resend_log_view
from views.superadmin.monthly_report_scheduler import run_monthly_report

# --- Admin views
from views.admin.admin_dashboard import admin_dashboard
from views.admin.billing_admin import billing_admin
from views.admin.payment_admin import payment_admin
from views.admin.tenant_assign_plan_view import assign_plans
from views.admin.upload_usage_csv import render_upload_usage_csv
from views.admin.subscription_audit_admin import subscription_audit_admin
from views.admin.plan_admin_view import plan_admin_view
from views.admin.usage_metric_admin import usage_metric_admin
from views.admin.plan_metric_limits_admin import plan_metric_limits_admin
from views.admin.admin_payment_verification import admin_payment_verification
from views.admin.admin_billing_report import admin_tenant_billing_report

# --- Client views
from views.client.client_dashboard import client_dashboard
from views.client.subscription_client import subscription_client
from views.client.client_billing_portal import client_billing_portal
from views.client.client_usage_dashboard import client_usage_dashboard
from views.client.invoice_preview import invoice_preview
from views.client.client_payment_view import client_payment_view


# --- Role menus
SUPERADMIN_MENU = {
    "📊 Platform Overview": superadmin_dashboard,
    "📈 Analytics Dashboard": render_admin_analytics_dashboard,
    "🏢 Manage Tenants": tenant_manager,
    "📜 Resend Log Viewer": resend_log_view
}

ADMIN_MENU = {
    "📊 Dashboard": admin_dashboard,
    "📦 Plan Management": plan_admin_view,
    "👥 Assign Plans": assign_plans,
    "📥 Upload Usage CSV": render_upload_usage_csv,
    "🧾 Billing Admin": billing_admin,
    "🧾 Billing Report": admin_tenant_billing_report,
    "📋 Subscription Audit": subscription_audit_admin,
    "📊 Usage Metrics": usage_metric_admin,
    "📊 Plan Metric Limits": plan_metric_limits_admin,
    "🧾 Payment Verification": admin_payment_verification,
    "💳 Payment Admin": payment_admin
}

CLIENT_MENU = {
    "📊 Dashboard": client_dashboard,
    "📦 My Subscription": subscription_client,
    "💳 Billing Portal": client_billing_portal,
    "📈 Usage Dashboard": client_usage_dashboard,
    "💳 My Payments": client_payment_view
}


def main():
    st.set_page_config(page_title="SaaS Billing Platform", layout="wide")
    init_session_state()

    query_params = st.query_params

    # --- Auth Routes
    if "verify" in query_params:
        token = query_params.get("verify")
        if token:
            result = verify_token(token)
            if result.get("success"):
                st.success("✅ Email verified successfully!")
            else:
                st.error(f"❌ {result.get('error', 'Verification failed.')}")
        return
    
    if "token" in query_params:
        reset_password()
        return

    if "reset" in query_params:
        reset_password_request()
        return

    # --- Not logged in
    if not st.session_state.get("authenticated"):
        auth_view()
        return

    # --- Role-based routing
    role = st.session_state.get("role")
    if role == "superadmin":
        st.sidebar.subheader("🛠️ SuperAdmin Panel")
        menu = st.sidebar.radio("Navigate", list(SUPERADMIN_MENU.keys()))
        SUPERADMIN_MENU[menu]()
        if st.sidebar.button("📜 Run monthly billing"):
            run_monthly_report()
            st.success("Monthly billing reports generated and emailed to admins.")
            st.rerun()

    elif role == "admin":
        st.sidebar.subheader("🧑‍💼 Admin Panel")
        menu = st.sidebar.radio("Navigate", list(ADMIN_MENU.keys()))
        ADMIN_MENU[menu]()

    elif role == "client":
        st.sidebar.subheader("🙋 Client Panel")
        menu = st.sidebar.radio("Navigate", list(CLIENT_MENU.keys()))
        CLIENT_MENU[menu]()

    else:
        st.error("🚫 Unauthorized role.")

    if st.sidebar.button("🔓 Logout"):
        st.session_state.clear()
        st.rerun()


if __name__ == "__main__":
    main()
