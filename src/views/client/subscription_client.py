#src/views/subscription_client.py

import streamlit as st
import sqlite3
from datetime import datetime
from utils.session_guard import require_login
from db.database import get_db_connection

def subscription_client():
    st.set_page_config(page_title="My Subscription", layout="centered")

    require_login('client')

    user = st.session_state.get("user")
    if not user:
        st.stop()

    user_id = st.session_state.username 
    st.title("📦 My Subscription Plan")

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Get active subscription
    cursor.execute("""
        SELECT s.id, p.name, p.description, p.monthly_fee, p.included_units, p.overage_rate, s.start_date, s.end_date, s.is_active
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.user_id = ? AND s.is_active = 1
    """, (user_id,))
    active_subscription = cursor.fetchone()

    if active_subscription:
        st.subheader("📄 Current Subscription")
        st.markdown(f"**Plan:** {active_subscription[1]}")
        st.markdown(f"**Description:** {active_subscription[2]}")
        st.markdown(f"**Monthly Fee:** R{active_subscription[3]:.2f}")
        st.markdown(f"**Included Units:** {active_subscription[4]} units")
        st.markdown(f"**Overage Rate:** R{active_subscription[5]:.2f} per unit")
        st.markdown(f"**Started On:** {active_subscription[6]}")
        st.markdown(f"**Ends On:** {active_subscription[7] or 'Ongoing'}")

        # Optional: Cancel button
        if st.button("❌ Cancel Subscription"):
            cursor.execute("UPDATE subscriptions SET is_active = 0, end_date = ? WHERE id = ?", (datetime.utcnow().strftime("%Y-%m-%d"), active_subscription[0]))
            
            cursor.execute("""
                INSERT INTO subscription_audit (user_id, tenant_id, action, old_plan_id, new_plan_id, timestamp)
                VALUES (?, ?, 'cancelled', ?, NULL, ?)
            """, (user_id, user["tenant_id"], active_subscription[0], datetime.utcnow().isoformat()))
                        
            conn.commit()
            st.success("Subscription cancelled.")
            st.rerun()

    else:
        st.info("You are not subscribed to any plan.")

    # --- List available plans
    st.subheader("📋 Available Plans")

    cursor.execute("SELECT id, name, description, monthly_fee, included_units, overage_rate FROM plans WHERE tenant_id = ?", (user["tenant_id"],))
    plans = cursor.fetchall()

    if not plans:
        st.warning("No plans available for your tenant.")
        conn.close()
        st.stop()

    selected_plan = st.selectbox("Select a plan to subscribe", options=plans, format_func=lambda p: f"{p[1]} - R{p[3]:.2f}/mo")

    if selected_plan:
        with st.expander("Plan Details", expanded=True):
            st.write(f"**Name:** {selected_plan[1]}")
            st.write(f"**Description:** {selected_plan[2]}")
            st.write(f"**Monthly Fee:** R{selected_plan[3]:.2f}")
            st.write(f"**Included Units:** {selected_plan[4]}")
            st.write(f"**Overage Rate:** R{selected_plan[5]:.2f}/unit")

        estimated_monthly = selected_plan[3]
        overage_example = selected_plan[5] * 50  # e.g., assume 50 excess units

        with st.expander("📈 Billing Preview", expanded=True):
            st.markdown(f"**Monthly Fee:** R{estimated_monthly:.2f}")
            st.markdown(f"**Included Usage:** {selected_plan[4]} units")
            st.markdown(f"**Example: 50 extra units → R{overage_example:.2f} overage**")
            st.info("Actual usage may vary. You’ll be billed at the end of the period based on real usage.")
            
        if st.button("✅ Subscribe to this plan"):
            # End current subscription if any
            cursor.execute("UPDATE subscriptions SET is_active = 0, end_date = ? WHERE user_id = ? AND is_active = 1", 
                        (datetime.utcnow().strftime("%Y-%m-%d"), user_id))

            # Add new subscription
            cursor.execute("""
                INSERT INTO subscriptions (user_id, tenant_id, plan_id, start_date, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (user_id, user["tenant_id"], selected_plan[0], datetime.utcnow().strftime("%Y-%m-%d")))
            
            cursor.execute("""
                INSERT INTO subscription_audit (user_id, tenant_id, action, old_plan_id, new_plan_id, timestamp)
                VALUES (?, ?, 'subscribed', NULL, ?, ?)
            """, (user_id, user["tenant_id"], selected_plan[0], datetime.utcnow().isoformat()))
            conn.commit()

            st.success("🎉 You’ve successfully subscribed to a new plan!")
            st.rerun()

    conn.close()
