# views/admin/plan_metric_limits_admin.py

import streamlit as st
from db.database import get_db_connection
from utils.session_guard import require_login

def plan_metric_limits_admin():
    st.set_page_config(
        page_title="📏 Define Plan Metric Limits", 
        layout="centered",
        page_icon="📏"
    )
    require_login('admin')

    user = st.session_state.get("user")
    tenant_id = user["tenant_id"]

    st.title("📏 Plan Metric Limits")
    st.caption("Configure usage limits and overage rates for each plan")

    # --- Database Connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Select Plan
    with st.container(border=True):
        st.subheader("1️⃣ Select Plan", divider="gray")
        cursor.execute("SELECT id, name FROM plans WHERE tenant_id = %s ORDER BY name", (tenant_id,))
        plans = cursor.fetchall()

        if not plans:
            st.warning("No plans available for your tenant.")
            conn.close()
            return

        plan = st.selectbox(
            "Choose a plan to configure", 
            plans, 
            format_func=lambda x: x[1],
            help="Select the plan you want to configure metric limits for"
        )
        plan_id = plan[0]

    # --- Load all metric types
    cursor.execute("SELECT id, name FROM usage_metrics WHERE tenant_id = %s ORDER BY name", (tenant_id,))
    all_metrics = cursor.fetchall()

    if not all_metrics:
        st.warning("No usage metrics defined yet.")
        conn.close()
        return

    # --- Show existing metric limits
    with st.container(border=True):
        st.subheader("2️⃣ Current Metric Limits", divider="gray")
        cursor.execute("""
            SELECT pml.id, mt.name, pml.metric_limit, pml.overage_rate
            FROM plan_metric_limits pml
            JOIN usage_metrics mt ON pml.metric_id = mt.id
            WHERE pml.plan_id = %s
            ORDER BY mt.name
        """, (plan_id,))
        existing_limits = cursor.fetchall()

        if existing_limits:
            st.info(f"Showing configured metrics for: **{plan[1]}** plan")
            
            cols = st.columns(3)
            with cols[0]:
                st.markdown("**Metric**")
            with cols[1]:
                st.markdown("**Included Units**")
            with cols[2]:
                st.markdown("**Overage Rate**")

            for limit_id, metric_name, metric_limit, overage_rate in existing_limits:
                with st.expander(f"⚙️ {metric_name}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_limit = st.number_input(
                            f"Included units", 
                            min_value=0, 
                            value=int(metric_limit),  # Convert to int explicitly
                            key=f"limit_{limit_id}",
                            help=f"Maximum included {metric_name} units for this plan"
                        )
                    with col2:
                        new_rate = st.number_input(
                            f"Overage rate (R/unit)", 
                            min_value=0.0, 
                            value=float(overage_rate),  # Ensure float type
                            step=0.01,
                            format="%.2f",
                            key=f"rate_{limit_id}",
                            help="Rate charged per unit over the limit"
                        )

                    if st.button("💾 Save Changes", 
                                key=f"update_{limit_id}",
                                type="primary",
                                use_container_width=True):
                        with st.spinner("Updating..."):
                            try:
                                cursor.execute("""
                                    UPDATE plan_metric_limits
                                    SET metric_limit = %s, overage_rate = %s
                                    WHERE id = %s
                                """, (new_limit, new_rate, limit_id))
                                conn.commit()
                                st.toast(f"✅ {metric_name} updated successfully", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating {metric_name}: {str(e)}")
        else:
            st.info("No metric limits defined for this plan yet.")

    # --- Add new metric limits
    with st.container(border=True):
        st.subheader("3️⃣ Add New Metric", divider="gray")
        
        # Get metrics not yet added to the selected plan
        cursor.execute("""
            SELECT id, name FROM usage_metrics 
            WHERE tenant_id = %s AND id NOT IN (
                SELECT metric_id FROM plan_metric_limits WHERE plan_id = %s
            )
            ORDER BY name
        """, (tenant_id, plan_id))
        available_metrics = cursor.fetchall()

        if not available_metrics:
            st.success("✨ All available metrics are already assigned to this plan")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                new_metric = st.selectbox(
                    "Select metric", 
                    available_metrics, 
                    format_func=lambda x: x[1],
                    help="Choose a metric to add to this plan"
                )
            with col2:
                new_limit = st.number_input(
                    "Included units", 
                    min_value=0,
                    value=1000,
                    key="add_limit",
                    help="Included units for this metric"
                )
            with col3:
                new_rate = st.number_input(
                    "Overage rate (R/unit)", 
                    min_value=0.0,
                    value=0.10,
                    step=0.01,
                    format="%.2f",
                    key="add_rate",
                    help="Rate charged per unit over the limit"
                )

            if st.button("➕ Add Metric to Plan", 
                        type="primary",
                        use_container_width=True):
                with st.spinner("Adding metric..."):
                    try:
                        cursor.execute("""
                            INSERT INTO plan_metric_limits (plan_id, metric_id, metric_limit, overage_rate)
                            VALUES (%s, %s, %s, %s)
                        """, (plan_id, new_metric[0], new_limit, new_rate))
                        conn.commit()
                        st.toast(f"✅ {new_metric[1]} added to the plan!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding metric: {str(e)}")

    conn.close()

    # Footer
    st.divider()
    st.caption("💡 Tip: Use consistent overage rates across similar plans for predictable billing")