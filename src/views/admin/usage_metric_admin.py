import streamlit as st
from db.database import get_db_connection
from utils.session_guard import require_login
from utils.ui_helpers import display_loading_animation, show_toast

def usage_metric_admin():
    """Enhanced usage metrics management interface"""
    require_login('admin')
    
    # Page configuration
    st.set_page_config(
        page_title="Metrics Manager",
        layout="wide",
        page_icon="📊"
    )
    
    user = st.session_state.get("user")
    if not user:
        st.stop()
    
    tenant_id = user["tenant_id"]
    
    # Page header
    st.title("📊 Usage Metrics Management")
    st.caption("Define and manage the metrics you want to track for billing purposes")
    
    # Tab layout for better organization
    tab1, tab2 = st.tabs(["📋 Current Metrics", "➕ Add New Metric"])
    
    with st.spinner("Loading metrics data..."):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Tab 1: Current Metrics
            with tab1:
                st.subheader("Your Defined Metrics")
                cursor.execute("""
                    SELECT id, name, unit, created_at 
                    FROM usage_metrics 
                    WHERE tenant_id = %s 
                    ORDER BY name
                """, (tenant_id,))
                metrics = cursor.fetchall()

                if metrics:
                    # Metrics table with pagination
                    cols = st.columns([4, 3, 3, 2])
                    cols[0].markdown("**Metric Name**")
                    cols[1].markdown("**Unit**")
                    cols[2].markdown("**Created On**")
                    cols[3].markdown("**Actions**")
                    
                    for mid, name, unit, created_at in metrics:
                        cols = st.columns([4, 3, 3, 2])
                        cols[0].markdown(f"`{name}`")
                        cols[1].markdown(unit)
                        cols[2].markdown(created_at.strftime('%Y-%m-%d'))
                        
                        # Delete button with confirmation
                        with cols[3]:
                            if st.button("🗑️", key=f"delete_{mid}", help="Delete metric"):
                                if st.session_state.get(f"confirm_delete_{mid}"):
                                    cursor.execute("DELETE FROM usage_metrics WHERE id = %s", (mid,))
                                    conn.commit()
                                    show_toast(f"Metric '{name}' deleted", "success")
                                    st.rerun()
                                else:
                                    st.session_state[f"confirm_delete_{mid}"] = True
                                    st.warning(f"Delete {name}? Click again to confirm")
                else:
                    st.info("No metrics defined yet. Add your first metric in the 'Add New Metric' tab.")
                    st.image("https://via.placeholder.com/600x200?text=Define+Usage+Metrics", use_column_width=True)

            # Tab 2: Add New Metric
            with tab2:
                st.subheader("Create New Usage Metric")
                with st.form("add_metric_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    name = col1.text_input(
                        "Metric Name*",
                        placeholder="e.g., API Calls, Storage",
                        help="Name that will appear in reports"
                    )
                    unit = col2.text_input(
                        "Measurement Unit*",
                        placeholder="e.g., requests, GB",
                        help="Unit of measurement for this metric"
                    )
                    
                    submitted = st.form_submit_button(
                        "➕ Add Metric",
                        type="primary",
                        use_container_width=True
                    )
                    
                    if submitted:
                        if not name.strip() or not unit.strip():
                            show_toast("Both name and unit are required", "warning")
                        else:
                            try:
                                cursor.execute(
                                    "INSERT INTO usage_metrics (tenant_id, name, unit) VALUES (%s, %s, %s)",
                                    (tenant_id, name.strip(), unit.strip())
                                )
                                conn.commit()
                                show_toast(f"Metric '{name}' added successfully", "success")
                                st.rerun()
                            except Exception as e:
                                show_toast(f"Error: {str(e)}", "error")
                                if "duplicate" in str(e).lower():
                                    st.error("A metric with this name already exists")

        except Exception as e:
            show_toast(f"Error loading metrics: {str(e)}", "error")
            st.error("Failed to load metrics data. Please try again.")
            if user.get("role") == "superadmin":
                st.exception(e)
        finally:
            conn.close()
            
    # Help section
    with st.expander("ℹ️ Usage Metrics Help"):
        st.markdown("""
        **Usage Metrics Guide:**
        - Metrics define what you want to track and bill for
        - Each metric should have a clear name and unit
        - Examples:
          - `API Calls` measured in `requests`
          - `Storage` measured in `GB`
          - `Active Users` measured in `seats`
        - Once created, metrics will be available for:
          - Usage tracking
          - Billing plans configuration
          - Analytics reports
        """)