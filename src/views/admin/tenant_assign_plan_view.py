import streamlit as st
from datetime import datetime
from db.database import get_db_connection
from utils.session import init_session_state
from utils.ui_helpers import loading_spinner, show_toast

def assign_plans():
    """Admin interface for assigning subscription plans to users with enhanced UX"""
    # Initialize session and check permissions
    init_session_state()
    
    if st.session_state.role not in ["admin", "tenantadmin", "superadmin"]:
        st.warning("🔒 Access denied. Only tenant administrators can assign plans.")
        st.stop()

    # Page configuration
    st.set_page_config(
        page_title="Plan Assignment",
        layout="wide",
        page_icon="🏷️"
    )

    tenant_id = st.session_state.tenant_id
    st.title("🏷️ Plan Assignment")
    st.markdown("---")

    # Database connection with loading spinner
    with loading_spinner("Loading assignment data..."):
        conn = get_db_connection()
        cursor = conn.cursor()

        # --- Get Users and Plans ---
        cursor.execute("""
            SELECT id, username, first_name, last_name 
            FROM users 
            WHERE tenant_id = %s AND is_active = 1
            ORDER BY last_name, first_name
        """, (tenant_id,))
        users = cursor.fetchall()
        user_options = {
            f"{first_name} {last_name} ({username})": user_id 
            for user_id, username, first_name, last_name in users
        }

        cursor.execute("""
            SELECT id, name, description 
            FROM plans 
            WHERE tenant_id = %s AND is_active = TRUE
            ORDER BY name
        """, (tenant_id,))
        plans = cursor.fetchall()
        plan_options = {
            f"{name} ({description[:30]}...)" if description else name: plan_id 
            for plan_id, name, description in plans
        }

    if not users or not plans:
        st.error("No active users or plans available for assignment")
        conn.close()
        return

    # --- Assignment Form ---
    with st.container(border=True):
        st.subheader("🔹 Assign New Plan", divider="gray")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_user_label = st.selectbox(
                "Select User*",
                options=list(user_options.keys()),
                help="Select user to assign plan to"
            )
            selected_user_id = user_options[selected_user_label]
            
            # Display user details
            cursor.execute("""
                SELECT email, registration_date FROM users WHERE id = %s
            """, (selected_user_id,))
            user_email, user_created = cursor.fetchone()
            st.caption(f"Email: {user_email}")
            st.caption(f"Member since: {user_created.strftime('%Y-%m-%d')}")

        with col2:
            selected_plan_label = st.selectbox(
                "Select Plan*",
                options=list(plan_options.keys()),
                help="Select plan to assign"
            )
            selected_plan_id = plan_options[selected_plan_label]
            
            # Display plan details
            cursor.execute("""
                SELECT monthly_fee, included_units FROM plans WHERE id = %s
            """, (selected_plan_id,))
            monthly_fee, included_units = cursor.fetchone()
            st.caption(f"Monthly Fee: R{monthly_fee:.2f}")
            st.caption(f"Included Units: {included_units:,}")

        # Effective date selection
        effective_date = st.date_input(
            "Effective Date",
            value=datetime.now(),
            min_value=datetime.now(),
            help="When the plan assignment should take effect"
        )

        # Check for existing subscription
        cursor.execute("""
            SELECT s.id, p.name 
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.user_id = %s AND s.tenant_id = %s
            AND (s.end_date IS NULL OR s.end_date > CURRENT_DATE)
        """, (selected_user_id, tenant_id))
        existing_sub = cursor.fetchone()

        if existing_sub:
            st.warning(f"⚠️ User already has active plan: {existing_sub[1]}")

        # Assignment button
        if st.button(
            "💾 Assign Plan",
            type="primary",
            use_container_width=True,
            disabled=not (selected_user_id and selected_plan_id)
        ):
            try:
                if existing_sub:
                    # End current subscription
                    cursor.execute("""
                        UPDATE subscriptions 
                        SET end_date = %s 
                        WHERE id = %s
                    """, (effective_date, existing_sub[0]))
                
                # Create new subscription
                cursor.execute("""
                    INSERT INTO subscriptions (
                        user_id, plan_id, tenant_id, 
                        start_date, is_active
                    )
                    VALUES (%s, %s, %s, %s, TRUE)
                """, (
                    selected_user_id, selected_plan_id, tenant_id,
                    effective_date
                ))
                
                conn.commit()
                show_toast(
                    f"Plan assigned successfully to {selected_user_label.split('(')[0]}",
                    "success"
                )
                st.rerun()
            except Exception as e:
                conn.rollback()
                show_toast(f"Error assigning plan: {str(e)}", "error")

    # --- Current Assignments ---
    st.subheader("📋 Current Subscriptions", divider="gray")
    
    with loading_spinner("Loading current assignments..."):
        cursor.execute("""
            SELECT 
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
        assignments = cursor.fetchall()

    if not assignments:
        st.info("No active subscriptions found")
    else:
        # Convert to DataFrame for better display
        import pandas as pd
        df = pd.DataFrame(assignments, columns=[
            "Username", "Name", "Plan", "Start Date", "End Date", "Active"
        ])
        df["Status"] = df["Active"].apply(
            lambda x: "✅ Active" if x else "❌ Ended"
        )
        
        # Format dates
        df["Start Date"] = pd.to_datetime(df["Start Date"]).dt.strftime('%Y-%m-%d')
        df["End Date"] = pd.to_datetime(df["End Date"]).dt.strftime('%Y-%m-%d')
        df["End Date"] = df["End Date"].replace("NaT", "Ongoing")

        # Display with filters
        status_filter = st.multiselect(
            "Filter by Status",
            options=["✅ Active", "❌ Ended"],
            default=["✅ Active"]
        )
        
        filtered_df = df[df["Status"].isin(status_filter)]
        st.dataframe(
            filtered_df[["Name", "Username", "Plan", "Start Date", "End Date", "Status"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Name": "User",
                "Username": st.column_config.TextColumn(),
                "Plan": st.column_config.TextColumn(),
                "Start Date": "Start",
                "End Date": "End",
                "Status": st.column_config.TextColumn()
            }
        )

    conn.close()

if __name__ == "__main__":
    assign_plans()