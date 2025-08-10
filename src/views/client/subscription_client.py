# src/views/client/subscription_client.py
import streamlit as st
from datetime import datetime
from utils.session_guard import require_login
from utils.ui_helpers import show_toast, loading_spinner
from db.database import get_db_connection

def subscription_client():
    st.set_page_config(
        page_title="My Subscription",
        layout="centered",
        page_icon="📦"
    )

    require_login('client')

    user = st.session_state.get("user")
    if not user:
        st.stop()

    user_id = st.session_state.username
    
    # Use columns to create a better layout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📦 My Subscription Plan")
    with col2:
        st.write("")  # Placeholder for potential status badge

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Get user ID from users table
    with loading_spinner("Loading your subscription..."):
        cursor.execute("SELECT id FROM users WHERE username = %s", (user_id,))
        user_row = cursor.fetchone()
        u_id = user_row[0] if user_row else None
        
        # --- Get active subscription
        cursor.execute("""
            SELECT p.id, s.id, p.name, p.description, p.monthly_fee, 
                   p.included_units, p.overage_rate, s.start_date, s.end_date, s.is_active
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.user_id = %s AND s.is_active
        """, (u_id,))
        active_subscription = cursor.fetchone()

    if active_subscription:
        with st.container(border=True):
            st.subheader("📄 Current Subscription", divider="gray")
            
            # Use columns for better information display
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Plan", active_subscription[2])
                st.markdown(f"**Description:** {active_subscription[3]}")
                st.markdown(f"**Included Units:** {active_subscription[5]:,} units")
            
            with col2:
                st.metric("Monthly Fee", f"R{active_subscription[4]:.2f}")
                st.markdown(f"**Overage Rate:** R{active_subscription[6]:.2f}/unit")
                st.markdown(f"**Status:** {'Active' if active_subscription[9] else 'Inactive'}")
            
            # Date information
            st.caption(f"**Started On:** {active_subscription[7].strftime('%d %b %Y') if isinstance(active_subscription[7], datetime) else active_subscription[7]}")
            st.caption(f"**Ends On:** {active_subscription[8].strftime('%d %b %Y') if isinstance(active_subscription[8], datetime) else (active_subscription[8] or 'Ongoing')}")

            # Cancellation section - Fixed version
            if st.button("❌ Cancel Subscription", type="primary", use_container_width=True, key="cancel_btn"):
                st.session_state.show_cancellation_confirmation = True

            if st.session_state.get('show_cancellation_confirmation', False):
                st.warning("Are you sure you want to cancel your subscription?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes, cancel my subscription", type="primary", key="confirm_cancel"):
                        with loading_spinner("Processing cancellation..."):
                            try:
                                cursor.execute("UPDATE subscriptions SET is_active = False, end_date = %s WHERE id = %s", 
                                            (datetime.utcnow().strftime("%Y-%m-%d"), active_subscription[1]))

                                cursor.execute("""
                                    INSERT INTO subscription_audit (user_id, tenant_id, action, old_plan_id, new_plan_id, timestamp)
                                    VALUES (%s, %s, 'cancelled', %s, NULL, %s)
                                """, (u_id, user["tenant_id"], active_subscription[0], datetime.utcnow().isoformat()))

                                conn.commit()
                                show_toast("Subscription cancelled successfully", "success")
                                # Clear confirmation state
                                del st.session_state.show_cancellation_confirmation
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error cancelling subscription: {str(e)}")
                                conn.rollback()
                with col2:
                    if st.button("No, keep my subscription", key="keep_subscription"):
                        del st.session_state.show_cancellation_confirmation
                        st.rerun()

    else:
        st.info("You don't have an active subscription.", icon="ℹ️")

    # --- List available plans
    st.subheader("📋 Available Plans", divider="gray")
    
    with loading_spinner("Loading available plans..."):
        cursor.execute("""
            SELECT id, name, description, monthly_fee, included_units, overage_rate 
            FROM plans 
            WHERE tenant_id = %s
            ORDER BY monthly_fee
        """, (user["tenant_id"],))
        plans = cursor.fetchall()

    if not plans:
        st.warning("No plans available for your organization.", icon="⚠️")
        conn.close()
        st.stop()

    # Plan selection with better formatting
    plan_options = [f"{p[1]} - R{p[3]:.2f}/mo" for p in plans]
    selected_plan_idx = st.selectbox(
        "Choose a plan to subscribe",
        options=range(len(plans)),
        format_func=lambda x: plan_options[x],
        index=0
    )
    selected_plan = plans[selected_plan_idx]

    # Plan details in tabs for better organization
    tab1, tab2 = st.tabs(["Plan Details", "Billing Estimate"])
    
    with tab1:
        st.markdown(f"### {selected_plan[1]}")
        st.markdown(selected_plan[2])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Monthly Fee", f"R{selected_plan[3]:.2f}")
            st.metric("Included Units", f"{selected_plan[4]:,}")
        with col2:
            st.metric("Overage Rate", f"R{selected_plan[5]:.2f}/unit")
            st.metric("Example Overage (50 units)", f"R{selected_plan[5] * 50:.2f}")
    
    with tab2:
        st.markdown("**Estimated Monthly Cost**")
        
        # Simple calculator for usage estimation
        estimated_usage = st.slider(
            "Estimate your monthly usage (units)",
            min_value=selected_plan[4],
            max_value=selected_plan[4] * 5,
            value=selected_plan[4],
            step=10
        )
        
        overage = max(0, estimated_usage - selected_plan[4])
        total_cost = selected_plan[3] + (overage * selected_plan[5])
        
        st.metric("Base Fee", f"R{selected_plan[3]:.2f}")
        st.metric("Overage Cost", f"R{overage * selected_plan[5]:.2f}", delta=f"{overage} extra units")
        st.metric("Total Estimated Cost", f"R{total_cost:.2f}", delta_color="off")
        
        st.caption("Note: This is an estimate only. Actual usage may vary.")

    # Subscribe button with confirmation
    subscribe_clicked = st.button("✅ Subscribe to Plan", type="primary", use_container_width=True, key="subscribe_btn")

    if subscribe_clicked:
        if active_subscription:
            st.warning("⚠️ This will replace your current subscription.")
            st.session_state.show_subscription_confirmation = True
    
        # If no active subscription or confirmation handled
        if not active_subscription or st.session_state.get('subscription_confirmed', False):
            with loading_spinner("Processing your subscription..."):
                try:
                    # End current subscription if any
                    if active_subscription:
                        cursor.execute("""
                            UPDATE subscriptions 
                            SET is_active = False, end_date = %s 
                            WHERE user_id = %s AND is_active = True
                        """, (datetime.utcnow().strftime("%Y-%m-%d"), u_id))

                    # Add new subscription
                    cursor.execute("""
                        INSERT INTO subscriptions (user_id, tenant_id, plan_id, start_date, is_active)
                        VALUES (%s, %s, %s, %s, True)
                    """, (u_id, user["tenant_id"], selected_plan[0], datetime.utcnow().strftime("%Y-%m-%d")))

                    cursor.execute("""
                        INSERT INTO subscription_audit (user_id, tenant_id, action, old_plan_id, new_plan_id, timestamp)
                        VALUES (%s, %s, 'subscribed', NULL, %s, %s)
                    """, (u_id, user["tenant_id"], selected_plan[0], datetime.utcnow().isoformat()))
                    
                    conn.commit()
                    show_toast("🎉 Subscription successful! Your new plan is now active.", "success")
                    # Clear confirmation state
                    if 'subscription_confirmed' in st.session_state:
                        del st.session_state.subscription_confirmed
                    if 'show_subscription_confirmation' in st.session_state:
                        del st.session_state.show_subscription_confirmation
                    st.rerun()
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    conn.rollback()

    # Show confirmation buttons if needed
    if st.session_state.get('show_subscription_confirmation', False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, switch plans", type="primary", key="confirm_subscribe"):
                st.session_state.subscription_confirmed = True
                st.rerun()
        with col2:
            if st.button("No, keep current plan", key="cancel_subscribe"):
                del st.session_state.show_subscription_confirmation
                st.rerun()

    conn.close()