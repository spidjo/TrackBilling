# src/views/client/subscription_client.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils.session import init_session_state, validate_session
from utils.ui_helpers import show_toast, loading_spinner 
from db.database import get_db_connection
import plotly.graph_objects as go

# Custom CSS for professional styling matching admin_dashboard
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
        margin-bottom: 1rem;
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
    
    .plan-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border: 2px solid #E5E7EB;
        transition: all 0.3s ease;
    }
    .plan-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }
    .plan-card.selected {
        border-color: var(--primary);
        background-color: #F5F3FF;
    }
</style>
""", unsafe_allow_html=True)

def format_currency(value):
    """Format currency values consistently"""
    return f"R{float(value):,.2f}" if value else "R0.00"

def subscription_client():
    """Professional client interface for managing subscriptions with enhanced UI/UX."""
    
    # Initialize page config first to prevent resizing
    st.set_page_config(
        page_title="My Subscription",
        layout="wide",
        page_icon="📦"
    )
    
    init_session_state()
    
    # Session validation with redirect
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()

    user_id = st.session_state.user_id
    tenant_id = st.session_state.tenant_id

    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">📦 My Subscription Plan</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # --- Get active subscription
        with loading_spinner("Loading your subscription..."):
            cursor.execute("""
                SELECT p.id, s.id, p.name, p.description, p.monthly_fee, 
                       p.included_units, p.overage_rate, s.start_date, s.end_date, s.is_active
                FROM subscriptions s
                JOIN plans p ON s.plan_id = p.id
                WHERE s.user_id = %s AND s.is_active
            """, (user_id,))
            active_subscription = cursor.fetchone()

        if active_subscription:
            # Current subscription section
            st.markdown("""
            <div class="section-header">
                <div class="icon">📄</div>
                <h2>Current Subscription</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Use metric cards for better visual presentation
            cols = st.columns(4)
            with cols[0]:
                st.markdown(f"""
                <div class="metric-card metric-positive">
                    <h3>Current Plan</h3>
                    <h2>{active_subscription[2]}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(f"""
                <div class="metric-card metric-neutral">
                    <h3>Monthly Fee</h3>
                    <h2>{format_currency(active_subscription[4])}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            with cols[2]:
                st.markdown(f"""
                <div class="metric-card metric-info">
                    <h3>Included Units</h3>
                    <h2>{active_subscription[5]:,}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            with cols[3]:
                status_color = "metric-positive" if active_subscription[9] else "metric-negative"
                st.markdown(f"""
                <div class="metric-card {status_color}">
                    <h3>Status</h3>
                    <h2>{"🟢 Active" if active_subscription[9] else "🔴 Inactive"}</h2>
                </div>
                """, unsafe_allow_html=True)

            # Additional details in expandable section
            with st.expander("📋 Subscription Details", expanded=False):
                detail_cols = st.columns(2)
                with detail_cols[0]:
                    st.markdown(f"**Description:** {active_subscription[3]}")
                    st.markdown(f"**Overage Rate:** {format_currency(active_subscription[6])}/unit")
                with detail_cols[1]:
                    st.markdown(f"**Start Date:** {format_date(active_subscription[7])}")
                    st.markdown(f"**End Date:** {format_date(active_subscription[8]) or 'Ongoing'}")

            # Cancellation flow with improved UI
            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
            
            if not st.session_state.get('show_cancellation_confirmation', False):
                if st.button(
                    "❌ Cancel Subscription", 
                    type="primary", 
                    use_container_width=True,
                    key="cancel_btn"
                ):
                    st.session_state.show_cancellation_confirmation = True
                    st.rerun()

            if st.session_state.get('show_cancellation_confirmation', False):
                st.markdown("""
                <div class="alert-card alert-warning">
                    <h3>⚠️ Confirm Cancellation</h3>
                    <p>Are you sure you want to cancel your subscription? This action cannot be undone.</p>
                </div>
                """, unsafe_allow_html=True)
                
                confirm_cols = st.columns([1, 1, 2])
                with confirm_cols[0]:
                    if st.button(
                        "✅ Confirm Cancellation",
                        type="primary",
                        key="confirm_cancel"
                    ):
                        handle_subscription_cancellation(
                            user_id, 
                            tenant_id, 
                            active_subscription[1], 
                            active_subscription[0]
                        )
                with confirm_cols[1]:
                    if st.button(
                        "❌ Keep Subscription",
                        key="keep_subscription"
                    ):
                        del st.session_state.show_cancellation_confirmation
                        st.rerun()

        else:
            st.markdown("""
            <div class="alert-card alert-info">
                <h3>ℹ️ No Active Subscription</h3>
                <p>You don't have an active subscription. Choose a plan below to get started.</p>
            </div>
            """, unsafe_allow_html=True)

        # --- List available plans
        st.markdown("""
        <div class="section-header">
            <div class="icon">📋</div>
            <h2>Available Plans</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with loading_spinner("Loading available plans..."):
            cursor.execute("""
                SELECT id, name, description, monthly_fee, included_units, overage_rate 
                FROM plans 
                WHERE tenant_id = %s
                ORDER BY monthly_fee
            """, (tenant_id,))
            plans = cursor.fetchall()

        if not plans:
            st.markdown("""
            <div class="alert-card alert-warning">
                <h3>⚠️ No Plans Available</h3>
                <p>No plans are currently available for your organization. Please contact your administrator.</p>
            </div>
            """, unsafe_allow_html=True)
            return

        # Display plans in tabs with improved UI
        tab1, tab2 = st.tabs(["📊 Plan Selection", "💰 Billing Estimate"])
        
        with tab1:
            selected_plan = display_plan_selection(plans, active_subscription)
        
        with tab2:
            display_billing_estimate(selected_plan)

        # Subscription button with confirmation flow
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        if not st.session_state.get('show_subscription_confirmation', False):
            if st.button(
                "✅ Subscribe to Selected Plan", 
                type="primary", 
                use_container_width=True,
                key="initial_subscribe_btn"
            ):
                if active_subscription:
                    st.session_state.show_subscription_confirmation = True
                    st.rerun()
                else:
                    handle_new_subscription(user_id, tenant_id, selected_plan[0])

        # Confirmation dialog for existing subscribers
        if st.session_state.get('show_subscription_confirmation', False):
            st.markdown("""
            <div class="alert-card alert-warning">
                <h3>⚠️ Subscription Change</h3>
                <p>This will replace your current subscription. Are you sure you want to proceed?</p>
            </div>
            """, unsafe_allow_html=True)
            
            confirm_cols = st.columns([1, 1, 2])
            with confirm_cols[0]:
                if st.button(
                    "✅ Confirm Change",
                    type="primary",
                    key="confirm_subscribe"
                ):
                    handle_new_subscription(
                        user_id, 
                        tenant_id, 
                        selected_plan[0], 
                        active_subscription
                    )
            with confirm_cols[1]:
                if st.button(
                    "❌ Keep Current Plan",
                    key="cancel_subscribe"
                ):
                    del st.session_state.show_subscription_confirmation
                    st.rerun()

        # Add usage history section
        st.markdown("""
        <div class="section-header">
            <div class="icon">📈</div>
            <h2>Usage History</h2>
        </div>
        """, unsafe_allow_html=True)
        
        display_usage_history(user_id, tenant_id)

    except Exception as e:
        st.markdown(f"""
        <div class="alert-card alert-danger">
            <h3>❌ Error</h3>
            <p>An unexpected error occurred: {str(e)}</p>
        </div>
        """, unsafe_allow_html=True)
    finally:
        if 'conn' in locals():
            conn.close()

def format_date(date_value):
    """Format date for display"""
    if isinstance(date_value, datetime):
        return date_value.strftime('%d %b %Y')
    return date_value

def display_plan_selection(plans, active_subscription=None):
    """Display plan selection interface with enhanced UI"""
    # Initialize session state for selected plan
    if 'selected_plan_idx' not in st.session_state:
        st.session_state.selected_plan_idx = 0
    
    # Display plans as cards in columns
    cols = st.columns(len(plans))
    for idx, plan in enumerate(plans):
        with cols[idx]:
            is_selected = idx == st.session_state.selected_plan_idx
            is_current = active_subscription and active_subscription[0] == plan[0]
            
            card_class = "plan-card selected" if is_selected else "plan-card"
            if is_current:
                card_class += " alert-success"
            
            st.markdown(f"""
            <div class="{card_class}" onclick="window.streamlit.setComponentValue({idx})">
                <h3>{plan[1]}{' (Current)' if is_current else ''}</h3>
                <h2 style="color: var(--primary); margin: 1rem 0;">{format_currency(plan[3])}/mo</h2>
                <p>{plan[2]}</p>
                <div style="margin-top: 1rem;">
                    <p>📊 {plan[4]:,} included units</p>
                    <p>⚡ {format_currency(plan[5])}/unit overage</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Select {plan[1]}", key=f"select_plan_{idx}", use_container_width=True):
                st.session_state.selected_plan_idx = idx
                st.rerun()
    
    selected_plan = plans[st.session_state.selected_plan_idx]
    
    return selected_plan

def display_billing_estimate(plan):
    """Display billing estimate calculator with enhanced visuals"""
    st.markdown("""
    <div class="section-header">
        <div class="icon">💰</div>
        <h2>Cost Estimator</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Usage slider with better styling
    estimated_usage = st.slider(
        "Estimated Monthly Usage (units)",
        min_value=plan[4],
        max_value=plan[4] * 5,
        value=plan[4],
        step=10,
        key="usage_slider",
        help="Adjust the slider to estimate your monthly usage"
    )
    
    # Calculate costs
    overage = max(0, estimated_usage - plan[4])
    overage_cost = overage * plan[5]
    total_cost = plan[3] + overage_cost
    
    # Display metrics in cards
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"""
        <div class="metric-card metric-neutral">
            <h3>Base Fee</h3>
            <h2>{format_currency(plan[3])}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown(f"""
        <div class="metric-card metric-{'warning' if overage > 0 else 'neutral'}">
            <h3>Overage Cost</h3>
            <h2>{format_currency(overage_cost)}</h2>
            <p>{overage} extra units</p>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        st.markdown(f"""
        <div class="metric-card metric-positive">
            <h3>Total Estimated</h3>
            <h2>{format_currency(total_cost)}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Visual representation
    if plan[4] > 0:
        usage_pct = (estimated_usage / (plan[4] * 1.2)) * 100  # Scale to 120% of included
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = estimated_usage,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Usage vs Included Units"},
            delta = {'reference': plan[4], 'increasing': {'color': "#EF4444"}},
            gauge = {
                'axis': {'range': [None, plan[4] * 1.2]},
                'bar': {'color': "#4F46E5"},
                'steps': [
                    {'range': [0, plan[4]], 'color': "#D1FAE5"},
                    {'range': [plan[4], plan[4] * 1.2], 'color': "#FEE2E2"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': plan[4]
                }
            }
        ))
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    st.caption("💡 Note: This is an estimate only. Actual usage and costs may vary.")

def display_usage_history(user_id, tenant_id):
    """Display usage history with charts"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT usage_date, metric_name, usage_amount 
            FROM usage_records 
            WHERE user_id = %s AND tenant_id = %s 
            ORDER BY usage_date DESC 
            LIMIT 100
        """, (user_id, tenant_id))
        usage_data = cursor.fetchall()
        
        if usage_data:
            df = pd.DataFrame(usage_data, columns=["Date", "Metric", "Quantity"])
            df["Date"] = pd.to_datetime(df["Date"])
            
            # Monthly usage trend
            monthly_usage = df.groupby([df["Date"].dt.to_period("M"), "Metric"])["Quantity"].sum().reset_index()
            monthly_usage["Date"] = monthly_usage["Date"].astype(str)
            
            fig = px.line(
                monthly_usage,
                x="Date",
                y="Quantity",
                color="Metric",
                title="Monthly Usage Trend",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Recent usage table
            with st.expander("📋 Recent Usage Details", expanded=False):
                st.dataframe(
                    df.sort_values("Date", ascending=False).head(10),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Date": st.column_config.DateColumn(),
                        "Quantity": st.column_config.NumberColumn(format="%d units")
                    }
                )
        else:
            st.info("No usage history available yet.")
            
    except Exception as e:
        st.error(f"Error loading usage history: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def handle_subscription_cancellation(user_id, tenant_id, subscription_id, plan_id):
    """Handle subscription cancellation with proper error handling"""
    with loading_spinner("Processing cancellation..."):
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE subscriptions 
                SET is_active = False, end_date = %s 
                WHERE id = %s
            """, (datetime.utcnow().strftime("%Y-%m-%d"), subscription_id))

            cursor.execute("""
                INSERT INTO subscription_audit (
                    user_id, tenant_id, action, old_plan_id, new_plan_id, timestamp
                ) VALUES (%s, %s, 'cancelled', %s, NULL, %s)
            """, (user_id, tenant_id, plan_id, datetime.utcnow().isoformat()))

            conn.commit()
            show_toast("✅ Subscription cancelled successfully", "success")
            for key in ['show_cancellation_confirmation', 'subscription_confirmed']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        except Exception as e:
            st.markdown(f"""
            <div class="alert-card alert-danger">
                <h3>❌ Cancellation Failed</h3>
                <p>Error cancelling subscription: {str(e)}</p>
            </div>
            """, unsafe_allow_html=True)
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

def handle_new_subscription(user_id, tenant_id, plan_id, active_subscription=None):
    """Handle new subscription with proper error handling"""
    with loading_spinner("Processing your subscription..."):
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if active_subscription:
                cursor.execute("""
                    UPDATE subscriptions 
                    SET is_active = False, end_date = %s 
                    WHERE user_id = %s AND is_active = True
                """, (datetime.utcnow().strftime("%Y-%m-%d"), user_id))

            cursor.execute("""
                INSERT INTO subscriptions (
                    user_id, tenant_id, plan_id, start_date, is_active
                ) VALUES (%s, %s, %s, %s, True)
            """, (user_id, tenant_id, plan_id, datetime.utcnow().strftime("%Y-%m-%d")))

            cursor.execute("""
                INSERT INTO subscription_audit (
                    user_id, tenant_id, action, old_plan_id, new_plan_id, timestamp
                ) VALUES (%s, %s, 'subscribed', %s, %s, %s)
            """, (
                user_id, 
                tenant_id, 
                active_subscription[0] if active_subscription else None, 
                plan_id, 
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            show_toast("🎉 Subscription successful! Your new plan is now active.", "success")
            for key in ['subscription_confirmed', 'show_subscription_confirmation']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        except Exception as e:
            st.markdown(f"""
            <div class="alert-card alert-danger">
                <h3>❌ Subscription Failed</h3>
                <p>Error processing subscription: {str(e)}</p>
            </div>
            """, unsafe_allow_html=True)
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    subscription_client()