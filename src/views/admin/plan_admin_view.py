# src/views/admin/plan_admin_view.py
import streamlit as st
from decimal import Decimal
from db.database import get_db_connection
from utils.session_guard import require_login
from utils.ui_helpers import loading_spinner, show_toast

def plan_admin_view():
    """Admin interface for managing subscription plans with enhanced UX"""
    # Page configuration
    st.set_page_config(
        page_title="Plan Management",
        layout="wide",
        page_icon="📊"
    )
    require_login('admin')

    if not st.session_state.get("user"):
        st.stop()

    # Initialize session state
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = None

    # UI Header
    st.title("📊 Plan Management")
    st.markdown("---")

    # Database connection with loading spinner
    with loading_spinner("Loading plan data..."):
        conn = get_db_connection()
        cursor = conn.cursor()
        tenant_id = st.session_state.user["tenant_id"]

    # Billing cycle options
    BILLING_CYCLES = ["Monthly", "Quarterly", "Annual"]

    # --- Add New Plan Section ---
    with st.expander("➕ Add New Plan", expanded=False):
        with st.form("add_plan_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Plan Name*", help="Required field")
                description = st.text_area("Description")
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
                    index=0
                )

            submitted = st.form_submit_button(
                "Create Plan",
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                if not name or monthly_fee <= 0:
                    show_toast("Please fill all required fields", "warning")
                else:
                    try:
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
                        show_toast("✅ New plan added successfully!", "success")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        show_toast(f"Error creating plan: {str(e)}", "error")

    # --- Existing Plans Section ---
    st.subheader("📋 Existing Plans", divider="gray")
    
    with loading_spinner("Loading plans..."):
        cursor.execute("""
            SELECT 
                id, name, description, monthly_fee, 
                included_units, overage_rate, billing_cycle, is_active
            FROM plans
            WHERE tenant_id = %s
            ORDER BY is_active DESC, monthly_fee ASC
        """, (tenant_id,))
        plans = cursor.fetchall()

    if not plans:
        st.info("No plans created yet. Add your first plan above.")
        conn.close()
        return

    # Plan cards layout
    for plan in plans:
        plan_id, name, desc, fee, units, overage, cycle, active = plan
        
        # Handle case where cycle might be None or invalid
        if cycle not in BILLING_CYCLES:
            cycle = "Monthly"  # Default value
            
        with st.container(border=True):
            # Plan header with status
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {name}")
                st.caption(f"Billing Cycle: {cycle}")
            with col2:
                status = st.empty()
                if active:
                    status.success("🟢 Active")
                else:
                    status.error("🔴 Inactive")

            # Plan details columns
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Description:** {desc or 'No description'}")
                st.markdown(f"**Monthly Fee:** R{float(fee):.2f}")
            with col2:
                st.markdown(f"**Included Units:** {int(units):,}")
                st.markdown(f"**Overage Rate:** R{float(overage):.2f}/unit")

            # Action buttons
            col1, col2, col3 = st.columns([2, 2, 3])
            with col1:
                if st.button(
                    "✏️ Edit Plan",
                    key=f"edit_{plan_id}",
                    use_container_width=True
                ):
                    st.session_state.edit_mode = plan_id
                    st.rerun()

            with col2:
                if active:
                    if st.button(
                        "❌ Deactivate",
                        key=f"deact_{plan_id}",
                        type="primary",
                        use_container_width=True
                    ):
                        try:
                            cursor.execute(
                                "UPDATE plans SET is_active = FALSE WHERE id = %s",
                                (plan_id,)
                            )
                            conn.commit()
                            show_toast("Plan deactivated", "warning")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            show_toast(f"Error deactivating plan: {str(e)}", "error")
                else:
                    if st.button(
                        "✅ Activate",
                        key=f"act_{plan_id}",
                        type="secondary",
                        use_container_width=True
                    ):
                        try:
                            cursor.execute(
                                "UPDATE plans SET is_active = TRUE WHERE id = %s",
                                (plan_id,)
                            )
                            conn.commit()
                            show_toast("Plan activated", "success")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            show_toast(f"Error activating plan: {str(e)}", "error")

            with col3:
                with st.expander("👥 Subscribers", expanded=False):
                    with loading_spinner("Loading subscribers..."):
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
                        st.caption(f"Total subscribers: {total_subs}")
                        
                        for sub in subscribers:
                            uname, start, end, sub_active, _ = sub
                            status = "🟢 Active" if sub_active else "🔴 Ended"
                            st.markdown(
                                f"- **{uname}** | "
                                f"Start: {start.strftime('%Y-%m-%d')} | "
                                f"End: {end.strftime('%Y-%m-%d') if end else 'Ongoing'} | "
                                f"{status}"
                            )
                    else:
                        st.caption("No active subscribers")

            # Edit form (shown when in edit mode)
            if st.session_state.get("edit_mode") == plan_id:
                with st.form(f"edit_form_{plan_id}"):
                    st.markdown("#### ✏️ Edit Plan Details")
                    
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
                        # Safely get index for selectbox
                        try:
                            cycle_index = BILLING_CYCLES.index(cycle)
                        except ValueError:
                            cycle_index = 0  # Default to Monthly if not found
                        
                        new_cycle = st.selectbox(
                            "Billing Cycle",
                            BILLING_CYCLES,
                            index=cycle_index
                        )

                    col1, col2, _ = st.columns([1,1,3])
                    with col1:
                        if st.form_submit_button(
                            "💾 Save Changes",
                            type="primary",
                            use_container_width=True
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
                                    WHERE id = %s
                                """, (
                                    new_name, new_desc, float(new_fee),
                                    int(new_units), float(new_overage),
                                    new_cycle, plan_id
                                ))
                                conn.commit()
                                st.session_state.edit_mode = None
                                show_toast("Plan updated successfully", "success")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                show_toast(f"Error updating plan: {str(e)}", "error")
                    
                    with col2:
                        if st.form_submit_button(
                            "❌ Cancel",
                            type="secondary",
                            use_container_width=True
                        ):
                            st.session_state.edit_mode = None
                            st.rerun()

    conn.close()

if __name__ == "__main__":
    plan_admin_view()