import streamlit as st
from datetime import date
from typing import List, Tuple
import pandas as pd
from db.database import get_db_connection
from utils.session import init_session_state
from utils.ui_helpers import loading_spinner, show_toast

# Apply the same custom CSS as admin_dashboard.py
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
    
    .metric-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
        border-top: 4px solid;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }
    .metric-positive {
        border-top-color: var(--secondary);
    }
    .metric-neutral {
        border-top-color: var(--info);
    }
    .metric-negative {
        border-top-color: var(--danger);
    }
    .metric-warning {
        border-top-color: var(--warning);
    }
    
    .alert-card {
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-left: 4px solid;
    }
    .alert-danger {
        border-left-color: var(--danger);
        background-color: #FEE2E2;
    }
    .alert-warning {
        border-left-color: var(--warning);
        background-color: #FEF3C7;
    }
    .alert-info {
        border-left-color: var(--info);
        background-color: #DBEAFE;
    }
    .alert-success {
        border-left-color: var(--secondary);
        background-color: #D1FAE5;
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
    
    .plan-card {
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-left: 4px solid var(--info);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_active_plans_for_tenant(tenant_id: int) -> List[Tuple]:
    """Fetch active plans for a tenant."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description, monthly_fee, included_units
                FROM plans
                WHERE tenant_id = %s AND is_active = TRUE
                ORDER BY name
            """, (tenant_id,))
            return cur.fetchall()
    finally:
        conn.close()


def load_users(tenant_id: int) -> List[Tuple]:
    """Load active users for the tenant."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, first_name, last_name, email, registration_date
                FROM users
                WHERE tenant_id = %s AND is_active = 1
                ORDER BY last_name, first_name
            """, (tenant_id,))
            return cur.fetchall()
    finally:
        conn.close()


def load_current_subscriptions(tenant_id: int) -> List[Tuple]:
    """Load current subscriptions for the tenant."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    s.id,
                    u.username,
                    CONCAT(u.first_name, ' ', u.last_name) as full_name,
                    p.name as plan_name,
                    s.start_date,
                    s.end_date,
                    s.is_active
                FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                JOIN plans p ON s.plan_id = p.id
                WHERE s.tenant_id = %s
                ORDER BY s.is_active DESC, s.start_date DESC
            """, (tenant_id,))
            return cur.fetchall()
    finally:
        conn.close()


def assign_plans():
    init_session_state()

    if st.session_state.get("role") not in ["admin", "tenantadmin", "superadmin"]:
        st.warning("🔒 Access denied. Only tenant administrators can assign plans.")
        st.stop()

    st.set_page_config(page_title="Plan Assignment", layout="wide", page_icon="🏷️")
    tenant_id = st.session_state.get("tenant_id")
    current_user = st.session_state.get("user") or {}
    performed_by = current_user.get("username") or current_user.get("id") or "system"

    # Enhanced header matching admin_dashboard.py style
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">🏷️ Plan Assignment</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {date.today().strftime('%Y-%m-%d')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    with loading_spinner("Loading assignment data..."):
        users = load_users(tenant_id)

    if not users:
        st.error("No active users available for assignment")
        return

    plans = fetch_active_plans_for_tenant(tenant_id)
    if not plans:
        st.error("No active plans available for this tenant")
        return

    user_options = {f"{r[2]} {r[3]} ({r[1]})": r[0] for r in users}
    plan_options = {
        f"{r[1]} ({(r[2][:30] + '...') if r[2] else r[1]})": r[0]
        for r in plans
    }

    # Summary metrics at the top
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card metric-neutral">
            <h3>Active Users</h3>
            <h2>{len(users):,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card metric-neutral">
            <h3>Available Plans</h3>
            <h2>{len(plans):,}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # Create tabs for better organization
    tab1, tab2 = st.tabs(["📝 Assign New Plan", "📋 Current Subscriptions"])

    with tab1:
        with st.container():
            st.markdown("""
            <div class="section-header">
                <div class="icon">🔹</div>
                <h2>Assign New Plan</h2>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)

            with col1:
                selected_user_label = st.selectbox("Select User*", options=list(user_options.keys()))
                selected_user_id = user_options[selected_user_label]
                selected_user_row = next((r for r in users if r[0] == selected_user_id), None)
                if selected_user_row:
                    _, username, first_name, last_name, email, reg_date = selected_user_row
                    with st.container(border=True):
                        st.markdown(f"""
                        **User Details**  
                        👤 **Name:** {first_name} {last_name}  
                        📧 **Email:** {email}  
                        📅 **Member since:** {reg_date.strftime('%Y-%m-%d') if reg_date else 'N/A'}
                        """)

            with col2:
                selected_plan_label = st.selectbox("Select Plan*", options=list(plan_options.keys()))
                selected_plan_id = plan_options[selected_plan_label]
                selected_plan_row = next((r for r in plans if r[0] == selected_plan_id), None)
                if selected_plan_row:
                    _, pname, pdesc, monthly_fee, included_units = selected_plan_row
                    with st.container(border=True):
                        st.markdown(f"""
                        **Plan Details**  
                        💰 **Monthly Fee:** R{monthly_fee:.2f}  
                        📊 **Included Units:** {included_units:,}  
                        📝 **Description:** {(pdesc[:100] + '...') if pdesc and len(pdesc) > 100 else pdesc or 'No description'}
                        """)

            effective_date = st.date_input("Effective Date*", value=date.today(), min_value=date.today())
            
            st.markdown("""
            <div class="alert-card alert-info">
                <p><strong>Note:</strong> Duplicate checks and plan ownership will be validated when you click Assign.</p>
            </div>
            """, unsafe_allow_html=True)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                assign_btn = st.button("💾 Assign Plan", type="primary", use_container_width=True)
            with col_btn2:
                cancel_sub_btn = st.button("❌ Cancel Current Subscription", use_container_width=True)

            if assign_btn or cancel_sub_btn:
                conn = None
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()

                    if cancel_sub_btn:
                        # Handle subscription cancellation
                        cur.execute("""
                            SELECT id, plan_id, start_date
                            FROM subscriptions
                            WHERE user_id = %s AND tenant_id = %s AND is_active = TRUE
                            FOR UPDATE
                        """, (selected_user_id, tenant_id))
                        active_sub = cur.fetchone()
                        
                        if not active_sub:
                            show_toast("No active subscription found for this user.", "warning")
                        else:
                            sub_id, plan_id, start_date = active_sub
                            end_date = date.today()
                            
                            if end_date < start_date:
                                show_toast("Cannot cancel subscription before it starts.", "error")
                            else:
                                cur.execute("""
                                    UPDATE subscriptions
                                    SET end_date = %s, is_active = FALSE
                                    WHERE id = %s
                                """, (end_date, sub_id))
                                
                                cur.execute("""
                                    INSERT INTO subscription_audit (user_id, tenant_id, action, old_plan_id, new_plan_id, "timestamp")
                                    VALUES (%s, %s, %s, %s, %s, NOW())
                                """, (selected_user_id, tenant_id, 'CANCELLED', plan_id, None))
                                
                                conn.commit()
                                show_toast(f"Subscription cancelled successfully for {first_name} {last_name}", "success")
                                st.rerun()

                    if assign_btn:
                        # Check plan belongs to tenant
                        cur.execute("SELECT tenant_id FROM plans WHERE id = %s", (selected_plan_id,))
                        plan_row = cur.fetchone()
                        if not plan_row or plan_row[0] != tenant_id:
                            show_toast("Selected plan does not belong to this tenant. Operation cancelled.", "error")
                            return

                        # Check for existing active subscription to the same plan
                        cur.execute("""
                            SELECT id FROM subscriptions
                            WHERE user_id = %s AND plan_id = %s AND is_active = TRUE
                        """, (selected_user_id, selected_plan_id))
                        if cur.fetchone():
                            show_toast("User already has an active subscription to this plan. No action taken.", "warning")
                            return

                        # Check for other active subscriptions
                        cur.execute("""
                            SELECT s.id, s.plan_id, p.name, s.start_date
                            FROM subscriptions s
                            JOIN plans p ON s.plan_id = p.id
                            WHERE s.user_id = %s AND s.tenant_id = %s AND s.is_active = TRUE
                            FOR UPDATE
                        """, (selected_user_id, tenant_id))
                        existing_active = cur.fetchone()

                        if existing_active:
                            existing_sub_id, existing_plan_id, existing_plan_name, existing_start = existing_active
                            
                            # End existing subscription
                            cur.execute("""
                                UPDATE subscriptions
                                SET end_date = %s, is_active = FALSE
                                WHERE id = %s
                            """, (effective_date, existing_sub_id))

                            # Log the replacement end
                            cur.execute("""
                                INSERT INTO subscription_audit (user_id, tenant_id, action, old_plan_id, new_plan_id, "timestamp")
                                VALUES (%s, %s, %s, %s, %s, NOW())
                            """, (selected_user_id, tenant_id, 'ENDED', existing_plan_id, None))

                        # Create new subscription
                        cur.execute("""
                            INSERT INTO subscriptions (user_id, plan_id, tenant_id, start_date, is_active)
                            VALUES (%s, %s, %s, %s, TRUE)
                            RETURNING id
                        """, (selected_user_id, selected_plan_id, tenant_id, effective_date))
                        new_sub_id = cur.fetchone()[0]

                        # Log the assignment
                        cur.execute("""
                            INSERT INTO subscription_audit (user_id, tenant_id, action, old_plan_id, new_plan_id, "timestamp")
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """, (
                            selected_user_id,
                            tenant_id,
                            'ASSIGNED',
                            existing_plan_id if existing_active else None,
                            selected_plan_id
                        ))

                        conn.commit()
                        show_toast(f"Plan {'replaced' if existing_active else 'assigned'} successfully for {first_name} {last_name}", "success")
                        st.rerun()

                except Exception as e:
                    st.error(f"Error during operation: {str(e)}")
                    if conn:
                        conn.rollback()
                finally:
                    if conn:
                        conn.close()
                    # Clear cache to ensure fresh data on next load
                    try:
                        fetch_active_plans_for_tenant.clear()
                    except Exception:
                        pass

    with tab2:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📃</div>
            <h2>Current Subscriptions</h2>
        </div>
        """, unsafe_allow_html=True)
        
        subscriptions = load_current_subscriptions(tenant_id)

        if not subscriptions:
            st.info("No current subscriptions for this tenant.")
        else:
            df_subs = pd.DataFrame(subscriptions, columns=[
                "Subscription ID", "Username", "Full Name", "Plan Name", "Start Date", "End Date", "Active"
            ])
            df_subs["Start Date"] = pd.to_datetime(df_subs["Start Date"]).dt.date
            df_subs["End Date"] = pd.to_datetime(df_subs["End Date"]).dt.date
            df_subs["Active"] = df_subs["Active"].apply(lambda x: "✅" if x else "❌")

            st.dataframe(
                df_subs,
                column_config={
                    "Start Date": st.column_config.DateColumn(),
                    "End Date": st.column_config.DateColumn(),
                    "Active": st.column_config.TextColumn()
                },
                height=400,
                use_container_width=True,
                hide_index=True
            )


if __name__ == "__main__":
    assign_plans()