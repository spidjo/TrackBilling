# tenant_manager.py - Simplified and robust version
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
</style>
""", unsafe_allow_html=True)

class SimpleTenantManager:
    """Simplified tenant management class"""
    
    INDUSTRY_OPTIONS = [
        "SaaS", "Cloud", "Telecom", "FinTech", 
        "Fleet/Logistics", "Healthcare", "Education", "Other"
    ]
    
    def __init__(self):
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize session state variables"""
        if 'current_view' not in st.session_state:
            st.session_state.current_view = 'dashboard'
        if 'selected_tenant_id' not in st.session_state:
            st.session_state.selected_tenant_id = None
        if 'new_tenant_id' not in st.session_state:
            st.session_state.new_tenant_id = None
    
    # Database methods (same as before, but simplified)
    @staticmethod
    def load_tenants(include_inactive: bool = False) -> List[Tuple]:
        """Load all tenants with comprehensive data"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                where_clause = "" if include_inactive else "WHERE t.is_active = TRUE"
                
                cursor.execute(f"""
                    SELECT 
                        t.id, t.name, t.industry, t.company_name, t.email, t.phone,
                        t.is_active, COUNT(DISTINCT u.id) as user_count,
                        COUNT(DISTINCT CASE WHEN s.is_active = TRUE THEN s.id END) as active_subs
                    FROM tenants t
                    LEFT JOIN users u ON t.id = u.tenant_id
                    LEFT JOIN subscriptions s ON t.id = s.tenant_id
                    {where_clause}
                    GROUP BY t.id, t.name, t.industry, t.company_name, t.email, t.phone, t.is_active
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
                    SELECT id, name, industry, company_name, email, phone, is_active, created_at
                    FROM tenants WHERE id = %s
                """, (tenant_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0], 'name': result[1], 'industry': result[2],
                        'company_name': result[3], 'email': result[4], 'phone': result[5],
                        'is_active': result[6], 'created_at': result[7]
                    }
                return None
        except Exception as e:
            logger.error(f"Error loading tenant details: {str(e)}")
            return None
    
    @staticmethod
    def create_tenant(tenant_data: Dict[str, Any]) -> Tuple[bool, Optional[int], str]:
        """Create a new tenant"""
        try:
            if not tenant_data.get('name') or not tenant_data['name'].strip():
                return False, None, "Tenant name is required"
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check for duplicate
                cursor.execute("SELECT id FROM tenants WHERE LOWER(name) = LOWER(%s)", 
                             (tenant_data['name'].strip(),))
                if cursor.fetchone():
                    return False, None, "Tenant name already exists"
                
                # Create tenant
                cursor.execute("""
                    INSERT INTO tenants (name, industry, company_name, email, phone, is_active, created_at) 
                    VALUES (%s, %s, %s, %s, %s, TRUE, %s) RETURNING id
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
                return True, tenant_id, "Tenant created successfully"
                
        except Exception as e:
            logger.error(f"Error creating tenant: {str(e)}")
            return False, None, f"Error creating tenant: {str(e)}"
    
    @staticmethod
    def update_tenant(tenant_id: int, tenant_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update existing tenant details"""
        try:
            if not tenant_data.get('name') or not tenant_data['name'].strip():
                return False, "Tenant name is required"
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE tenants 
                    SET name = %s, industry = %s, company_name = %s, email = %s, phone = %s, updated_at = %s
                    WHERE id = %s
                """, (
                    tenant_data['name'].strip(), tenant_data['industry'],
                    tenant_data.get('company_name', tenant_data['name'].strip()),
                    tenant_data.get('email'), tenant_data.get('phone'),
                    datetime.now(timezone.utc), tenant_id
                ))
                
                conn.commit()
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
                cursor.execute("UPDATE tenants SET is_active = %s WHERE id = %s", (is_active, tenant_id))
                conn.commit()
                action = "activated" if is_active else "deactivated"
                return True, f"Tenant {action} successfully"
        except Exception as e:
            logger.error(f"Error updating tenant status: {str(e)}")
            return False, f"Error updating tenant status: {str(e)}"
    
    @staticmethod
    def create_tenant_admin(tenant_id: int, admin_data: Dict[str, Any]) -> Tuple[bool, Optional[int], Optional[str], str]:
        """Create a tenant admin user"""
        try:
            # Basic validation
            if not all([admin_data.get('first_name'), admin_data.get('last_name'), 
                       admin_data.get('email'), admin_data.get('username')]):
                return False, None, None, "All fields are required"
            
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
                
                # Create user
                cursor.execute("""
                    INSERT INTO users 
                    (tenant_id, first_name, last_name, username, password, email, role, is_active, 
                     is_verified, registration_date, company_name)
                    VALUES (%s, %s, %s, %s, %s, %s, 'admin', TRUE, TRUE, %s, %s)
                    RETURNING id
                """, (
                    tenant_id, admin_data['first_name'].strip(), admin_data['last_name'].strip(),
                    admin_data['username'].strip().lower(), 'temporary_password_123',
                    admin_data['email'].strip().lower(), now_utc, company_name
                ))
                
                user_id = cursor.fetchone()[0]
                
                # Create password reset entry
                cursor.execute("INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)",
                            (user_id, reset_token, reset_expiry))
                
                conn.commit()
                return True, user_id, reset_token, "Admin user created successfully"
                
        except Exception as e:
            logger.error(f"Error creating tenant admin: {str(e)}")
            return False, None, None, f"Error creating admin user: {str(e)}"
    
    def render_dashboard(self):
        """Simple dashboard view"""
        st.markdown("### 📊 Dashboard")
        
        tenants = self.load_tenants()
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        total_tenants = len(tenants)
        active_tenants = len([t for t in tenants if t[6]])
        total_users = sum(t[7] for t in tenants)
        total_subs = sum(t[8] for t in tenants)
        
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
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("➕ Create New Tenant", use_container_width=True):
                st.session_state.current_view = 'create_tenant'
                st.rerun()
        
        with col2:
            if st.button("👥 View All Tenants", use_container_width=True):
                st.session_state.current_view = 'tenant_list'
                st.rerun()
    
    def render_tenant_list(self):
        """Simple tenant list view"""
        st.markdown("### 👥 Tenant Directory")
        
        # Action buttons
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("Manage all tenant accounts")
        with col2:
            if st.button("➕ Create New Tenant", use_container_width=True):
                st.session_state.current_view = 'create_tenant'
                st.rerun()
        
        # Filters
        show_inactive = st.checkbox("Show Inactive Tenants", value=False)
        search_term = st.text_input("Search tenants", placeholder="Search by name or industry...")
        
        tenants = self.load_tenants(include_inactive=show_inactive)
        
        if not tenants:
            st.info("No tenants found")
            return
        
        # Filter tenants
        if search_term:
            tenants = [t for t in tenants if search_term.lower() in t[1].lower() or 
                      search_term.lower() in (t[2] or '').lower()]
        
        # Display tenants
        for tenant in tenants:
            tenant_id, name, industry, company_name, email, phone, is_active, user_count, active_subs = tenant
            
            with st.container():
                cols = st.columns([3, 1, 1, 1, 2])
                
                with cols[0]:
                    status_icon = "🟢" if is_active else "🔴"
                    st.markdown(f"**{status_icon} {name}**")
                    st.markdown(f"<span class='industry-badge'>{industry}</span>", unsafe_allow_html=True)
                
                with cols[1]:
                    st.write(f"👥 {user_count}")
                
                with cols[2]:
                    st.write(f"📊 {active_subs}")
                
                with cols[3]:
                    status_text = "Active" if is_active else "Inactive"
                    status_class = "status-active" if is_active else "status-inactive"
                    st.markdown(f"<span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)
                
                with cols[4]:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("👁️", key=f"view_{tenant_id}", help="View Details"):
                            st.session_state.selected_tenant_id = tenant_id
                            st.session_state.current_view = 'view_tenant'
                            st.rerun()
                    with col2:
                        if st.button("✏️", key=f"edit_{tenant_id}", help="Edit"):
                            st.session_state.selected_tenant_id = tenant_id
                            st.session_state.current_view = 'edit_tenant'
                            st.rerun()
                    with col3:
                        if is_active:
                            if st.button("🚫", key=f"deactivate_{tenant_id}", help="Deactivate"):
                                success, message = self.toggle_tenant_status(tenant_id, False)
                                if success:
                                    st.success(message)
                                    st.rerun()
                        else:
                            if st.button("✅", key=f"activate_{tenant_id}", help="Activate"):
                                success, message = self.toggle_tenant_status(tenant_id, True)
                                if success:
                                    st.success(message)
                                    st.rerun()
                
                st.divider()
    
    def render_tenant_form(self, tenant_data: Optional[Dict[str, Any]] = None):
        """Simple tenant form for create/edit"""
        is_edit = tenant_data is not None
        
        st.markdown(f"### {'✏️ Edit Tenant' if is_edit else '➕ Create New Tenant'}")
        
        # Back button
        if st.button("← Back to List"):
            st.session_state.current_view = 'tenant_list'
            st.session_state.selected_tenant_id = None
            st.rerun()
        
        # Simple form
        with st.form(key="tenant_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input(
                    "Tenant Name *",
                    value=tenant_data.get('name', '') if tenant_data else '',
                    placeholder="Enter tenant organization name"
                )
                industry = st.selectbox(
                    "Industry Sector *",
                    self.INDUSTRY_OPTIONS,
                    index=self.INDUSTRY_OPTIONS.index(tenant_data.get('industry', '')) 
                    if tenant_data and tenant_data.get('industry') in self.INDUSTRY_OPTIONS else 0
                )
            
            with col2:
                company_name = st.text_input(
                    "Company Legal Name",
                    value=tenant_data.get('company_name', '') if tenant_data else '',
                    placeholder="Legal company name (optional)"
                )
                contact_email = st.text_input(
                    "Contact Email",
                    value=tenant_data.get('email', '') if tenant_data else '',
                    placeholder="primary@company.com"
                )
            
            phone = st.text_input(
                "Phone Number",
                value=tenant_data.get('phone', '') if tenant_data else '',
                placeholder="+1 (555) 123-4567"
            )
            
            # Form submit button - NO key parameter
            submitted = st.form_submit_button(
                f"{'Update' if is_edit else 'Create'} Tenant",
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
                        st.success(message)
                        st.session_state.current_view = 'tenant_list'
                        st.session_state.selected_tenant_id = None
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    success, tenant_id, message = self.create_tenant(form_data)
                    if success:
                        st.success(message)
                        st.session_state.new_tenant_id = tenant_id
                        st.session_state.current_view = 'create_admin'
                        st.rerun()
                    else:
                        st.error(message)
    
    def render_tenant_details(self, tenant_id: int):
        """Simple tenant details view"""
        tenant_details = self.load_tenant_details(tenant_id)
        if not tenant_details:
            st.error("Tenant not found")
            st.session_state.current_view = 'tenant_list'
            st.rerun()
            return
        
        st.markdown(f"### 👁️ {tenant_details['name']} - Details")
        
        # Back button
        if st.button("← Back to List"):
            st.session_state.current_view = 'tenant_list'
            st.session_state.selected_tenant_id = None
            st.rerun()
        
        # Basic info
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Industry", tenant_details['industry'])
            st.metric("Company Name", tenant_details['company_name'])
            st.metric("Status", "Active" if tenant_details['is_active'] else "Inactive")
        
        with col2:
            st.metric("Contact Email", tenant_details['email'] or "Not set")
            st.metric("Phone", tenant_details['phone'] or "Not set")
            st.metric("Created", tenant_details['created_at'].strftime("%Y-%m-%d") if tenant_details['created_at'] else "Unknown")
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Edit Tenant", use_container_width=True):
                st.session_state.current_view = 'edit_tenant'
                st.rerun()
        
        with col2:
            if tenant_details['is_active']:
                if st.button("Deactivate Tenant", use_container_width=True):
                    success, message = self.toggle_tenant_status(tenant_id, False)
                    if success:
                        st.success(message)
                        st.rerun()
            else:
                if st.button("Activate Tenant", use_container_width=True):
                    success, message = self.toggle_tenant_status(tenant_id, True)
                    if success:
                        st.success(message)
                        st.rerun()
        
        with col3:
            if st.button("Add Admin", use_container_width=True):
                st.session_state.new_tenant_id = tenant_id
                st.session_state.current_view = 'create_admin'
                st.rerun()
    
    def render_admin_creation_form(self):
        """Simple admin creation form"""
        tenant_id = st.session_state.new_tenant_id
        if not tenant_id:
            st.session_state.current_view = 'tenant_list'
            st.rerun()
            return
        
        tenant_details = self.load_tenant_details(tenant_id)
        if not tenant_details:
            st.error("Tenant not found")
            st.session_state.current_view = 'tenant_list'
            st.rerun()
            return
        
        st.markdown(f"### 👨‍💼 Create Admin for {tenant_details['name']}")
        
        # Back button
        if st.button("← Back"):
            st.session_state.current_view = 'tenant_list'
            st.session_state.new_tenant_id = None
            st.rerun()
        
        with st.form(key="admin_form"):
            st.info("Create the first administrator account for this tenant.")
            
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name *", placeholder="Admin's first name")
                email = st.text_input("Email Address *", placeholder="admin@company.com")
            with col2:
                last_name = st.text_input("Last Name *", placeholder="Admin's last name")
                username = st.text_input("Username *", placeholder="Choose a username")
            
            col1, col2 = st.columns(2)
            with col1:
                create_btn = st.form_submit_button("Create Admin & Send Invitation", use_container_width=True)
            with col2:
                skip_btn = st.form_submit_button("Skip for Now", use_container_width=True)
            
            if create_btn:
                admin_data = {
                    'first_name': first_name, 'last_name': last_name,
                    'email': email, 'username': username
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
                        st.success("Tenant Admin created successfully! Invitation email sent.")
                    else:
                        st.warning("Admin created but invitation email failed to send.")
                    
                    st.session_state.current_view = 'tenant_list'
                    st.session_state.new_tenant_id = None
                    st.rerun()
                else:
                    st.error(message)
            
            if skip_btn:
                st.session_state.current_view = 'tenant_list'
                st.session_state.new_tenant_id = None
                st.info("Tenant created without admin. You can add admins later.")
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
        
        # Simple view routing
        if st.session_state.current_view == 'create_tenant':
            self.render_tenant_form()
        elif st.session_state.current_view == 'edit_tenant':
            if st.session_state.selected_tenant_id:
                tenant_data = self.load_tenant_details(st.session_state.selected_tenant_id)
                if tenant_data:
                    self.render_tenant_form(tenant_data)
                else:
                    st.error("Tenant not found")
                    st.session_state.current_view = 'tenant_list'
                    st.rerun()
            else:
                st.session_state.current_view = 'tenant_list'
                st.rerun()
        elif st.session_state.current_view == 'view_tenant':
            if st.session_state.selected_tenant_id:
                self.render_tenant_details(st.session_state.selected_tenant_id)
            else:
                st.session_state.current_view = 'tenant_list'
                st.rerun()
        elif st.session_state.current_view == 'create_admin':
            self.render_admin_creation_form()
        elif st.session_state.current_view == 'tenant_list':
            self.render_tenant_list()
        else:  # dashboard
            self.render_dashboard()

def tenant_manager():
    """Main entry point"""
    manager = SimpleTenantManager()
    manager.main()

if __name__ == "__main__":
    tenant_manager()