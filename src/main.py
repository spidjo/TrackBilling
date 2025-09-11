import streamlit as st
from utils.session import init_session_state
from auth_manager import verify_token
from typing import Dict, Callable
from enum import Enum
import base64

# --- Constants and Configuration ---
class Role(Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    CLIENT = "client"

PAGE_TITLE = "SaaS Billing Platform"
PAGE_ICON = "💳"
PAGE_LAYOUT = "wide"

# --- Professional Theme Configuration with Burgundy Accent ---
LIGHT_THEME = {
    "PRIMARY": "#ffffff",  # White background
    "SECONDARY": "#f8f9fb",  # Very light gray
    "ACCENT": "#7b1e3a",  # Burgundy accent
    "ACCENT_DARK": "#5c162c",  # Darker burgundy for hover
    "TEXT": "#1f2937",  # Dark gray text
    "TEXT_LIGHT": "#6b7280",  # Medium gray
    "SUCCESS": "#10b981",  # Emerald
    "ERROR": "#ef4444",  # Bright red
    "WARNING": "#f59e0b",  # Amber
    "INFO": "#3b82f6",  # Blue
    "BG": "#ffffff",
    "CARD": "#ffffff",
    "BORDER": "#e5e7eb",  # Light gray border
    "SHADOW": "0 2px 10px rgba(0,0,0,0.08)",
    "SIDEBAR_HEADER": "#7b1e3a",  # Burgundy header
    "SIDEBAR_TEXT": "#ffffff",
    "BUTTON_TEXT": "#ffffff"
}

DARK_THEME = {
    "PRIMARY": "#111827",  # Dark background
    "SECONDARY": "#1f2937",
    "ACCENT": "#b22c52",  # Lighter burgundy for dark mode
    "ACCENT_DARK": "#921f42",  # Darker burgundy
    "TEXT": "#f9fafb",  # Off-white
    "TEXT_LIGHT": "#d1d5db",
    "SUCCESS": "#34d399",
    "ERROR": "#f87171",
    "WARNING": "#fbbf24",
    "INFO": "#60a5fa",
    "BG": "#111827",
    "CARD": "#1f2937",
    "BORDER": "#374151",
    "SHADOW": "0 2px 10px rgba(0,0,0,0.3)",
    "SIDEBAR_HEADER": "#7b1e3a",  # Burgundy header consistent
    "SIDEBAR_TEXT": "#ffffff",
    "BUTTON_TEXT": "#ffffff"
}

# --- Logo Setup ---
def get_logo_base64():
    logo_path = "logo.png"  # Placeholder
    try:
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

# --- Lazy Imports ---
def lazy_import(view_name: str):
    """Dynamically import views to improve startup performance"""
    module_map = {
        # Auth
        "auth_view": "views.auth.auth_view",
        "reset_password": "views.auth.reset_password",
        "reset_password_request": "views.auth.reset_password_request",

        # SuperAdmin
        "superadmin_dashboard": "views.superadmin.superadmin_dashboard",
        "tenant_manager": "views.superadmin.tenant_manager",
        "render_admin_analytics_dashboard": "views.superadmin.admin_analytics_dashboard",
        "resend_log_view": "views.superadmin.resend_log_view",
        "start_scheduler": "monthly_report_scheduler",
        "render_anomaly_dashboard": "views.superadmin.anomaly_dashboard",

        # Admin
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

        # Client
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
    menus = {
        Role.SUPERADMIN: {
            "Platform Overview": ("📊", "superadmin_dashboard"),
            "Analytics Dashboard": ("📈", "render_admin_analytics_dashboard"),
            "Manage Tenants": ("🏢", "tenant_manager"),
            "Resend Log Viewer": ("📜", "resend_log_view"),
            "Anomaly Dashboard": ("🔍", "render_anomaly_dashboard")
        },
        Role.ADMIN: {
            "Dashboard": ("📊", "admin_dashboard"),
            "Plan Management": ("📦", "plan_admin_view"),
            "Assign Plans": ("👥", "assign_plans"),
            "Upload Usage CSV": ("📥", "render_upload_usage_csv"),
            "Billing Admin": ("🧾", "billing_admin"),
            "Billing Report": ("📋", "admin_tenant_billing_report"),
            "Subscription Audit": ("📋", "subscription_audit_admin"),
            "Usage Metrics": ("📊", "usage_metric_admin"),
            "Plan Metric Limits": ("📏", "plan_metric_limits_admin"),
            "Payment Verification": ("✅", "admin_payment_verification"),
            "Payment Admin": ("💳", "payment_admin"),
            "Anomaly Dashboard": ("🔍", "render_anomaly_dashboard")
        },
        Role.CLIENT: {
            "Dashboard": ("📊", "client_dashboard"),
            "My Subscription": ("📦", "subscription_client"),
            "Billing Portal": ("💳", "client_billing_portal"),
            "Usage Dashboard": ("📈", "client_usage_dashboard"),
            "My Payments": ("💰", "client_payment_view")
        }
    }
    return menus.get(role, {})

# --- Authentication Handlers ---
def handle_token_verification(token: str):
    result = verify_token(token)
    if result.get("success"):
        st.success("✅ Email verified successfully!")
    else:
        st.error(f"❌ {result.get('error', 'Verification failed.')}")

# --- Theme Management ---
def apply_theme(theme):
    """Apply professional theme with burgundy accent"""
    st.markdown(f"""
    <style>
        html, body, .main .block-container {{
            font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
        }}

        .main .block-container {{
            background-color: {theme["BG"]};
            padding: 2rem 3rem;
            max-width: 95%;
        }}

        .sidebar .sidebar-content {{
            background-color: {theme["PRIMARY"]};
            border-right: 1px solid {theme["BORDER"]};
            padding: 1rem;
        }}

        /* Active menu item with burgundy accent */
        div[data-testid="stButton"] > button[kind="primary"] {{
            background-color: {theme["ACCENT"]} !important;
            color: {theme["BUTTON_TEXT"]} !important;
            font-weight: 500;
            border-left: 4px solid {theme["ACCENT_DARK"]} !important;
        }}

        /* Hover effects */
        div[data-testid="stButton"] > button:hover {{
            transform: translateX(4px);
            box-shadow: {theme["SHADOW"]};
        }}

        /* Buttons */
        .stButton > button {{
            background-color: {theme["ACCENT"]};
            color: {theme["BUTTON_TEXT"]};
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1.25rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }}
        .stButton > button:hover {{
            background-color: {theme["ACCENT_DARK"]};
            transform: translateY(-1px);
            box-shadow: {theme["SHADOW"]};
        }}

        h1 {{
            border-bottom: 2px solid {theme["ACCENT"]};
            padding-bottom: 0.5rem;
        }}
        h2 {{
            border-bottom: 1px solid {theme["BORDER"]};
        }}

        .stTabs > div > div > button[aria-selected="true"] {{
            color: {theme["ACCENT"]};
            border-bottom: 2px solid {theme["ACCENT"]};
        }}

        ::-webkit-scrollbar-thumb {{
            background: {theme["ACCENT"]};
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: {theme["ACCENT_DARK"]};
        }}
    </style>
    """, unsafe_allow_html=True)

# --- Main Application ---
def main():
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout=PAGE_LAYOUT,
        initial_sidebar_state="expanded"
    )
    init_session_state()

    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

    theme = DARK_THEME if st.session_state.dark_mode else LIGHT_THEME
    apply_theme(theme)

    query_params = st.query_params
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

    if not st.session_state.get("authenticated"):
        lazy_import("auth_view")()
        return

    role = st.session_state.get("role")
    try:
        role_enum = Role(role)
    except ValueError:
        st.error("🚫 Unauthorized role.")
        return

    menu = get_menu(role_enum)
    if not menu:
        st.error("🚫 No menu configured for this role.")
        return

    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = list(menu.keys())[0]

    with st.sidebar:
        logo_base64 = get_logo_base64()
        if logo_base64:
            st.markdown(
                f'<div style="text-align: center; margin-bottom: 1.5rem; padding: 1rem 0;">'
                f'<img src="data:image/png;base64,{logo_base64}" style="max-width: 180px; margin-bottom: 0.5rem;">'
                f'<h3 style="margin: 0; color: {theme["TEXT"]}; font-weight: 600;">SaaS Billing</h3>'
                f'</div>', unsafe_allow_html=True
            )
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(
                "🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode",
                key="theme_toggle",
                help="Toggle between light and dark theme",
                use_container_width=True
            ):
                st.session_state.dark_mode = not st.session_state.dark_mode
                st.rerun()

        role_icons = {Role.SUPERADMIN: "🛠️", Role.ADMIN: "👔", Role.CLIENT: "👤"}
        st.markdown(f"""
        <div style="background-color: {theme["SIDEBAR_HEADER"]}; 
                    padding: 0.75rem 1rem; 
                    border-radius: 8px; 
                    margin: 1rem 0 1.5rem 0;
                    color: {theme["SIDEBAR_TEXT"]};">
            <div style="display: flex; align-items: center; gap: 0.5rem; font-weight: 600;">
                {role_icons.get(role_enum, "👤")} {role_enum.value.capitalize()} Panel
            </div>
        </div>
        """, unsafe_allow_html=True)

        for item, (icon, view) in menu.items():
            is_active = st.session_state.selected_menu == item
            button_kind = "primary" if is_active else "secondary"
            if st.button(f"{icon} {item}", key=f"menu_{item}", use_container_width=True, type=button_kind):
                st.session_state.selected_menu = item
                st.rerun()

        if role_enum == Role.SUPERADMIN:
            if st.button("🚀 Run Monthly Billing", use_container_width=True, type="primary"):
                with st.spinner("Generating reports..."):
                    lazy_import("start_scheduler")()
                    st.toast("Monthly billing reports generated.", icon="✅")

        if st.button("🔒 Logout", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()

    st.markdown('<div class="page-transition">', unsafe_allow_html=True)
    try:
        selected_item = st.session_state.selected_menu
        view_name = menu[selected_item][1]
        view_func = lazy_import(view_name)
        st.markdown(f"""
        <div style="margin-bottom: 2rem;">
            <div style="font-size: 0.9rem; color: {theme["TEXT_LIGHT"]}; margin-bottom: 0.5rem;">
                {role_enum.value.capitalize()} Panel / {selected_item}
            </div>
            <h1>{menu[selected_item][0]} {selected_item}</h1>
        </div>
        """, unsafe_allow_html=True)
        view_func()
    except Exception as e:
        st.error(f"Failed to load view: {str(e)}")
        st.stop()
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
