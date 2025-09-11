import streamlit as st
from decimal import Decimal
from db.database import get_db_connection
from utils.session import init_session_state, validate_session
from utils.ui_helpers import loading_spinner, show_toast
from datetime import datetime

# Custom CSS for professional styling
st.markdown("""
<style>
    :root {
        --primary: #4F46E5;
        --secondary: #10B981;
        --danger: #EF4444;
        --warning: #F59E0B;
        --info: #3B82F6;
        --dark: #1F2937;
        --light: #F9FAFB;
    }
    
    .plan-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
        border-left: 4px solid;
    }
    .plan-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }
    .plan-active {
        border-left-color: var(--secondary);
    }
    .plan-inactive {
        border-left-color: var(--danger);
    }
    
    .feature-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
        background-color: #E0E7FF;
        color: #4F46E5;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .section-header {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
    }
    .section-header h2 {
        color: #1F2937;
        font-weight: 700;
        margin: 0;
    }
    .section-header .icon {
        margin-right: 0.75rem;
        font-size: 1.5rem;
    }
    
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, rgba(79,70,229,0.1) 0%, rgba(79,70,229,0.5) 50%, rgba(79,70,229,0.1) 100%);
        margin: 1.5rem 0;
    }
    
    .plan-separator {
        height: 2px;
        background: linear-gradient(90deg, rgba(79,70,229,0.1) 0%, rgba(79,70,229,0.3) 50%, rgba(79,70,229,0.1) 100%);
        margin: 2rem 0;
        border-radius: 2px;
    }
    
    .stats-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    .stats-badge-primary {
        background-color: #E0E7FF;
        color: #4F46E5;
    }
    .stats-badge-success {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .stats-badge-warning {
        background-color: #FEF3C7;
        color: #92400E;
    }
</style>
""", unsafe_allow_html=True)

BILLING_CYCLES = ["Monthly", "Quarterly", "Annual"]

@st.cache_data(ttl=600)
def fetch_plans_for_tenant(tenant_id: int):
    """Cached fetch for plans belonging to a tenant."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                id, name, description, monthly_fee, 
                included_units, overage_rate, billing_cycle, is_active
            FROM plans
            WHERE tenant_id = %s
            ORDER BY is_active DESC, monthly_fee ASC
        """, (tenant_id,))
        plans = cur.fetchall()
        return plans
    finally:
        conn.close()

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"

def plan_admin_view():
    """Professional admin interface for managing subscription plans"""
    init_session_state()
    
    # Session validation with redirect
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()
        
    # Page configuration
    st.set_page_config(
        page_title="Plan Management",
        layout="wide",
        page_icon="📊"
    )

    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = None

    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">📊 Plan Management</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    tenant_id = st.session_state.tenant_id

    # Get plan statistics
    with loading_spinner("Loading plan statistics..."):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_plans,
                    SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_plans,
                    SUM(CASE WHEN is_active = FALSE THEN 1 ELSE 0 END) as inactive_plans
                FROM plans
                WHERE tenant_id = %s
            """, (tenant_id,))
            stats = cursor.fetchone()
            total_plans = stats["total_plans"] if stats else 0
            active_plans = stats["active_plans"] if stats else 0
            inactive_plans = stats["inactive_plans"] if stats else 0
        finally:
            conn.close()

    # Display plan statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card metric-neutral">
            <h3>Total Plans</h3>
            <h2>{total_plans:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card metric-positive">
            <h3>Active Plans</h3>
            <h2>{active_plans:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card metric-negative">
            <h3>Inactive Plans</h3>
            <h2>{inactive_plans:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Get subscriber count
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as total_subscribers
                FROM subscriptions 
                WHERE is_active = TRUE
                AND user_id IN (SELECT id FROM users WHERE tenant_id = %s)
            """, (tenant_id,))
            subscribers = cursor.fetchone()
            total_subscribers = subscribers["total_subscribers"] if subscribers else 0
        finally:
            conn.close()
        
        st.markdown(f"""
        <div class="metric-card metric-warning">
            <h3>Active Subscribers</h3>
            <h2>{total_subscribers:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # --- Add New Plan Section ---
    with st.expander("➕ Add New Plan", expanded=False):
        with st.form("add_plan_form", clear_on_submit=True):
            st.markdown("""
            <div class="section-header">
                <div class="icon">✨</div>
                <h2>Create New Plan</h2>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(
                    "Plan Name*",
                    help="Required field",
                    placeholder="e.g., Premium Plan"
                )
                description = st.text_area(
                    "Description",
                    placeholder="Describe the features and benefits of this plan"
                )
                monthly_fee = st.number_input(
                    "Monthly Fee (R)*",
                    min_value=0.0,
                    step=0.01,
                    value=0.0,
                    format="%.2f",
                    help="Base monthly subscription cost"
                )
            with col2:
                included_units = st.number_input(
                    "Included Units*",
                    min_value=0,
                    value=0,
                    help="Units included in base price"
                )
                overage_rate = st.number_input(
                    "Overage Rate (R/unit)*",
                    min_value=0.0,
                    step=0.01,
                    value=0.0,
                    format="%.2f",
                    help="Cost per additional unit"
                )
                billing_cycle = st.selectbox(
                    "Billing Cycle", 
                    BILLING_CYCLES, 
                    index=0,
                    help="How often customers will be billed"
                )

            submitted = st.form_submit_button(
                "Create Plan", 
                type="primary", 
                use_container_width=True
            )

            if submitted:
                if not name or monthly_fee <= 0:
                    show_toast("Please fill all required fields and set a monthly fee greater than 0", "warning")
                else:
                    conn = None
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO plans (
                                tenant_id, name, description, 
                                monthly_fee, included_units, 
                                overage_rate, billing_cycle, is_active
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                        """, (
                            tenant_id, name, description,
                            float(monthly_fee), int(included_units),
                            float(overage_rate), billing_cycle
                        ))
                        conn.commit()
                        try:
                            fetch_plans_for_tenant.clear()
                        except Exception:
                            pass
                        show_toast("✅ New plan added successfully!", "success")
                        st.rerun()
                    except Exception as e:
                        if conn:
                            conn.rollback()
                        show_toast(f"Error creating plan: {str(e)}", "error")
                    finally:
                        if conn:
                            conn.close()

    # --- Existing Plans Section ---
    st.markdown("""
    <div class="section-header">
        <div class="icon">📋</div>
        <h2>Existing Plans</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with loading_spinner("Loading plans..."):
        plans = fetch_plans_for_tenant(tenant_id)

    if not plans:
        st.info("No plans created yet. Add your first plan above.")
        return

    # Plan cards layout
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for i, plan in enumerate(plans):
            plan_id, name, desc, fee, units, overage, cycle, active = plan
            if cycle not in BILLING_CYCLES:
                cycle = "Monthly"

            # Plan card container using Streamlit components
            with st.container():
                # Card styling
                card_class = "plan-card plan-active" if active else "plan-card plan-inactive"
                st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
                
                # Card header
                header_col1, header_col2 = st.columns([4, 1])
                with header_col1:
                    st.subheader(name)
                    if desc:
                        st.caption(desc)
                with header_col2:
                    if active:
                        st.markdown("<span class='verified-badge'>🟢 Active</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span class='pending-badge'>🔴 Inactive</span>", unsafe_allow_html=True)
                
                # Plan metrics in columns
                metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                with metric_col1:
                    st.metric("Monthly Fee", format_currency(fee))
                with metric_col2:
                    st.metric("Included Units", f"{int(units):,}")
                with metric_col3:
                    st.metric("Overage Rate", f"R{float(overage):.2f}/unit")
                with metric_col4:
                    st.metric("Billing Cycle", cycle)
                
                # Action buttons
                action_col1, action_col2, action_col3 = st.columns([2, 2, 3])
                with action_col1:
                    if st.button(
                        "✏️ Edit Plan", 
                        key=f"edit_{plan_id}", 
                        use_container_width=True,
                        help="Modify this plan's details"
                    ):
                        st.session_state.edit_mode = plan_id
                        st.rerun()

                with action_col2:
                    # Activation toggle
                    if active:
                        if st.button(
                            "❌ Deactivate", 
                            key=f"deact_{plan_id}", 
                            use_container_width=True,
                            help="Disable this plan for new subscriptions"
                        ):
                            try:
                                cursor.execute(
                                    "UPDATE plans SET is_active = FALSE WHERE id = %s AND tenant_id = %s", 
                                    (plan_id, tenant_id)
                                )
                                conn.commit()
                                fetch_plans_for_tenant.clear()
                                show_toast("Plan deactivated", "warning")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                show_toast(f"Error deactivating plan: {str(e)}", "error")
                    else:
                        if st.button(
                            "✅ Activate", 
                            key=f"act_{plan_id}", 
                            use_container_width=True,
                            help="Enable this plan for new subscriptions"
                        ):
                            try:
                                cursor.execute(
                                    "UPDATE plans SET is_active = TRUE WHERE id = %s AND tenant_id = %s", 
                                    (plan_id, tenant_id)
                                )
                                conn.commit()
                                fetch_plans_for_tenant.clear()
                                show_toast("Plan activated", "success")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                show_toast(f"Error activating plan: {str(e)}", "error")

                with action_col3:
                    with st.expander("👥 Subscriber Analytics", expanded=False):
                        with loading_spinner("Loading subscriber data..."):
                            cursor.execute("""
                                SELECT 
                                    u.username, 
                                    s.start_date, 
                                    s.end_date, 
                                    s.is_active,
                                    COUNT(*) OVER() as total_count
                                FROM subscriptions s
                                JOIN users u ON u.id = s.user_id
                                WHERE s.plan_id = %s
                                ORDER BY s.is_active DESC, s.start_date DESC
                                LIMIT 50
                            """, (plan_id,))
                            subscribers = cursor.fetchall()

                        if subscribers:
                            total_subs = subscribers[0][4] if subscribers else 0
                            active_subs = sum(1 for sub in subscribers if sub[3])
                            
                            sub_col1, sub_col2 = st.columns(2)
                            with sub_col1:
                                st.metric("Total Subscribers", total_subs)
                            with sub_col2:
                                st.metric("Active Subscribers", active_subs)
                            
                            st.write("**Recent Subscribers:**")
                            for sub in subscribers[:5]:  # Show top 5
                                uname, start, end, sub_active, _ = sub
                                status_text = "🟢 Active" if sub_active else "🔴 Ended"
                                start_fmt = start.strftime('%Y-%m-%d') if start else "N/A"
                                end_fmt = end.strftime('%Y-%m-%d') if end else "Ongoing"
                                st.write(f"- **{uname}** | {start_fmt} → {end_fmt} | {status_text}")
                            
                            if total_subs > 5:
                                st.caption(f"Showing 5 of {total_subs} subscribers")
                        else:
                            st.info("No subscribers for this plan")
                
                # Edit form (shown when in edit mode)
                if st.session_state.get("edit_mode") == plan_id:
                    with st.form(f"edit_form_{plan_id}"):
                        st.markdown("""
                        <div class="section-header">
                            <div class="icon">✏️</div>
                            <h2>Edit Plan Details</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            new_name = st.text_input("Plan Name", value=name)
                            new_desc = st.text_area("Description", value=desc)
                            new_fee = st.number_input(
                                "Monthly Fee (R)", 
                                min_value=0.0, 
                                step=0.01, 
                                value=float(fee), 
                                format="%.2f"
                            )
                        with col2:
                            new_units = st.number_input(
                                "Included Units", 
                                min_value=0, 
                                value=int(units)
                            )
                            new_overage = st.number_input(
                                "Overage Rate (R/unit)", 
                                min_value=0.0, 
                                step=0.01, 
                                value=float(overage), 
                                format="%.2f"
                            )
                            try:
                                cycle_index = BILLING_CYCLES.index(cycle)
                            except ValueError:
                                cycle_index = 0
                            new_cycle = st.selectbox(
                                "Billing Cycle", 
                                BILLING_CYCLES, 
                                index=cycle_index
                            )

                        col1, col2, _ = st.columns([1,1,3])
                        with col1:
                            if st.form_submit_button(
                                "💾 Save Changes", 
                                use_container_width=True,
                                type="primary"
                            ):
                                try:
                                    cursor.execute("""
                                        UPDATE plans
                                        SET 
                                            name = %s, 
                                            description = %s, 
                                            monthly_fee = %s, 
                                            included_units = %s, 
                                            overage_rate = %s,
                                            billing_cycle = %s
                                        WHERE id = %s AND tenant_id = %s
                                    """, (
                                        new_name, new_desc, float(new_fee),
                                        int(new_units), float(new_overage),
                                        new_cycle, plan_id, tenant_id
                                    ))
                                    conn.commit()
                                    st.session_state.edit_mode = None
                                    fetch_plans_for_tenant.clear()
                                    show_toast("Plan updated successfully", "success")
                                    st.rerun()
                                except Exception as e:
                                    conn.rollback()
                                    show_toast(f"Error updating plan: {str(e)}", "error")
                        
                        with col2:
                            if st.form_submit_button(
                                "❌ Cancel", 
                                use_container_width=True
                            ):
                                st.session_state.edit_mode = None
                                st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)  # Close card div
                
                # Add separator between plans (except after the last one)
                if i < len(plans) - 1:
                    st.markdown('<div class="plan-separator"></div>', unsafe_allow_html=True)
    finally:
        conn.close()

if __name__ == "__main__":
    plan_admin_view()