# views/admin/plan_metric_limits_admin.py

import streamlit as st
from db.database import get_db_connection
from utils.session_guard import require_login

def plan_metric_limits_admin():
    st.set_page_config(page_title="📏 Define Plan Metric Limits", layout="centered")
    require_login('admin')

    user = st.session_state.get("user")
    tenant_id = user["tenant_id"]

    st.title("📏 Plan Metric Limits")

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Select Plan
    cursor.execute("SELECT id, name FROM plans WHERE tenant_id = ?", (tenant_id,))
    plans = cursor.fetchall()

    if not plans:
        st.warning("No plans available for your tenant.")
        conn.close()
        return

    plan = st.selectbox("Select a plan", plans, format_func=lambda x: x[1])
    plan_id = plan[0]

    # --- Load all metric types
    cursor.execute("SELECT id, name FROM usage_metrics WHERE tenant_id = ?", (tenant_id,))
    all_metrics = cursor.fetchall()

    if not all_metrics:
        st.warning("No usage metrics defined yet.")
        conn.close()
        return

    st.subheader("🔧 Configure Metric Limits")

    # --- Show existing metric limits
    cursor.execute("""
        SELECT pml.id, mt.name, pml.metric_limit, pml.overage_rate
        FROM plan_metric_limits pml
        JOIN usage_metrics mt ON pml.metric_id = mt.id
        WHERE pml.plan_id = ?
    """, (plan_id,))
    existing_limits = cursor.fetchall()

    if existing_limits:
        for limit_id, metric_name, metric_limit, overage_rate in existing_limits:
            with st.expander(f"🔹 {metric_name}"):
                new_limit = st.number_input(f"Included {metric_name} units", min_value=0, value=metric_limit, key=f"limit_{limit_id}")
                new_rate = st.number_input(f"Overage rate (R per unit)", min_value=0.0, value=overage_rate, key=f"rate_{limit_id}")

                if st.button("💾 Update", key=f"update_{limit_id}"):
                    cursor.execute("""
                        UPDATE plan_metric_limits
                        SET metric_limit = ?, overage_rate = ?
                        WHERE id = ?
                    """, (new_limit, new_rate, limit_id))
                    conn.commit()
                    st.success(f"{metric_name} updated")

    else:
        st.info("No metric limits defined for this plan yet.")

    st.divider()

    # --- Add new metric limits
    st.subheader("➕ Add Metric to Plan")

    # Get metrics not yet added to the selected plan
    cursor.execute("""
        SELECT id, name FROM usage_metrics 
        WHERE tenant_id = ? AND id NOT IN (
            SELECT metric_id FROM plan_metric_limits WHERE plan_id = ?
        )
    """, (tenant_id, plan_id))
    available_metrics = cursor.fetchall()

    if not available_metrics:
        st.info(f"All metrics are already assigned to this plan. Plan ID: {plan_id}")
    else:
        new_metric = st.selectbox("Metric", available_metrics, format_func=lambda x: x[1])
        new_limit = st.number_input("Included units", min_value=0, key="add_limit")
        new_rate = st.number_input("Overage rate (R per unit)", min_value=0.0, key="add_rate")

        if st.button("➕ Add Metric Limit"):
            cursor.execute("""
                INSERT INTO plan_metric_limits (plan_id, metric_id, metric_limit, overage_rate)
                VALUES (?, ?, ?, ?)
            """, (plan_id, new_metric[0], new_limit, new_rate))
            conn.commit()
            st.success(f"{new_metric[1]} added to the plan!")
            st.rerun()

    conn.close()
