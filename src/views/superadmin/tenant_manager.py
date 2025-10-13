# tenant_manager.py - Refactored with enhanced robustness and superadmin features
import streamlit as st
from db.database import get_db_connection
from utils.session_guard import require_login
import secrets
import re
from datetime import datetime, timedelta, timezone
from utils.email_service import APP_NAME, APP_URL, send_admin_invitation_email
from typing import Optional, Dict, Any, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom CSS for styling
st.markdown("""
<style>
    .tenant-card {
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #4CAF50;
    }
    .tenant-form {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    .industry-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        background-color: #e3f2fd;
        color: #1976d2;
    }
    .admin-form {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #b3d9ff;
        margin: 1rem 0;
    }
    .status-active {
        color: #10B981;
        font-weight: 600;
    }
    .status-inactive {
        color: #EF4444;
        font-weight: 600;
    }
    .warning-banner {
        background-color: #FEF3C7;
        border: 1px solid #F59E0B;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class TenantManager:
    """Enhanced tenant management class with robust error handling"""
    
    INDUSTRY_OPTIONS = [
        "SaaS", "Cloud", "Telecom", "FinTech", 
        "Fleet/Logistics", "Healthcare", "Education", "Other"
    ]
    
    def __init__(self):
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize session state variables"""
        defaults = {
            'show_admin_form': False,
            'new_tenant_id': None,
            'edit_tenant_id': None,
            'view_tenant_id': None,
            'current_tab': 'manage'
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format with comprehensive checks"""
        if not email or not isinstance(email, str):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email.strip()) is not None
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username or not isinstance(username, str):
            return False
        
        pattern = r'^[a-zA-Z0-9_]{3,50}$'
        return re.match(pattern, username.strip()) is not None
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format (basic international format)"""
        if not phone:
            return True  # Phone is optional
        
        pattern = r'^[\+]?[0-9\s\-\(\)]{10,15}$'
        return re.match(pattern, phone.strip()) is not None
    
    @staticmethod
    def load_tenants(include_inactive: bool = False) -> List[Tuple]:
        """Load all tenants with comprehensive data"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                where_clause = "" if include_inactive else "WHERE t.is_active = TRUE"
                
                cursor.execute(f"""
                    SELECT 
                        t.id, 
                        t.name, 
                        t.industry,
                        t.company_name,
                        t.email,
                        t.phone,
                        t.is_active,
                        t.created_at,
                        COUNT(DISTINCT u.id) as user_count,
                        COUNT(DISTINCT s.id) as active_subs,
                        COUNT(DISTINCT CASE WHEN s.is_active = TRUE THEN s.id END) as total_active_subs,
                        MAX(u.last_login) as last_activity
                    FROM tenants t
                    LEFT JOIN users u ON t.id = u.tenant_id
                    LEFT JOIN subscriptions s ON t.id = s.tenant_id
                    {where_clause}
                    GROUP BY t.id, t.name, t.industry, t.company_name, t.email, t.phone, t.is_active, t.created_at
                    ORDER BY t.name
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error loading tenants: {str(e)}")
            st.error(f"Failed to load tenant data: {str(e)}")
            return []
    
    @staticmethod
    def load_tenant_details(tenant_id: int) -> Optional[Dict[str, Any]]:
        """Load detailed information for a specific tenant"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        id, name, industry, company_name, email, phone, 
                        is_active, created_at, updated_at
                    FROM tenants 
                    WHERE id = %s
                """, (tenant_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'name': result[1],
                        'industry': result[2],
                        'company_name': result[3],
                        'email': result[4],
                        'phone': result[5],
                        'is_active': result[6],
                        'created_at': result[7],
                        'updated_at': result[8]
                    }
                return None
        except Exception as e:
            logger.error(f"Error loading tenant details: {str(e)}")
            return None
    
    @staticmethod
    def create_tenant(tenant_data: Dict[str, Any]) -> Tuple[bool, Optional[int], str]:
        """Create a new tenant with comprehensive validation"""
        try:
            # Validate required fields
            if not tenant_data.get('name') or not tenant_data['name'].strip():
                return False, None, "Tenant name is required"
            
            if not tenant_data.get('industry'):
                return False, None, "Industry sector is required"
            
            # Validate email if provided
            if tenant_data.get('email') and not TenantManager.validate_email(tenant_data['email']):
                return False, None, "Invalid email format"
            
            # Validate phone if provided
            if tenant_data.get('phone') and not TenantManager.validate_phone(tenant_data['phone']):
                return False, None, "Invalid phone number format"
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check for duplicate tenant name
                cursor.execute("SELECT id FROM tenants WHERE LOWER(name) = LOWER(%s)", 
                             (tenant_data['name'].strip(),))
                if cursor.fetchone():
                    return False, None, "Tenant name already exists"
                
                # Create tenant
                cursor.execute("""
                    INSERT INTO tenants 
                    (name, industry, company_name, email, phone, is_active, created_at) 
                    VALUES (%s, %s, %s, %s, %s, TRUE, %s) 
                    RETURNING id
                """, (
                    tenant_data['name'].strip(),
                    tenant_data['industry'],
                    tenant_data.get('company_name', tenant_data['name'].strip()),
                    tenant_data.get('email'),
                    tenant_data.get('phone'),
                    datetime.now(timezone.utc)
                ))
                
                tenant_id = cursor.fetchone()[0]
                conn.commit()
                
                logger.info(f"Created new tenant: {tenant_data['name']} (ID: {tenant_id})")
                return True, tenant_id, "Tenant created successfully"
                
        except Exception as e:
            logger.error(f"Error creating tenant: {str(e)}")
            return False, None, f"Error creating tenant: {str(e)}"
    
    @staticmethod
    def update_tenant(tenant_id: int, tenant_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update existing tenant details"""
        try:
            # Validate required fields
            if not tenant_data.get('name') or not tenant_data['name'].strip():
                return False, "Tenant name is required"
            
            if not tenant_data.get('industry'):
                return False, "Industry sector is required"
            
            # Validate email if provided
            if tenant_data.get('email') and not TenantManager.validate_email(tenant_data['email']):
                return False, "Invalid email format"
            
            # Validate phone if provided
            if tenant_data.get('phone') and not TenantManager.validate_phone(tenant_data['phone']):
                return False, "Invalid phone number format"
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check for duplicate tenant name (excluding current tenant)
                cursor.execute("""
                    SELECT id FROM tenants 
                    WHERE LOWER(name) = LOWER(%s) AND id != %s
                """, (tenant_data['name'].strip(), tenant_id))
                
                if cursor.fetchone():
                    return False, "Another tenant with this name already exists"
                
                # Update tenant
                cursor.execute("""
                    UPDATE tenants 
                    SET name = %s, industry = %s, company_name = %s, 
                        email = %s, phone = %s, updated_at = %s
                    WHERE id = %s
                """, (
                    tenant_data['name'].strip(),
                    tenant_data['industry'],
                    tenant_data.get('company_name', tenant_data['name'].strip()),
                    tenant_data.get('email'),
                    tenant_data.get('phone'),
                    datetime.now(timezone.utc),
                    tenant_id
                ))
                
                conn.commit()
                logger.info(f"Updated tenant ID {tenant_id}")
                return True, "Tenant updated successfully"
                
        except Exception as e:
            logger.error(f"Error updating tenant: {str(e)}")
            return False, f"Error updating tenant: {str(e)}"
    
    @staticmethod
    def toggle_tenant_status(tenant_id: int, is_active: bool) -> Tuple[bool, str]:
        """Activate or deactivate a tenant"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE tenants 
                    SET is_active = %s, updated_at = %s 
                    WHERE id = %s
                """, (is_active, datetime.now(timezone.utc), tenant_id))
                
                conn.commit()
                
                action = "activated" if is_active else "deactivated"
                logger.info(f"Tenant ID {tenant_id} {action}")
                return True, f"Tenant {action} successfully"
                
        except Exception as e:
            logger.error(f"Error updating tenant status: {str(e)}")
            return False, f"Error updating tenant status: {str(e)}"
    
    @staticmethod
    def create_tenant_admin(tenant_id: int, admin_data: Dict[str, Any]) -> Tuple[bool, Optional[int], Optional[str], str]:
        """Create a tenant admin user with comprehensive validation"""
        try:
            # Validate inputs
            errors = []
            if not admin_data.get('first_name') or not admin_data['first_name'].strip():
                errors.append("First name is required")
            if not admin_data.get('last_name') or not admin_data['last_name'].strip():
                errors.append("Last name is required")
            if not admin_data.get('email') or not TenantManager.validate_email(admin_data['email']):
                errors.append("Valid email address is required")
            if not admin_data.get('username') or not TenantManager.validate_username(admin_data['username']):
                errors.append("Username must be 3-50 characters and contain only letters, numbers, and underscores")
            
            if errors:
                return False, None, None, "; ".join(errors)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get tenant details
                cursor.execute("SELECT name, company_name FROM tenants WHERE id = %s", (tenant_id,))
                tenant_result = cursor.fetchone()
                if not tenant_result:
                    return False, None, None, "Tenant not found"
                
                tenant_name, company_name = tenant_result
                
                # Check for existing username or email
                cursor.execute("SELECT id FROM users WHERE username = %s", (admin_data['username'].strip().lower(),))
                if cursor.fetchone():
                    return False, None, None, "Username already exists"
                
                cursor.execute("SELECT id FROM users WHERE email = %s", (admin_data['email'].strip().lower(),))
                if cursor.fetchone():
                    return False, None, None, "Email address already registered"
                
                # Generate password reset token
                reset_token = secrets.token_urlsafe(32)
                now_utc = datetime.now(timezone.utc)
                reset_expiry = now_utc + timedelta(hours=24)
                
                # Create user as verified immediately
                cursor.execute("""
                    INSERT INTO users 
                    (tenant_id, first_name, last_name, username, password, email, role, is_active, 
                     is_verified, registration_date, company_name)
                    VALUES (%s, %s, %s, %s, %s, %s, 'admin', TRUE, TRUE, %s, %s)
                    RETURNING id
                """, (
                    tenant_id,
                    admin_data['first_name'].strip(),
                    admin_data['last_name'].strip(),
                    admin_data['username'].strip().lower(),
                    'temporary_password_123',  # Will be reset via email
                    admin_data['email'].strip().lower(),
                    now_utc,
                    company_name
                ))
                
                user_id = cursor.fetchone()[0]
                
                # Create password reset entry
                cursor.execute("""
                    INSERT INTO password_resets (user_id, token, expires_at)
                    VALUES (%s, %s, %s)
                """, (user_id, reset_token, reset_expiry))
                
                conn.commit()
                logger.info(f"Created admin user {user_id} for tenant {tenant_id}")
                
                return True, user_id, reset_token, "Admin user created successfully"
                
        except Exception as e:
            logger.error(f"Error creating tenant admin: {str(e)}")
            return False, None, None, f"Error creating admin user: {str(e)}"
    
    def render_tenant_form(self, tenant_data: Optional[Dict[str, Any]] = None):
        """Render the tenant creation/editing form"""
        is_edit = tenant_data is not None
        
        with st.form(f"tenant_form_{'edit' if is_edit else 'new'}", clear_on_submit=not is_edit):
            st.markdown(f"### {'Edit' if is_edit else 'Create New'} Tenant")
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input(
                    "Tenant Name *",
                    value=tenant_data.get('name', '') if tenant_data else '',
                    placeholder="Enter tenant organization name",
                    help="Official name of the tenant organization"
                )
                
                industry = st.selectbox(
                    "Industry Sector *",
                    self.INDUSTRY_OPTIONS,
                    index=self.INDUSTRY_OPTIONS.index(tenant_data.get('industry', '')) 
                    if tenant_data and tenant_data.get('industry') in self.INDUSTRY_OPTIONS else 0,
                    help="Select the primary industry for this tenant"
                )
            
            with col2:
                company_name = st.text_input(
                    "Company Legal Name",
                    value=tenant_data.get('company_name', '') if tenant_data else '',
                    placeholder="Enter legal company name (optional)",
                    help="Legal company name for contracts and billing"
                )
                
                contact_email = st.text_input(
                    "Contact Email",
                    value=tenant_data.get('email', '') if tenant_data else '',
                    placeholder="primary@company.com",
                    help="Primary contact email for administrative communications"
                )
            
            phone = st.text_input(
                "Phone Number",
                value=tenant_data.get('phone', '') if tenant_data else '',
                placeholder="+1 (555) 123-4567",
                help="Primary contact phone number (optional)"
            )
            
            submitted = st.form_submit_button(
                f"{'Update' if is_edit else 'Create'} Tenant",
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                form_data = {
                    'name': name,
                    'industry': industry,
                    'company_name': company_name,
                    'email': contact_email,
                    'phone': phone
                }
                
                if is_edit:
                    success, message = self.update_tenant(tenant_data['id'], form_data)
                    if success:
                        st.toast(message, icon="✅")
                        st.session_state.edit_tenant_id = None
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    success, tenant_id, message = self.create_tenant(form_data)
                    if success:
                        st.toast(message, icon="✅")
                        st.session_state.new_tenant_id = tenant_id
                        st.session_state.show_admin_form = True
                        st.rerun()
                    else:
                        st.error(message)
    
    def render_admin_creation_form(self):
        """Render the admin user creation form"""
        tenant_id = st.session_state.new_tenant_id
        if not tenant_id:
            return
        
        tenant_details = self.load_tenant_details(tenant_id)
        if not tenant_details:
            st.error("Tenant not found")
            return
        
        st.markdown("### Create Tenant Administrator")
        
        with st.form("admin_form"):
            st.markdown(f"""
            <div class='admin-form'>
                <h4>👨‍💼 Administrator Setup for {tenant_details['name']}</h4>
                <p>Create the first administrator account for this tenant. The admin will receive an email to set their password.</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name *", placeholder="Admin's first name")
            with col2:
                last_name = st.text_input("Last Name *", placeholder="Admin's last name")
            
            col3, col4 = st.columns(2)
            with col3:
                email = st.text_input("Email Address *", placeholder="admin@company.com")
            with col4:
                username = st.text_input("Username *", placeholder="Choose a username")
            
            col5, col6 = st.columns(2)
            with col5:
                admin_submitted = st.form_submit_button(
                    "Create Admin & Send Invitation",
                    type="secondary",
                    use_container_width=True
                )
            with col6:
                if st.form_submit_button("Skip for Now", use_container_width=True):
                    st.session_state.show_admin_form = False
                    st.session_state.new_tenant_id = None
                    st.toast("Tenant created without admin. You can add admins later.", icon="ℹ️")
                    st.rerun()
            
            if admin_submitted:
                admin_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'username': username
                }
                
                success, user_id, reset_token, message = self.create_tenant_admin(tenant_id, admin_data)
                
                if success:
                    # Send invitation email
                    email_success = send_admin_invitation_email(
                        to_email=email.strip().lower(),
                        username=first_name.strip(),
                        token=reset_token,
                        tenant_name=tenant_details['name']
                    )
                    
                    if email_success:
                        st.toast("Tenant Admin created successfully! Invitation email sent.", icon="✅")
                    else:
                        st.warning("Admin created but invitation email failed to send. Please manually send the password reset link.")
                    
                    st.session_state.show_admin_form = False
                    st.session_state.new_tenant_id = None
                    st.rerun()
                else:
                    st.error(message)
    
    def render_tenant_list(self):
        """Render the tenant directory with enhanced features"""
        st.markdown("### Tenant Directory")
        
        # Filters
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            show_inactive = st.checkbox("Show Inactive Tenants", value=False)
        with col2:
            search_term = st.text_input("Search tenants", placeholder="Search by name or industry...")
        with col3:
            if st.button("Refresh", use_container_width=True):
                st.rerun()
        
        tenants = self.load_tenants(include_inactive=show_inactive)
        
        if not tenants:
            st.info("No tenants found")
            return
        
        # Filter tenants based on search
        if search_term:
            tenants = [t for t in tenants if search_term.lower() in t[1].lower() or 
                      search_term.lower() in (t[2] or '').lower()]
        
        for tenant in tenants:
            (tenant_id, name, industry, company_name, email, phone, 
             is_active, created_at, user_count, active_subs, total_active_subs, last_activity) = tenant
            
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 2])
                
                with col1:
                    status_icon = "🟢" if is_active else "🔴"
                    st.markdown(f"**{status_icon} {name}**")
                    st.markdown(f"<span class='industry-badge'>{industry}</span>", unsafe_allow_html=True)
                    if company_name and company_name != name:
                        st.caption(f"Legal: {company_name}")
                
                with col2:
                    st.markdown(f"👥 {user_count}")
                    st.caption("Users")
                
                with col3:
                    st.markdown(f"📊 {total_active_subs}")
                    st.caption("Active Subs")
                
                with col4:
                    status_class = "status-active" if is_active else "status-inactive"
                    status_text = "Active" if is_active else "Inactive"
                    st.markdown(f"<span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)
                
                with col5:
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("👁️", key=f"view_{tenant_id}", help="View Details"):
                            st.session_state.view_tenant_id = tenant_id
                    with btn_col2:
                        if st.button("✏️", key=f"edit_{tenant_id}", help="Edit Tenant"):
                            st.session_state.edit_tenant_id = tenant_id
                    with btn_col3:
                        if is_active:
                            if st.button("🚫", key=f"deactivate_{tenant_id}", help="Deactivate"):
                                success, message = self.toggle_tenant_status(tenant_id, False)
                                if success:
                                    st.toast(message, icon="✅")
                                    st.rerun()
                                else:
                                    st.error(message)
                        else:
                            if st.button("✅", key=f"activate_{tenant_id}", help="Activate"):
                                success, message = self.toggle_tenant_status(tenant_id, True)
                                if success:
                                    st.toast(message, icon="✅")
                                    st.rerun()
                                else:
                                    st.error(message)
                
                st.divider()
    
    def render_tenant_detail_view(self, tenant_id: int):
        """Render detailed view of a tenant"""
        tenant_details = self.load_tenant_details(tenant_id)
        if not tenant_details:
            st.error("Tenant not found")
            return
        
        st.markdown("### Tenant Details")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"#### {tenant_details['name']}")
        with col2:
            if st.button("← Back to List", use_container_width=True):
                st.session_state.view_tenant_id = None
                st.rerun()
        
        # Basic info
        st.markdown("#### Basic Information")
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.metric("Industry", tenant_details['industry'])
            st.metric("Company Name", tenant_details['company_name'])
            st.metric("Status", "Active" if tenant_details['is_active'] else "Inactive")
        
        with info_col2:
            st.metric("Contact Email", tenant_details['email'] or "Not set")
            st.metric("Phone", tenant_details['phone'] or "Not set")
            st.metric("Created", tenant_details['created_at'].strftime("%Y-%m-%d") if tenant_details['created_at'] else "Unknown")
        
        # Action buttons
        st.markdown("#### Actions")
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("Edit Tenant Details", use_container_width=True):
                st.session_state.edit_tenant_id = tenant_id
                st.session_state.view_tenant_id = None
                st.rerun()
        
        with action_col2:
            if tenant_details['is_active']:
                if st.button("Deactivate Tenant", use_container_width=True):
                    success, message = self.toggle_tenant_status(tenant_id, False)
                    if success:
                        st.toast(message, icon="✅")
                        st.rerun()
            else:
                if st.button("Activate Tenant", use_container_width=True):
                    success, message = self.toggle_tenant_status(tenant_id, True)
                    if success:
                        st.toast(message, icon="✅")
                        st.rerun()
        
        with action_col3:
            if st.button("Add New Admin", use_container_width=True):
                st.session_state.new_tenant_id = tenant_id
                st.session_state.show_admin_form = True
                st.session_state.view_tenant_id = None
                st.rerun()
    
    def render_dashboard(self):
        """Render the main dashboard view"""
        st.markdown("### Tenant Management Dashboard")
        
        tenants = self.load_tenants()
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_tenants = len(tenants)
        active_tenants = len([t for t in tenants if t[6]])  # is_active field
        total_users = sum(t[8] for t in tenants)  # user_count field
        total_subs = sum(t[10] for t in tenants)  # total_active_subs field
        
        with col1:
            st.metric("Total Tenants", total_tenants)
        with col2:
            st.metric("Active Tenants", active_tenants)
        with col3:
            st.metric("Total Users", total_users)
        with col4:
            st.metric("Active Subscriptions", total_subs)
        
        # Quick actions
        st.markdown("#### Quick Actions")
        quick_col1, quick_col2, quick_col3 = st.columns(3)
        
        with quick_col1:
            if st.button("➕ Create New Tenant", use_container_width=True):
                st.session_state.edit_tenant_id = None
                st.rerun()
        
        with quick_col2:
            if st.button("📊 View All Tenants", use_container_width=True):
                st.session_state.current_tab = 'manage'
                st.rerun()
        
        with quick_col3:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
    
    def main(self):
        """Main tenant management interface"""
        require_login('superadmin')
        
        st.set_page_config(
            page_title="Tenant Management", 
            layout="wide",
            page_icon="🏢"
        )
        
        st.title("🏢 Tenant Management")
        st.markdown("Comprehensive tenant account management and configuration")
        
        # Tab navigation
        tab1, tab2 = st.tabs(["📊 Dashboard", "👥 Tenant Management"])
        
        with tab1:
            self.render_dashboard()
        
        with tab2:
            # Handle different view states
            if st.session_state.show_admin_form and st.session_state.new_tenant_id:
                self.render_admin_creation_form()
            
            elif st.session_state.edit_tenant_id:
                tenant_details = self.load_tenant_details(st.session_state.edit_tenant_id)
                if tenant_details:
                    self.render_tenant_form(tenant_details)
                else:
                    st.error("Tenant not found")
                    st.session_state.edit_tenant_id = None
            
            elif st.session_state.view_tenant_id:
                self.render_tenant_detail_view(st.session_state.view_tenant_id)
            
            else:
                # Main management view
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("### Tenant Management")
                with col2:
                    if st.button("➕ Create New Tenant", use_container_width=True):
                        st.session_state.edit_tenant_id = None  # Ensure we're in create mode
                
                self.render_tenant_list()

def tenant_manager():
    """Main entry point for the tenant manager"""
    manager = TenantManager()
    manager.main()

if __name__ == "__main__":
    tenant_manager()