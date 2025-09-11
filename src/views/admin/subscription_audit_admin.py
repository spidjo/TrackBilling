import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.session import init_session_state, validate_session
from db.database import get_db_connection
from utils.ui_helpers import display_loading_animation, show_toast

# Custom CSS for professional styling (same as admin_dashboard.py)
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
    
    .audit-item {
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 4px solid;
        transition: all 0.2s ease;
    }
    .audit-item:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .audit-subscribed {
        border-left-color: var(--secondary);
    }
    .audit-cancelled {
        border-left-color: var(--danger);
    }
    .audit-switched {
        border-left-color: var(--info);
    }
</style>
""", unsafe_allow_html=True)

def subscription_audit_admin():
    """Enhanced subscription audit trail with filtering and analytics"""
    init_session_state()
    
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()

    # Page configuration
    st.set_page_config(
        page_title="🔍 Subscription Audit Trail",
        layout="wide",
        page_icon="📊",
        menu_items={
            'Get Help': 'https://your-help-docs.com',
            'Report a bug': "mailto:support@yourcompany.com"
        }
    )

    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">🔍 Subscription Activity Audit</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            <button style="background-color: #4F46E5; color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; cursor: pointer;">Refresh Data</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    tenant_id = st.session_state.tenant_id
    
    # Initialize session state for filters
    if 'audit_date_range' not in st.session_state:
        st.session_state.audit_date_range = [
            datetime.now() - timedelta(days=30), 
            datetime.now()
        ]
    if 'audit_action_filter' not in st.session_state:
        st.session_state.audit_action_filter = ["subscribed", "cancelled", "switched"]
    if 'audit_user_filter' not in st.session_state:
        st.session_state.audit_user_filter = ""

    # Filters section with sidebar layout
    with st.sidebar:
        st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h3 style="color: #1F2937; margin-bottom: 0.5rem;">🔍 Filter Options</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.session_state.audit_date_range = st.date_input(
            "Date Range",
            value=st.session_state.audit_date_range,
            max_value=datetime.now(),
            help="Filter by date range"
        )
        
        st.session_state.audit_action_filter = st.multiselect(
            "Action Types",
            options=["subscribed", "cancelled", "switched"],
            default=st.session_state.audit_action_filter,
            help="Filter by action type"
        )
        
        st.session_state.audit_user_filter = st.text_input(
            "Search User",
            value=st.session_state.audit_user_filter,
            placeholder="Enter username...",
            help="Filter by username"
        )
        
        # Additional filters
        plan_filter = st.text_input(
            "Filter by Plan",
            placeholder="Enter plan name...",
            help="Filter by plan name"
        )
        
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # Quick action buttons
        st.markdown("**Quick Actions**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Export CSV", use_container_width=True):
                pass  # Will be handled in main content
        with col2:
            if st.button("🔄 Reset Filters", use_container_width=True):
                st.session_state.audit_date_range = [
                    datetime.now() - timedelta(days=30), 
                    datetime.now()
                ]
                st.session_state.audit_action_filter = ["subscribed", "cancelled", "switched"]
                st.session_state.audit_user_filter = ""
                st.rerun()

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
                tenant_id,
                st.session_state.audit_date_range[0],
                st.session_state.audit_date_range[1] + timedelta(days=1),  # Include full end date
                st.session_state.audit_action_filter
            ]

            # Add username filter if provided
            if st.session_state.audit_user_filter:
                query += " AND u.username ILIKE %s"
                params.append(f"%{st.session_state.audit_user_filter}%")
                
            # Add plan filter if provided
            if plan_filter:
                query += " AND (p1.name ILIKE %s OR p2.name ILIKE %s)"
                params.extend([f"%{plan_filter}%", f"%{plan_filter}%"])

            query += " ORDER BY sa.timestamp DESC LIMIT 1000"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                st.info("No subscription activity found matching your filters.")
                return

            # Display metrics
            show_audit_metrics(rows)

            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

            # Activity timeline with enhanced UI
            st.markdown("""
            <div class="section-header">
                <div class="icon">📜</div>
                <h2>Activity Timeline</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Add search and filter for the timeline
            search_term = st.text_input("Search in results", placeholder="Search text in activity...")
            
            filtered_rows = rows
            if search_term:
                filtered_rows = [
                    r for r in rows 
                    if search_term.lower() in r[1].lower() or 
                       (r[3] and search_term.lower() in r[3].lower()) or 
                       (r[4] and search_term.lower() in r[4].lower())
                ]
            
            # Display timeline with pagination
            items_per_page = 20
            total_pages = max(1, (len(filtered_rows) // items_per_page) + (1 if len(filtered_rows) % items_per_page > 0 else 0))
            
            if total_pages > 1:
                page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
                start_idx = (page - 1) * items_per_page
                end_idx = min(start_idx + items_per_page, len(filtered_rows))
                page_rows = filtered_rows[start_idx:end_idx]
                
                st.caption(f"Showing {start_idx + 1}-{end_idx} of {len(filtered_rows)} records")
            else:
                page_rows = filtered_rows
            
            for ts, username, action, old_plan, new_plan in page_rows:
                action_class = ""
                action_icon = ""
                if action == "subscribed":
                    action_class = "audit-subscribed"
                    action_icon = "🟢"
                elif action == "cancelled":
                    action_class = "audit-cancelled"
                    action_icon = "🔴"
                elif action == "switched":
                    action_class = "audit-switched"
                    action_icon = "🔁"
                
                st.markdown(f'<div class="audit-item {action_class}">', unsafe_allow_html=True)
                cols = st.columns([1, 4, 2])
                with cols[0]:
                    st.markdown(f"**{ts.strftime('%Y-%m-%d')}**")
                    st.markdown(f"`{ts.strftime('%H:%M')}`")
                with cols[1]:
                    if action == "subscribed":
                        st.markdown(f"{action_icon} **{username}** subscribed to **{new_plan}**")
                    elif action == "cancelled":
                        st.markdown(f"{action_icon} **{username}** cancelled **{old_plan}**")
                    elif action == "switched":
                        st.markdown(f"{action_icon} **{username}** switched from **{old_plan}** to **{new_plan}**")
                with cols[2]:
                    st.caption(f"via {action}")
                st.markdown('</div>', unsafe_allow_html=True)

            # Export option with enhanced UI
            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📤 Export Audit Log (CSV)",
                    data=convert_to_csv(rows),
                    file_name=f"subscription_audit_{datetime.now().date()}.csv",
                    mime="text/csv",
                    help="Export filtered results to CSV",
                    use_container_width=True
                )
            with col2:
                if st.button("📋 Copy to Clipboard", use_container_width=True):
                    try:
                        import pyperclip
                        pyperclip.copy(convert_to_csv(rows))
                        show_toast("Data copied to clipboard!", "success")
                    except:
                        show_toast("Clipboard access not available", "error")

        except Exception as e:
            show_toast(f"Error loading audit data: {str(e)}", "error")
            st.error("Failed to load subscription audit data. Please try again.")
            if st.session_state.role == "superadmin":
                st.exception(e)
        finally:
            conn.close()

def show_audit_metrics(rows):
    """Display key metrics about subscription activity with professional cards"""
    total_actions = len(rows)
    subscriptions = sum(1 for r in rows if r[2] == "subscribed")
    cancellations = sum(1 for r in rows if r[2] == "cancelled")
    switches = sum(1 for r in rows if r[2] == "switched")
    
    # Calculate percentages
    sub_pct = (subscriptions / total_actions * 100) if total_actions > 0 else 0
    cancel_pct = (cancellations / total_actions * 100) if total_actions > 0 else 0
    switch_pct = (switches / total_actions * 100) if total_actions > 0 else 0

    cols = st.columns(4)
    with cols[0]:
        st.markdown(f"""
        <div class="metric-card metric-neutral">
            <h3>Total Actions</h3>
            <h2>{total_actions:,}</h2>
            <div style="margin-top: 0.5rem;">
                <span style="color: #6B7280; font-size: 0.9rem;">All time periods</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""
        <div class="metric-card metric-positive">
            <h3>New Subscriptions</h3>
            <h2>{subscriptions:,}</h2>
            <div style="margin-top: 0.5rem;">
                <span style="color: #10B981; font-size: 0.9rem;">{sub_pct:.1f}% of total</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"""
        <div class="metric-card metric-negative">
            <h3>Cancellations</h3>
            <h2>{cancellations:,}</h2>
            <div style="margin-top: 0.5rem;">
                <span style="color: #EF4444; font-size: 0.9rem;">{cancel_pct:.1f}% of total</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f"""
        <div class="metric-card metric-warning">
            <h3>Plan Switches</h3>
            <h2>{switches:,}</h2>
            <div style="margin-top: 0.5rem;">
                <span style="color: #F59E0B; font-size: 0.9rem;">{switch_pct:.1f}% of total</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

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

if __name__ == "__main__":
    subscription_audit_admin()