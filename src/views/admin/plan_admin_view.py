import streamlit as st
import sqlite3
from db.database import get_db_connection
from utils.session_guard import require_login

def plan_admin_view():
    st.set_page_config(page_title="Manage Plans", layout="wide")
    require_login('admin')

    user = st.session_state.get("user")
    if not user:
        st.stop()

    st.title("📊 Plan Management")

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Add New Plan
    with st.expander("➕ Add New Plan", expanded=False):
        with st.form("add_plan_form"):
            name = st.text_input("Plan Name")
            description = st.text_area("Description")
            monthly_fee = st.number_input("Monthly Fee (R)", min_value=0.0, step=0.01)
            included_units = st.number_input("Included Units", min_value=0)
            overage_rate = st.number_input("Overage Rate (R/unit)", min_value=0.0, step=0.01)

            submitted = st.form_submit_button("Create Plan")
            if submitted:
                cursor.execute("""
                    INSERT INTO plans (tenant_id, name, description, monthly_fee, included_units, overage_rate, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (user["tenant_id"], name, description, monthly_fee, included_units, overage_rate))
                conn.commit()
                st.success("✅ New plan added successfully!")
                st.rerun()

    # --- List Existing Plans
    st.subheader("📋 Existing Plans")
    cursor.execute("""
        SELECT id, name, description, monthly_fee, included_units, overage_rate, is_active
        FROM plans
        WHERE tenant_id = ?
    """, (user["tenant_id"],))
    plans = cursor.fetchall()

    if not plans:
        st.info("No plans created yet.")
        st.stop()

    for plan in plans:
        plan_id, name, desc, fee, units, overage, active = plan
        with st.expander(f"📦 {name} (R{fee:.2f}/mo)", expanded=False):
            st.markdown(f"**Description:** {desc}")
            st.markdown(f"**Monthly Fee:** R{fee:.2f}")
            st.markdown(f"**Included Units:** {units}")
            st.markdown(f"**Overage Rate:** R{overage:.2f} per unit")
            st.markdown(f"**Status:** {'✅ Active' if active else '❌ Inactive'}")

            col1, col2, col3 = st.columns([2, 2, 3])

            with col1:
                if st.button("✏️ Edit", key=f"edit_{plan_id}"):
                    with st.form(f"edit_form_{plan_id}"):
                        new_name = st.text_input("Plan Name", value=name)
                        new_desc = st.text_area("Description", value=desc)
                        new_fee = st.number_input("Monthly Fee (R)", min_value=0.0, step=0.01, value=fee)
                        new_units = st.number_input("Included Units", min_value=0, value=units)
                        new_overage = st.number_input("Overage Rate (R/unit)", min_value=0.0, step=0.01, value=overage)

                        submitted = st.form_submit_button("Update")
                        if submitted:
                            cursor.execute("""
                                UPDATE plans
                                SET name = ?, description = ?, monthly_fee = ?, included_units = ?, overage_rate = ?
                                WHERE id = ?
                            """, (new_name, new_desc, new_fee, new_units, new_overage, plan_id))
                            conn.commit()
                            st.success("✅ Plan updated.")
                            st.rerun()

            with col2:
                if active and st.button("❌ Deactivate", key=f"deact_{plan_id}"):
                    cursor.execute("UPDATE plans SET is_active = 0 WHERE id = ?", (plan_id,))
                    conn.commit()
                    st.warning("Plan deactivated.")
                    st.rerun()

            with col3:
                with st.expander("👥 View Subscribers"):
                    cursor.execute("""
                        SELECT u.username, s.start_date, s.end_date, s.is_active
                        FROM subscriptions s
                        JOIN users u ON u.id = s.user_id
                        WHERE s.plan_id = ?
                        ORDER BY s.start_date DESC
                    """, (plan_id,))
                    subscribers = cursor.fetchall()

                    if subscribers:
                        for sub in subscribers:
                            uname, start, end, active = sub
                            st.markdown(f"- **{uname}** | Start: {start} | End: {end or 'Ongoing'} | {'🟢 Active' if active else '🔴 Ended'}")
                    else:
                        st.caption("No subscribers yet.")

    conn.close()
