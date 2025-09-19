# tenant_manager.py - Recreated with proper UTF-8 encoding
import streamlit as st
from db.database import get_db_connection
from utils.session_guard import require_login
import secrets
import re
from datetime import datetime, timedelta, timezone
from utils.email_service import send_admin_invitation_email


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
</style>
""", unsafe_allow_html=True)

def load_tenants():
    """Load all tenants with additional relevant data"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.name, t.industry, 
                   COUNT(DISTINCT u.id) as user_count,
                   COUNT(DISTINCT s.id) as active_subs
            FROM tenants t
            LEFT JOIN users u ON t.id = u.tenant_id
            LEFT JOIN subscriptions s ON t.id = s.tenant_id AND s.is_active = TRUE
            WHERE t.is_active = TRUE
            GROUP BY t.id
            ORDER BY t.name
        """)
        return cursor.fetchall()

def create_tenant(name, industry, company_name=None, email=None, phone=None):
    """Create a new tenant with validation"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tenants (name, industry, company_name, email, phone, is_active) VALUES (%s, %s, %s, %s, %s, TRUE) RETURNING id", 
            (name, industry, company_name, email, phone)
        )
        tenant_id = cursor.fetchone()[0]
        conn.commit()
        return tenant_id

def update_tenant(tenant_id, name, industry):
    """Update existing tenant details"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tenants SET name = %s, industry = %s WHERE id = %s",
            (name, industry, tenant_id)
        )
        conn.commit()

def delete_tenant(tenant_id):
    """Soft delete a tenant (mark as inactive)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tenants SET is_active = FALSE WHERE id = %s",
            (tenant_id,)
        )
        conn.commit()

def create_tenant_admin(tenant_id, first_name, last_name, email, username):
    """Create a tenant admin user with verification token AND password reset token"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get the tenant's company name
        cursor.execute("SELECT company_name FROM tenants WHERE id = %s", (tenant_id,))
        tenant_result = cursor.fetchone()
        company_name = tenant_result[0] if tenant_result else None
        
        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        
        # Generate password reset token (1 hour expiry)
        password_reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Create user with temporary password and verification token
        cursor.execute("""
            INSERT INTO users 
            (tenant_id, first_name, last_name, username, password, email, role, is_active, 
             verification_token, token_timestamp, is_verified, registration_date, company_name)
            VALUES (%s, %s, %s, %s, 'password123', %s, 'admin', 1, %s, NOW(), 0, CURRENT_TIMESTAMP, %s)
            RETURNING id
        """, (tenant_id, first_name, last_name, username, email, verification_token, company_name))
        
        user_id = cursor.fetchone()[0]
        
        # Insert password reset token
        cursor.execute("""
            INSERT INTO password_resets (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (user_id, password_reset_token, expires_at))
        
        conn.commit()
        
        return user_id, verification_token, password_reset_token

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_username(username):
    """Validate username format"""
    pattern = r'^[a-zA-Z0-9_]{3,50}$'
    return re.match(pattern, username) is not None

def send_admin_invite_email(email, first_name, verification_token, tenant_name):
    """Send invitation email to tenant admin"""
    try:
        # Send email using the enhanced email service
        success = send_admin_invitation_email(
            to_email=email,
            username=first_name,
            token=verification_token,
            tenant_name=tenant_name
        )
        return success
    except Exception as e:
        st.error(f"Failed to send invitation email: {str(e)}")
        return False

def tenant_manager():
    """Main tenant management interface"""
    require_login('superadmin')
    st.set_page_config(page_title="Tenant Management", layout="wide")
    
    st.title("Tenant Management")
    st.markdown("Manage all tenant accounts and their configurations")
    
    # Load tenant data
    tenants = load_tenants()
    tenant_options = {f"{t[1]} (ID: {t[0]})": t for t in tenants}
    
    # Initialize session state for admin creation
    if 'show_admin_form' not in st.session_state:
        st.session_state.show_admin_form = False
    if 'new_tenant_id' not in st.session_state:
        st.session_state.new_tenant_id = None
    
    # Main form container
    with st.container():
        st.markdown("### Tenant Details")
        with st.form("tenant_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            # Tenant selection dropdown
            with col1:
                selected = st.selectbox(
                    "Select Tenant",
                    ["Create New Tenant"] + list(tenant_options.keys()),
                    help="Select existing tenant or create new one"
                )
            
            # Form fields
            if selected != "Create New Tenant":
                tenant = tenant_options[selected]
                tenant_id, name, industry, user_count, active_subs = tenant
                is_existing = True
            else:
                tenant_id, name, industry = None, "", ""
                is_existing = False
            
            with col2:
                industry_options = [
                    "SaaS", "Cloud", "Telecom", "FinTech", 
                    "Fleet/Logistics", "Healthcare", "Education", "Other"
                ]
                industry = st.selectbox(
                    "Industry Sector",
                    industry_options,
                    index=industry_options.index(industry) if industry in industry_options else 0,
                    help="Select the primary industry for this tenant"
                )
            
            name = st.text_input(
                "Tenant Name", 
                value=name,
                placeholder="Enter tenant organization name",
                help="Official name of the tenant organization"
            )
            
            # Additional tenant fields for new tenants
            if not is_existing:
                col3, col4 = st.columns(2)
                with col3:
                    company_name = st.text_input(
                        "Company Name",
                        placeholder="Enter legal company name"
                    )
                with col4:
                    contact_email = st.text_input(
                        "Contact Email",
                        placeholder="Primary contact email"
                    )
                
                col5, col6 = st.columns(2)
                with col5:
                    phone = st.text_input(
                        "Phone Number",
                        placeholder="Contact phone number"
                    )
            
            # Form submission
            submitted = st.form_submit_button(
                "Save Tenant",
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                if not name.strip():
                    st.error("Tenant name is required")
                else:
                    try:
                        if is_existing:
                            update_tenant(tenant_id, name.strip(), industry)
                            st.toast("Tenant updated successfully", icon="✅")
                        else:
                            # Create new tenant
                            new_tenant_id = create_tenant(
                                name.strip(), 
                                industry, 
                                company_name if company_name else name.strip(),
                                contact_email,
                                phone
                            )
                            st.session_state.new_tenant_id = new_tenant_id
                            st.session_state.show_admin_form = True
                            st.toast("Tenant created successfully! Please create the first Tenant Admin.", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving tenant: {str(e)}")
    
    # Admin creation form (shown after tenant creation)
    if st.session_state.show_admin_form and st.session_state.new_tenant_id:
        st.markdown("### Create First Tenant Administrator")
        with st.form("admin_form"):
            st.markdown("""
            <div class='admin-form'>
                <h4>Tenant Administrator Setup</h4>
                <p>Create the first administrator account for this tenant. This user will receive an email to set their password and verify their account.</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2) 
            with col1:
                first_name = st.text_input("First Name", placeholder="Admin's first name")
            with col2:
                last_name = st.text_input("Last Name", placeholder="Admin's last name")
            
            col3, col4 = st.columns(2)
            with col3:
                email = st.text_input("Email Address", placeholder="admin@company.com")
            with col4:
                username = st.text_input("Username", placeholder="Choose a username")
            
            admin_submitted = st.form_submit_button(
                "Create Admin & Send Invitation",
                type="secondary",
                use_container_width=True
            )
            
            if admin_submitted:
                # Validate inputs
                errors = []
                if not first_name.strip():
                    errors.append("First name is required")
                if not last_name.strip():
                    errors.append("Last name is required")
                if not email.strip() or not is_valid_email(email):
                    errors.append("Valid email address is required")
                if not username.strip() or not is_valid_username(username):
                    errors.append("Username must be 3-50 characters and contain only letters, numbers, and underscores")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        # Create admin user
                        user_id, verification_token, password_reset_token = create_tenant_admin(
                            st.session_state.new_tenant_id,
                            first_name.strip(),
                            last_name.strip(),
                            email.strip().lower(),
                            username.strip().lower()
                        )

                        # Send invitation email - use the password_reset_token for the reset link
                        success = send_admin_invite_email(
                            email.strip().lower(),
                            first_name.strip(),
                            verification_token,  # Use the verification token
                            name.strip()
                        )

                        
                        if success:
                            st.toast("Tenant Admin created successfully! Invitation email sent.", icon="✅")
                            st.session_state.show_admin_form = False
                            st.session_state.new_tenant_id = None
                            st.rerun()
                        else:
                            st.error("Failed to send invitation email. Please try again.")
                    except Exception as e:
                        if "users_username_key" in str(e):
                            st.error("Username already exists. Please choose a different username.")
                        elif "users_email_key" in str(e):
                            st.error("Email address already registered. Please use a different email.")
                        else:
                            st.error(f"Error creating admin user: {str(e)}")
    
    # Tenant list display
    st.markdown("### Tenant Directory")
    
    if not tenants:
        st.info("No tenants found in the system")
    else:
        for tenant in tenants:
            tenant_id, name, industry, user_count, active_subs = tenant
            
            with st.container():
                cols = st.columns([3, 1, 1, 1, 1])
                with cols[0]:
                    st.markdown(f"**{name}**")
                    st.markdown(f"<span class='industry-badge'>{industry}</span>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"Users: {user_count}")
                with cols[2]:
                    st.markdown(f"Subs: {active_subs}")
                with cols[3]:
                    if st.button("Edit", key=f"edit_{tenant_id}"):
                        st.session_state.edit_tenant = tenant_id
                        st.rerun()
                with cols[4]:
                    if st.button("Delete", key=f"del_{tenant_id}"):
                        delete_tenant(tenant_id)
                        st.toast("Tenant marked as inactive", icon="✅")
                        st.rerun()
                
                st.divider()

if __name__ == "__main__":
    tenant_manager()