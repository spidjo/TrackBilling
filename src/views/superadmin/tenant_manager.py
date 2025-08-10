import streamlit as st
from db.database import get_db_connection
from utils.session_guard import require_login

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
            GROUP BY t.id
            ORDER BY t.name
        """)
        return cursor.fetchall()

def create_tenant(name, industry):
    """Create a new tenant with validation"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tenants (name, industry) VALUES (%s, %s) RETURNING id", 
            (name, industry)
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

def tenant_manager():
    """Main tenant management interface"""
    require_login('superadmin')
    st.set_page_config(page_title="🏢 Tenant Management", layout="wide")
    
    st.title("🏢 Tenant Management")
    st.markdown("Manage all tenant accounts and their configurations")
    
    # Load tenant data
    tenants = load_tenants()
    tenant_options = {f"{t[1]} (ID: {t[0]})": t for t in tenants}
    
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
            
            # Form submission
            submitted = st.form_submit_button(
                "💾 Save Tenant",
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
                            st.toast("✅ Tenant updated successfully", icon="✅")
                        else:
                            create_tenant(name.strip(), industry)
                            st.toast("✅ Tenant created successfully", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving tenant: {str(e)}")
    
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
                    st.markdown(f"👤 {user_count}")
                with cols[2]:
                    st.markdown(f"📊 {active_subs}")
                with cols[3]:
                    if st.button("✏️ Edit", key=f"edit_{tenant_id}"):
                        st.session_state.edit_tenant = tenant_id
                        st.rerun()
                with cols[4]:
                    if st.button("🗑️ Delete", key=f"del_{tenant_id}"):
                        delete_tenant(tenant_id)
                        st.toast("✅ Tenant marked as inactive", icon="✅")
                        st.rerun()
                
                st.divider()

if __name__ == "__main__":
    tenant_manager()