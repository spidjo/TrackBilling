import streamlit as st
from datetime import datetime, timedelta
from utils.session_guard import require_login
from db.database import get_db_connection
from utils.ui_helpers import display_loading_animation, show_toast

def subscription_audit_admin():
    """Enhanced subscription audit trail with filtering and analytics"""
    # Page configuration
    st.set_page_config(
        page_title="🔍 Subscription Audit Trail",
        layout="wide",
        menu_items={
            'Get Help': 'https://your-help-docs.com',
            'Report a bug': "mailto:support@yourcompany.com"
        }
    )
    require_login('admin')

    # Session setup
    user = st.session_state.get("user")
    if not user:
        st.stop()

    # Page header
    st.title("🔍 Subscription Activity Audit")
    st.caption("Track all subscription changes across your organization")

    # Filters section
    with st.expander("🔎 Filter Options", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_range = st.date_input(
                "Date Range",
                value=[datetime.now() - timedelta(days=30), datetime.now()],
                max_value=datetime.now(),
                help="Filter by date range"
            )
        
        with col2:
            action_filter = st.multiselect(
                "Action Types",
                options=["subscribed", "cancelled", "switched"],
                default=["subscribed", "cancelled", "switched"],
                help="Filter by action type"
            )
        
        with col3:
            user_filter = st.text_input(
                "Search User",
                placeholder="Enter username...",
                help="Filter by username"
            )

    # Load data with loading animation
    with display_loading_animation("Loading audit data..."):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Base query with filters
            query = """
                SELECT sa.timestamp, u.username, sa.action, p1.name, p2.name
                FROM subscription_audit sa
                JOIN users u ON sa.user_id = u.id
                LEFT JOIN plans p1 ON sa.old_plan_id = p1.id
                LEFT JOIN plans p2 ON sa.new_plan_id = p2.id
                WHERE sa.tenant_id = %s
                AND sa.timestamp BETWEEN %s AND %s
                AND sa.action = ANY(%s)
            """
            params = [
                user["tenant_id"],
                date_range[0],
                date_range[1] + timedelta(days=1),  # Include full end date
                action_filter
            ]

            # Add username filter if provided
            if user_filter:
                query += " AND u.username ILIKE %s"
                params.append(f"%{user_filter}%")

            query += " ORDER BY sa.timestamp DESC LIMIT 1000"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                st.info("No subscription activity found matching your filters.")
                return

            # Display metrics
            show_audit_metrics(rows)

            # Activity timeline
            st.subheader("📜 Activity Timeline")
            for ts, username, action, old_plan, new_plan in rows:
                with st.container(border=True):
                    cols = st.columns([1, 4, 2])
                    with cols[0]:
                        st.markdown(f"`{ts.strftime('%Y-%m-%d %H:%M')}`")
                    with cols[1]:
                        if action == "subscribed":
                            st.markdown(f"🟢 **{username}** subscribed to **{new_plan}**")
                        elif action == "cancelled":
                            st.markdown(f"🔴 **{username}** cancelled **{old_plan}**")
                        elif action == "switched":
                            st.markdown(f"🔁 **{username}** switched from **{old_plan}** to **{new_plan}**")
                    with cols[2]:
                        st.caption(f"via {action}")

            # Export option
            st.download_button(
                label="📤 Export Audit Log",
                data=convert_to_csv(rows),
                file_name=f"subscription_audit_{datetime.now().date()}.csv",
                mime="text/csv",
                help="Export filtered results to CSV"
            )

        except Exception as e:
            show_toast(f"Error loading audit data: {str(e)}", "error")
            st.error("Failed to load subscription audit data. Please try again.")
            if user.get("role") == "superadmin":
                st.exception(e)
        finally:
            conn.close()

def show_audit_metrics(rows):
    """Display key metrics about subscription activity"""
    total_actions = len(rows)
    subscriptions = sum(1 for r in rows if r[2] == "subscribed")
    cancellations = sum(1 for r in rows if r[2] == "cancelled")
    switches = sum(1 for r in rows if r[2] == "switched")

    cols = st.columns(4)
    with cols[0]:
        st.metric("Total Actions", total_actions)
    with cols[1]:
        st.metric("New Subscriptions", subscriptions)
    with cols[2]:
        st.metric("Cancellations", cancellations)
    with cols[3]:
        st.metric("Plan Switches", switches)

def convert_to_csv(rows):
    """Convert audit data to CSV format"""
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Username", "Action", "Old Plan", "New Plan"])
    
    for row in rows:
        writer.writerow([
            row[0].strftime('%Y-%m-%d %H:%M:%S'),
            row[1],
            row[2],
            row[3] or "",
            row[4] or ""
        ])
    
    return output.getvalue()