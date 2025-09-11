import streamlit as st
from datetime import datetime
from db.database import get_db_connection
from utils.session import init_session_state, validate_session
from utils.ui_helpers import display_loading_animation, show_toast

# Apply the same custom CSS styling
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
    
    .metric-table-header {
        background: linear-gradient(90deg, #4F46E5, #6366F1);
        color: white;
        padding: 0.75rem;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
    
    .metric-table-row {
        padding: 1rem;
        border-bottom: 1px solid #E5E7EB;
        transition: background-color 0.2s ease;
    }
    
    .metric-table-row:hover {
        background-color: #F9FAFB;
    }
    
    .delete-btn {
        background: #EF4444 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.25rem 0.75rem !important;
        cursor: pointer !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
    }
    
    .delete-btn:hover {
        background: #DC2626 !important;
    }
</style>
""", unsafe_allow_html=True)

def usage_metric_admin():
    """Enhanced usage metrics management interface with professional UX"""
    init_session_state()
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()
    
    # Page configuration
    st.set_page_config(
        page_title="Metrics Manager",
        layout="wide",
        page_icon="📊"
    )

    tenant_id = st.session_state.tenant_id

    # Dashboard header with professional styling
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<h1 style='color: #1F2937; margin: 0;'>📊 Usage Metrics Management</h1>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<p style='color: #6B7280; text-align: right; margin: 0;'>Last updated: {st.session_state.get('last_update', 'Never')}</p>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # Database connection with loading spinner
    with st.spinner("Loading metrics data..."):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Get metrics count for summary card
            cursor.execute("SELECT COUNT(*) FROM usage_metrics WHERE tenant_id = %s", (tenant_id,))
            metrics_count = cursor.fetchone()[0]
            
            # Summary metrics
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card metric-positive">
                    <h3>Total Metrics</h3>
                    <h2>{metrics_count:,}</h2>
                    <p style="color: #6B7280; margin-top: 0.5rem;">Active tracking metrics</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                cursor.execute("""
                    SELECT COUNT(DISTINCT metric_name) 
                    FROM usage_records 
                    WHERE tenant_id = %s 
                    AND usage_date >= CURRENT_DATE - INTERVAL '7 days'
                """, (tenant_id,))
                active_metrics = cursor.fetchone()[0]
                st.markdown(f"""
                <div class="metric-card metric-{'warning' if active_metrics < metrics_count else 'neutral'}">
                    <h3>Active Metrics (7 days)</h3>
                    <h2>{active_metrics:,}/{metrics_count:,}</h2>
                    <p style="color: #6B7280; margin-top: 0.5rem;">Recently used metrics</p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

            # Tab layout for better organization
            tab1, tab2 = st.tabs(["📋 Current Metrics", "➕ Add New Metric"])
            
            # Tab 1: Current Metrics
            with tab1:
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📋</div>
                    <h2>Your Defined Metrics</h2>
                </div>
                """, unsafe_allow_html=True)
                
                cursor.execute("""
                    SELECT id, name, unit, description, created_at 
                    FROM usage_metrics 
                    WHERE tenant_id = %s 
                    ORDER BY name
                """, (tenant_id,))
                metrics = cursor.fetchall()

                if metrics:
                    # Create a proper Streamlit table instead of HTML buttons
                    st.markdown("""
                    <div style="background: white; border-radius: 12px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        <div class="metric-table-header">
                            <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 1rem; align-items: center;">
                                <div>Metric Name</div>
                                <div>Unit</div>
                                <div>Created On</div>
                                <div style="text-align: center;">Actions</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    for mid, name, unit, description, created_at in metrics:
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        with col1:
                            st.markdown(f"**{name}**")
                            if description:
                                st.caption(description)
                        with col2:
                            st.markdown(f"`{unit}`")
                        with col3:
                            st.markdown(created_at.strftime('%Y-%m-%d'))
                        with col4:
                            if st.button("🗑️ Delete", key=f"delete_{mid}", use_container_width=True):
                                st.session_state[f"delete_metric_id"] = mid
                                st.session_state[f"delete_metric_name"] = name
                                st.rerun()
                        
                        # Show delete confirmation if this metric is being deleted
                        if st.session_state.get(f"delete_metric_id") == mid:
                            st.warning(f"⚠️ Are you sure you want to delete '{name}'? This action cannot be undone.")
                            confirm_col1, confirm_col2 = st.columns(2)
                            with confirm_col1:
                                if st.button("✅ Confirm Delete", key=f"confirm_{mid}", use_container_width=True):
                                    cursor.execute("DELETE FROM usage_metrics WHERE id = %s", (mid,))
                                    conn.commit()
                                    show_toast(f"Metric '{name}' deleted successfully", "success")
                                    # Clear the delete state
                                    if "delete_metric_id" in st.session_state:
                                        del st.session_state["delete_metric_id"]
                                    if f"delete_metric_name" in st.session_state:
                                        del st.session_state["delete_metric_name"]
                                    st.rerun()
                            with confirm_col2:
                                if st.button("❌ Cancel", key=f"cancel_{mid}", use_container_width=True):
                                    # Clear the delete state
                                    if "delete_metric_id" in st.session_state:
                                        del st.session_state["delete_metric_id"]
                                    if f"delete_metric_name" in st.session_state:
                                        del st.session_state["delete_metric_name"]
                                    st.rerun()
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                else:
                    st.markdown("""
                    <div class="alert-card alert-info">
                        <h3>📊 No Metrics Defined</h3>
                        <p>You haven't created any usage metrics yet. Metrics are essential for tracking and billing your services.</p>
                        <p>Switch to the <strong>Add New Metric</strong> tab to create your first metric.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.image("https://via.placeholder.com/600x200?text=Define+Usage+Metrics+for+Better+Tracking", 
                            use_column_width=True, caption="Define metrics to start tracking usage and billing")

            # Tab 2: Add New Metric
            with tab2:
                st.markdown("""
                <div class="section-header">
                    <div class="icon">➕</div>
                    <h2>Create New Usage Metric</h2>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("add_metric_form", clear_on_submit=True):
                    with st.container():
                        st.markdown("""
                        <div style="background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        name = col1.text_input(
                            "**Metric Name** *",
                            placeholder="e.g., API Calls, Storage, Active Users",
                            help="Unique name that will appear in reports and dashboards"
                        )
                        unit = col2.text_input(
                            "**Measurement Unit** *",
                            placeholder="e.g., requests, GB, seats",
                            help="Unit of measurement for this metric (e.g., requests, GB, seats)"
                        )
                        
                        description = st.text_area(
                            "**Description**",
                            placeholder="Describe what this metric tracks and how it's measured...",
                            help="Optional detailed description for better understanding"
                        )
                        
                        st.markdown("""
                        <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #E5E7EB;">
                        """, unsafe_allow_html=True)
                        
                        submitted = st.form_submit_button(
                            "🚀 Create Metric",
                            type="primary",
                            use_container_width=True,
                            help="Add this metric to your tracking system"
                        )
                        
                        st.markdown("</div></div>", unsafe_allow_html=True)
                        
                        if submitted:
                            if not name.strip() or not unit.strip():
                                show_toast("Please fill in all required fields", "warning")
                            else:
                                try:
                                    cursor.execute(
                                        "INSERT INTO usage_metrics (tenant_id, name, unit, description) VALUES (%s, %s, %s, %s)",
                                        (tenant_id, name.strip(), unit.strip(), description.strip() if description else None)
                                    )
                                    conn.commit()
                                    show_toast(f"✅ Metric '{name}' added successfully", "success")
                                    st.session_state.last_update = datetime.now().strftime('%Y-%m-%d %H:%M')  # Fixed this line
                                    st.rerun()
                                except Exception as e:
                                    if "duplicate" in str(e).lower():
                                        show_toast("A metric with this name already exists", "error")
                                        st.error("❌ Metric name must be unique. Please choose a different name.")
                                    else:
                                        show_toast(f"Error creating metric: {str(e)}", "error")
                                        st.error("Failed to create metric. Please try again.")

        except Exception as e:
            show_toast(f"Error loading metrics: {str(e)}", "error")
            st.markdown("""
            <div class="alert-card alert-danger">
                <h3>❌ Database Error</h3>
                <p>Failed to load metrics data. Please try refreshing the page or contact support if the issue persists.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.role == "superadmin":
                with st.expander("Technical Details"):
                    st.exception(e)
        finally:
            conn.close()
    
    # Help section with enhanced styling using Streamlit components
    with st.expander("ℹ️ Usage Metrics Guide", expanded=False):
        # Header
        st.markdown("### 📖 Best Practices for Usage Metrics")
        
        # Two-column layout for best practices
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎯 Defining Effective Metrics")
            st.markdown("""
            - **Clear Naming**: Use descriptive names that are easily understood
            - **Standard Units**: Choose consistent units across similar metrics  
            - **Relevance**: Track metrics that directly relate to your business value
            - **Scalability**: Consider how metrics will work as your business grows
            """)
        
        with col2:
            st.markdown("#### 💡 Common Metric Examples")
            st.markdown("""
            - **API Calls**: Measured in `requests`
            - **Storage**: Measured in `GB` or `TB`
            - **Active Users**: Measured in `seats`
            - **Data Processing**: Measured in `records` or `MB`
            """)
        
        # Usage benefits section
        st.markdown("---")
        st.markdown("#### 🚀 Usage & Benefits")
        st.markdown("""
        Once created, metrics become available for **usage tracking**, **billing plans configuration**, 
        and **analytics reports**. Well-defined metrics help you understand customer usage patterns 
        and optimize your pricing strategy.
        """)
        
        # Additional tips in a callout box
        st.info("""
        💡 **Pro Tip**: Start with 3-5 core metrics that capture the essential value your service provides. 
        You can always add more metrics later as your business evolves.
        """)

if __name__ == "__main__":
    usage_metric_admin()