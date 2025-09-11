import streamlit as st
import pandas as pd
from db.database import get_db_connection
from utils.session import init_session_state, validate_session
from utils.ui_helpers import show_toast

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
    
    .plan-table-header {
        background: linear-gradient(90deg, #4F46E5, #6366F1);
        color: white;
        padding: 0.75rem;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
    
    .plan-table-row {
        padding: 1rem;
        border-bottom: 1px solid #E5E7EB;
        transition: background-color 0.2s ease;
    }
    
    .plan-table-row:hover {
        background-color: #F9FAFB;
    }
</style>
""", unsafe_allow_html=True)

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"

def plan_metric_limits_admin():
    """Professional admin interface for managing plan metric limits"""
    
    # Initialize session and page config
    st.set_page_config(
        page_title="📏 Plan Metric Limits Manager", 
        layout="wide",
        page_icon="📏"
    )
    
    init_session_state() 
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()

    tenant_id = st.session_state.tenant_id

    # Professional header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">📏 Plan Metric Limits Management</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Configure usage limits and pricing</span>
            <button onclick="window.location.reload()" style="background-color: #4F46E5; color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; cursor: pointer;">Refresh Data</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    try:
        # Database Connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            cursor.execute("SELECT COUNT(*) FROM plans WHERE tenant_id = %s", (tenant_id,))
            plan_count = cursor.fetchone()[0]
            st.markdown(f"""
            <div class="metric-card metric-positive">
                <h3>Available Plans</h3>
                <h2>{plan_count:,}</h2>
                <p style="color: #6B7280; margin-top: 0.5rem;">Total plans configured</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            cursor.execute("SELECT COUNT(*) FROM usage_metrics WHERE tenant_id = %s", (tenant_id,))
            metric_count = cursor.fetchone()[0]
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Tracked Metrics</h3>
                <h2>{metric_count:,}</h2>
                <p style="color: #6B7280; margin-top: 0.5rem;">Available metrics</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            cursor.execute("""
                SELECT COUNT(DISTINCT plan_id) FROM plan_metric_limits 
                WHERE plan_id IN (SELECT id FROM plans WHERE tenant_id = %s)
            """, (tenant_id,))
            configured_plans = cursor.fetchone()[0]
            st.markdown(f"""
            <div class="metric-card metric-{'warning' if configured_plans < plan_count else 'success'}">
                <h3>Configured Plans</h3>
                <h2>{configured_plans:,}/{plan_count:,}</h2>
                <p style="color: #6B7280; margin-top: 0.5rem;">Plans with metric limits</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # Plan Selection Section
        st.markdown("""
        <div class="section-header">
            <div class="icon">📋</div>
            <h2>Plan Selection</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            cursor.execute(
                "SELECT id, name, description FROM plans WHERE tenant_id = %s ORDER BY name", 
                (tenant_id,)
            )
            plans = cursor.fetchall()

            if not plans:
                st.markdown("""
                <div class="alert-card alert-warning">
                    <h3>📝 No Plans Available</h3>
                    <p>You need to create plans before configuring metric limits.</p>
                    <p>Visit the Plans Management section to create your first plan.</p>
                </div>
                """, unsafe_allow_html=True)
                conn.close()
                return

            # Plan selection with enhanced styling
            selected_plan = st.selectbox(
                "**Select Plan to Configure**", 
                plans, 
                format_func=lambda x: f"{x[1]} - {x[2]}" if x[2] else x[1],
                help="Choose the plan you want to configure metric limits for",
                key="plan_select"
            )
            plan_id = selected_plan[0]

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # Current Metric Limits Section
        st.markdown("""
        <div class="section-header">
            <div class="icon">⚙️</div>
            <h2>Current Metric Limits</h2>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT pml.id, mt.name, mt.unit, pml.metric_limit, pml.overage_rate
            FROM plan_metric_limits pml
            JOIN usage_metrics mt ON pml.metric_id = mt.id
            WHERE pml.plan_id = %s
            ORDER BY mt.name
        """, (plan_id,))
        existing_limits = cursor.fetchall()

        if existing_limits:
            st.markdown(f"""
            <div class="alert-card alert-info">
                <h3>📊 Configured Metrics for {selected_plan[1]}</h3>
                <p>Manage the usage limits and overage rates for each metric in this plan.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Create a professional table layout
            st.markdown("""
            <div style="background: white; border-radius: 12px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div class="plan-table-header">
                    <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr; gap: 1rem; align-items: center;">
                        <div>Metric</div>
                        <div>Unit</div>
                        <div>Included Units</div>
                        <div>Overage Rate</div>
                        <div style="text-align: center;">Actions</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            for limit_id, metric_name, unit, metric_limit, overage_rate in existing_limits:
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{metric_name}**")
                    st.caption(f"Unit: {unit}")
                
                with col2:
                    st.markdown(f"`{unit}`")
                
                with col3:
                    new_limit = st.number_input(
                        "Included units", 
                        min_value=0, 
                        value=int(metric_limit),
                        key=f"limit_{limit_id}",
                        label_visibility="collapsed"
                    )
                
                with col4:
                    new_rate = st.number_input(
                        "Overage rate", 
                        min_value=0.0, 
                        value=float(overage_rate),
                        step=0.01,
                        format="%.2f",
                        key=f"rate_{limit_id}",
                        label_visibility="collapsed"
                    )
                
                with col5:
                    if st.button(
                        "💾 Save", 
                        key=f"update_{limit_id}",
                        use_container_width=True,
                        type="primary"
                    ):
                        try:
                            cursor.execute("""
                                UPDATE plan_metric_limits
                                SET metric_limit = %s, overage_rate = %s
                                WHERE id = %s
                            """, (new_limit, new_rate, limit_id))
                            conn.commit()
                            show_toast(f"✅ {metric_name} limits updated successfully")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating {metric_name}: {str(e)}")
                            conn.rollback()
            
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert-card alert-warning">
                <h3>📝 No Metric Limits Configured</h3>
                <p>This plan doesn't have any metric limits defined yet.</p>
                <p>Add metrics below to start tracking usage and billing for this plan.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # Add New Metric Limits Section
        st.markdown("""
        <div class="section-header">
            <div class="icon">➕</div>
            <h2>Add New Metric to Plan</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Get metrics not yet added to the selected plan
        cursor.execute("""
            SELECT id, name, unit FROM usage_metrics 
            WHERE tenant_id = %s AND id NOT IN (
                SELECT metric_id FROM plan_metric_limits WHERE plan_id = %s
            )
            ORDER BY name
        """, (tenant_id, plan_id))
        available_metrics = cursor.fetchall()

        if not available_metrics:
            st.markdown("""
            <div class="alert-card alert-success">
                <h3>🎉 All Metrics Configured</h3>
                <p>All available metrics are already assigned to this plan.</p>
                <p>You can modify existing limits above or create new metrics in the Metrics Management section.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            with st.form(key="add_metric_form", clear_on_submit=True):
                st.markdown("""
                <div style="background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    new_metric = st.selectbox(
                        "**Select Metric**", 
                        available_metrics, 
                        format_func=lambda x: f"{x[1]} ({x[2]})",
                        help="Choose a metric to add to this plan",
                        key="new_metric_select"
                    )
                
                with col2:
                    new_limit = st.number_input(
                        "**Included Units**", 
                        min_value=0,
                        value=1000,
                        key="add_limit",
                        help="Number of units included in the plan"
                    )
                
                with col3:
                    new_rate = st.number_input(
                        "**Overage Rate (R/unit)**", 
                        min_value=0.0,
                        value=0.10,
                        step=0.01,
                        format="%.2f",
                        key="add_rate",
                        help="Rate charged per unit over the included limit"
                    )
                
                st.markdown("""
                <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #E5E7EB;">
                """, unsafe_allow_html=True)
                
                if st.form_submit_button(
                    "🚀 Add Metric to Plan", 
                    type="primary",
                    use_container_width=True
                ):
                    try:
                        cursor.execute("""
                            INSERT INTO plan_metric_limits (plan_id, metric_id, metric_limit, overage_rate)
                            VALUES (%s, %s, %s, %s)
                        """, (plan_id, new_metric[0], new_limit, new_rate))
                        conn.commit()
                        show_toast(f"✅ {new_metric[1]} added to {selected_plan[1]} plan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding metric: {str(e)}")
                        conn.rollback()
                
                st.markdown("</div></div>", unsafe_allow_html=True)

    except Exception as e:
        st.markdown("""
        <div class="alert-card alert-danger">
            <h3>❌ Database Error</h3>
            <p>Failed to load plan data. Please try refreshing the page or contact support if the issue persists.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.role == "superadmin":
            with st.expander("Technical Details"):
                st.exception(e)
    finally:
        if 'conn' in locals():
            conn.close()

    # Help section
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    with st.expander("📖 Plan Metric Limits Guide", expanded=False):
        st.markdown("""
        ### Best Practices for Metric Limits
        
        **🎯 Setting Appropriate Limits:**
        - **Starter Plans**: Set lower limits to encourage upgrades
        - **Business Plans**: Offer higher limits with competitive overage rates  
        - **Enterprise Plans**: Consider unlimited or very high limits
        
        **💰 Overage Rate Strategy:**
        - **Competitive Pricing**: Research market rates for similar services
        - **Tiered Overage**: Consider lower rates for higher usage tiers
        - **Predictable Billing**: Ensure overage costs are transparent to customers
        
        **📊 Usage Monitoring:**
        - **Regular Reviews**: Monitor which metrics are most used
        - **Customer Feedback**: Adjust limits based on customer needs
        - **Revenue Optimization**: Balance included limits vs overage revenue
        """)
        
        st.info("""
        💡 **Pro Tip**: Start with conservative limits and adjust based on actual usage patterns. 
        It's easier to increase limits than to decrease them later.
        """)

if __name__ == "__main__":
    plan_metric_limits_admin()