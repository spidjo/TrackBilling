import streamlit as st
from utils.session import init_session_state
from auth_manager import verify_token
from typing import Dict, Callable
from enum import Enum

# --- Constants and Configuration ---
class Role(Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    CLIENT = "client"

PAGE_TITLE = "SaaS Billing Platform"
PAGE_ICON = "💰"
PAGE_LAYOUT = "wide"

# --- Lazy Imports ---
def lazy_import(view_name: str):
    """Dynamically import views to improve startup performance"""
    module_map = {
        # Auth views
        "auth_view": "views.auth.auth_view",
        "reset_password": "views.auth.reset_password",
        "reset_password_request": "views.auth.reset_password_request",
        
        # SuperAdmin views
        "superadmin_dashboard": "views.superadmin.superadmin_dashboard",
        "tenant_manager": "views.superadmin.tenant_manager",
        "render_admin_analytics_dashboard": "views.superadmin.admin_analytics_dashboard",
        "resend_log_view": "views.superadmin.resend_log_view",
        "run_monthly_report": "views.superadmin.monthly_report_scheduler",
        "render_anomaly_dashboard": "views.superadmin.anomaly_dashboard",
        
        # Admin views
        "admin_dashboard": "views.admin.admin_dashboard",
        "billing_admin": "views.admin.billing_admin",
        "payment_admin": "views.admin.payment_admin",
        "assign_plans": "views.admin.tenant_assign_plan_view",
        "render_upload_usage_csv": "views.admin.upload_usage_csv",
        "subscription_audit_admin": "views.admin.subscription_audit_admin",
        "plan_admin_view": "views.admin.plan_admin_view",
        "usage_metric_admin": "views.admin.usage_metric_admin",
        "plan_metric_limits_admin": "views.admin.plan_metric_limits_admin",
        "admin_payment_verification": "views.admin.admin_payment_verification",
        "admin_tenant_billing_report": "views.admin.admin_billing_report",
        
        # Client views
        "client_dashboard": "views.client.client_dashboard",
        "subscription_client": "views.client.subscription_client",
        "client_billing_portal": "views.client.client_billing_portal",
        "client_usage_dashboard": "views.client.client_usage_dashboard",
        "invoice_preview": "views.client.invoice_preview",
        "client_payment_view": "views.client.client_payment_view"
    }
    
    module_path = module_map.get(view_name)
    if not module_path:
        raise ImportError(f"View {view_name} not found in module map")
    
    module = __import__(module_path, fromlist=[view_name])
    return getattr(module, view_name)

# --- Menu Definitions ---
def get_menu(role: Role) -> Dict[str, Callable]:
    """Dynamically load menu items based on role"""
    menus = {
        Role.SUPERADMIN: {
            "📊 Platform Overview": lazy_import("superadmin_dashboard"),
            "📈 Analytics Dashboard": lazy_import("render_admin_analytics_dashboard"),
            "🏢 Manage Tenants": lazy_import("tenant_manager"),
            "📜 Resend Log Viewer": lazy_import("resend_log_view"),
            "🔍 Anomaly Dashboard": lazy_import("render_anomaly_dashboard")
        },
        Role.ADMIN: {
            "📊 Dashboard": lazy_import("admin_dashboard"),
            "📦 Plan Management": lazy_import("plan_admin_view"),
            "👥 Assign Plans": lazy_import("assign_plans"),
            "📥 Upload Usage CSV": lazy_import("render_upload_usage_csv"),
            "🧾 Billing Admin": lazy_import("billing_admin"),
            "🧾 Billing Report": lazy_import("admin_tenant_billing_report"),
            "📋 Subscription Audit": lazy_import("subscription_audit_admin"),
            "📊 Usage Metrics": lazy_import("usage_metric_admin"),
            "📊 Plan Metric Limits": lazy_import("plan_metric_limits_admin"),
            "🧾 Payment Verification": lazy_import("admin_payment_verification"),
            "💳 Payment Admin": lazy_import("payment_admin"),
            "🔍 Anomaly Dashboard": lazy_import("render_anomaly_dashboard")
        },
        Role.CLIENT: {
            "📊 Dashboard": lazy_import("client_dashboard"),
            "📦 My Subscription": lazy_import("subscription_client"),
            "💳 Billing Portal": lazy_import("client_billing_portal"),
            "📈 Usage Dashboard": lazy_import("client_usage_dashboard"),
            "💳 My Payments": lazy_import("client_payment_view")
        }
    }
    return menus.get(role, {})

# --- Authentication Handlers ---
def handle_token_verification(token: str):
    """Handle email verification token"""
    result = verify_token(token)
    if result.get("success"):
        st.success("✅ Email verified successfully!")
    else:
        st.error(f"❌ {result.get('error', 'Verification failed.')}")

# --- Main Application ---
def main():
    # Initialize application
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout=PAGE_LAYOUT
    )
    init_session_state()
    
    # Custom CSS for better UI
    st.markdown("""
    <style>
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        .sidebar .sidebar-title {
            font-weight: 600;
            margin-bottom: 1rem;
        }
        .sidebar .stRadio > div {
            flex-direction: column;
            gap: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # Handle query parameters
    query_params = st.query_params
    
    # --- Authentication Routes ---
    if "verify" in query_params:
        if token := query_params.get("verify"):
            handle_token_verification(token)
        return
    
    if "token" in query_params:
        lazy_import("reset_password")()
        return
    
    if "reset" in query_params:
        lazy_import("reset_password_request")()
        return

    # --- Authentication Check ---
    if not st.session_state.get("authenticated"):
        lazy_import("auth_view")()
        return

    # --- Role-Based Routing ---
    role = st.session_state.get("role")
    try:
        role_enum = Role(role)
    except ValueError:
        st.error("🚫 Unauthorized role.")
        return

    # Get appropriate menu for the role
    menu = get_menu(role_enum)
    if not menu:
        st.error("🚫 No menu configured for this role.")
        return

    # Sidebar Navigation
    with st.sidebar:
        st.subheader(f"{'🛠️' if role_enum == Role.SUPERADMIN else '🧑‍💼' if role_enum == Role.ADMIN else '🙋'} {role_enum.value.capitalize()} Panel")
        
        # Radio navigation with icons
        selected = st.radio(
            "Navigate",
            options=list(menu.keys()),
            label_visibility="collapsed"
        )
        
        # Special actions for superadmin
        if role_enum == Role.SUPERADMIN:
            if st.button("📜 Run monthly billing", use_container_width=True):
                with st.spinner("Generating reports..."):
                    lazy_import("run_monthly_report")()
                    st.toast("Monthly billing reports generated and emailed to admins.", icon="✅")
        
        # Logout button
        if st.button("🔓 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Render the selected view
    try:
        menu[selected]()
    except Exception as e:
        st.error(f"Failed to load view: {str(e)}")
        st.stop()

if __name__ == "__main__":
    main()