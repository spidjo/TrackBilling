import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any
from db.database import get_db_connection
from utils.session import init_session_state, validate_session
from utils.email_utils import send_email
from functools import wraps
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Enums
class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Status(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    IGNORED = "ignored"

# Custom CSS for professional styling
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
    
    .anomaly-card {
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-left: 4px solid;
        transition: all 0.3s ease;
    }
    .anomaly-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }
    .severity-low { 
        border-left-color: var(--secondary);
        background-color: #D1FAE5;
    }
    .severity-medium { 
        border-left-color: var(--warning);
        background-color: #FEF3C7;
    }
    .severity-high { 
        border-left-color: var(--danger);
        background-color: #FEE2E2;
    }
    .severity-critical { 
        border-left-color: #9C27B0;
        background-color: #F3E5F5;
    }
    
    .status-badge {
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .status-open { 
        background-color: #FF9800; 
        color: white; 
    }
    .status-investigating { 
        background-color: var(--info); 
        color: white; 
    }
    .status-resolved { 
        background-color: var(--secondary); 
        color: white; 
    }
    .status-ignored { 
        background-color: #9E9E9E; 
        color: white; 
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
    
    .filter-section {
        background-color: white;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    }
</style>
""", unsafe_allow_html=True)

def fetch_anomalies(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: Optional[int] = None,
    anomaly_type: Optional[str] = None,
    severity_filter: str = "All",
    status_filter: str = "All"
) -> pd.DataFrame:
    """Fetch anomalies from database with optional filters."""
    with get_db_connection() as conn:
        query = """
            SELECT
                a.id, t.name AS tenant, a.tenant_id,
                u.first_name || ' ' || u.last_name AS user,
                a.assigned_to,
                m.name AS metric_name,
                a.anomaly_type, a.anomaly_description,
                a.detected_value, a.expected_value, a.threshold_value, 
                a.detected_at,
                a.severity, a.status, u.email AS user_email
            FROM anomalies a
            LEFT JOIN tenants t ON a.tenant_id = t.id
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN usage_metrics m ON a.metric_id = m.id
            WHERE 1=1
        """
        params = []
        
        # Date filters
        if start_date:
            query += " AND a.detected_at >= %s"
            params.append(start_date)
        if end_date:
            query += " AND a.detected_at < %s"
            params.append((pd.to_datetime(end_date) + timedelta(days=1)).strftime("%Y-%m-%d"))
        
        # Other filters
        if tenant_id:
            query += " AND a.tenant_id = %s"
            params.append(tenant_id)
        if anomaly_type:
            query += " AND a.anomaly_type = %s"
            params.append(anomaly_type)
        if severity_filter != "All":
            query += " AND a.severity = %s"
            params.append(severity_filter)
        
        # Role-based filtering
        if st.session_state.role != "superadmin":
            query += " AND a.tenant_id = %s"
            params.append(st.session_state.tenant_id)
            if st.session_state.role == "TeamMember":
                query += " AND a.assigned_to_user_id = %s"
                params.append(st.session_state.user_id)
        
        # Status filter
        if status_filter != "All":
            query += " AND a.status = %s"
            params.append(status_filter)

        query += " ORDER BY a.detected_at DESC"
        
        print(f"Executing query: {query} with params: {params}")
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
            return df
        return pd.DataFrame()

def update_anomaly_status(anomaly_id: int, new_status: str, user: Dict[str, Any]) -> None:
    """Update anomaly status and log the change."""
    user_id = st.session_state.user_id
    with get_db_connection() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE anomalies SET status = %s WHERE id = %s", 
                (new_status, anomaly_id)
            )
            log_resolution_comment(
                anomaly_id, 
                f"Status changed to {new_status} by {get_current_user_name(user_id)}",
                performed_by=get_current_user_name(user_id)
            )
            if new_status.lower() == "resolved":
                notify_resolution(anomaly_id)
            conn.commit()
            st.toast(f"✅ Status updated to {new_status}", icon="✅")
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to update anomaly status: {str(e)}")
            raise

def assign_anomaly(anomaly_id: int, assigned_to_id: int, user: Dict[str, Any]) -> None:
    """Assign anomaly to a user and notify them."""
    user_id = st.session_state.user_id
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE anomalies SET assigned_to = %s WHERE id = %s", 
                (assigned_to_id, anomaly_id)
            )
            log_resolution_comment(
                anomaly_id,
                f"Assigned to user ID {assigned_to_id} by {get_current_user_name(user_id)}",
                performed_by=get_current_user_name(user_id)
            )
            notify_assignment(anomaly_id, assigned_to_id)
            st.toast("✅ Anomaly assigned successfully", icon="✅")
    finally:
        conn.close()

def log_resolution_comment(anomaly_id: int, comment: str, performed_by: str) -> None:
    """Log a comment about anomaly resolution."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO anomaly_logs (anomaly_id, action, comment, performed_by, created_at) VALUES (%s, %s, %s, %s, %s)",
                (anomaly_id, 'comment', comment, performed_by, datetime.now())
            )
    finally:
        conn.close()

def get_resolution_logs(anomaly_id: int) -> List[Dict[str, Any]]:
    """Get resolution logs for an anomaly."""
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT comment, created_at FROM anomaly_logs WHERE anomaly_id = %s ORDER BY created_at DESC",
            (anomaly_id,)
        ).fetchall()
    finally:
        conn.close()

def fetch_admin_users() -> Dict[int, str]:
    """Fetch all admin users for assignment dropdown."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            "SELECT id, first_name || ' ' || last_name AS name FROM users WHERE role = 'admin'", 
            conn
        )
        return df.set_index("id")["name"].to_dict()
    finally:
        conn.close()

def notify_assignment(anomaly_id: int, assigned_to_id: int) -> None:
    """Notify user about new anomaly assignment."""
    conn = get_db_connection()
    try:
        user_info = conn.execute(
            "SELECT name, email FROM users WHERE id = %s", 
            (assigned_to_id,)
        ).fetchone()
        if user_info:
            send_email(
                to_email=user_info["email"],
                subject="New Anomaly Assigned",
                body_text=f"Hello {user_info['name']},\n\nAn anomaly (ID: {anomaly_id}) has been assigned to you."
            )
    finally:
        conn.close()

def severity_color(severity: str) -> str:
    """Get color for severity level."""
    return {
        "low": "#10B981",
        "medium": "#F59E0B",
        "high": "#EF4444",
        "critical": "#9C27B0"
    }.get(severity.lower(), "#9E9E9E")

def status_color(status: str) -> str:
    """Get color for status."""
    return {
        "open": "#FF9800",
        "investigating": "#3B82F6",
        "resolved": "#10B981",
        "ignored": "#9E9E9E"
    }.get(status.lower(), "#9E9E9E")

def export_csv(df: pd.DataFrame) -> bytes:
    """Export DataFrame to CSV."""
    return df.to_csv(index=False).encode('utf-8')

def export_pdf(df: pd.DataFrame) -> bytes:
    """Export DataFrame to PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Anomaly Report", ln=True, align="C")
    pdf.ln(5)
    
    cols = ["ID", "Tenant", "Metric", "Type", "Severity", "Status", "Detected At"]
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, " | ".join(cols), ln=True)
    pdf.set_font("Arial", size=10)
    
    for _, row in df.iterrows():
        detected_at = row.detected_at.strftime("%Y-%m-%d") if hasattr(row.detected_at, "strftime") else str(row.detected_at)[:10]
        values = [
            str(row.id),
            row.tenant[:20] if pd.notna(row.tenant) else "",
            row.metric_name[:20] if pd.notna(row.metric_name) else "",
            row.anomaly_type,
            row.severity,
            row.status,
            detected_at
        ]
        line = " | ".join(values)
        pdf.multi_cell(0, 8, line)
    
    return pdf.output(dest='S').encode('latin1')

def render_anomaly_dashboard() -> None:
    """Main dashboard rendering function."""
    # Initialize session state
    init_session_state()

    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()
        
    st.set_page_config(
        page_title="🔍 Anomaly Dashboard", 
        layout="wide",
        page_icon="🔍"
    )

    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">🔍 Anomaly Dashboard</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            <button style="background-color: #4F46E5; color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; cursor: pointer;">Refresh Data</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # Sidebar filters
    with st.sidebar:
        st.markdown("""
        <div class="filter-section">
            <h3 style="color: #1F2937; margin-bottom: 1rem;">🔍 Filters</h3>
        """, unsafe_allow_html=True)
        
        today = datetime.today().date()
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", today - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", today)
        
        tenant_id = st.text_input("Tenant ID (optional)", "")
        anomaly_type = st.selectbox("Anomaly Type", ["All", "spike", "drop"], index=0)
        severity_filter = st.selectbox("Severity", ["All"] + [e.value for e in Severity], index=0)
        status_filter = st.selectbox("Status", ["All"] + [e.value for e in Status], index=0)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # Fetch data with filters
    with st.spinner("Loading anomalies..."):
        df = fetch_anomalies(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            tenant_id=int(tenant_id) if tenant_id.strip().isdigit() else None,
            anomaly_type=anomaly_type if anomaly_type != "All" else None,
            severity_filter=severity_filter if severity_filter != "All" else "All",
            status_filter=status_filter if status_filter != "All" else "All"
        )

    if not df.empty:
        df['detected_at'] = pd.to_datetime(df['detected_at'])
        admin_users = fetch_admin_users()

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Total Anomalies</h3>
                <h2>{len(df):,}</h2>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            open_count = len(df[df['status'] == 'open'])
            st.markdown(f"""
            <div class="metric-card metric-{'negative' if open_count > 0 else 'positive'}">
                <h3>Open</h3>
                <h2>{open_count:,}</h2>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            investigating_count = len(df[df['status'] == 'investigating'])
            st.markdown(f"""
            <div class="metric-card metric-warning">
                <h3>Investigating</h3>
                <h2>{investigating_count:,}</h2>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            resolved_count = len(df[df['status'] == 'resolved'])
            st.markdown(f"""
            <div class="metric-card metric-positive">
                <h3>Resolved</h3>
                <h2>{resolved_count:,}</h2>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # Export buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Export CSV", 
                data=export_csv(df), 
                file_name=f"anomalies_{datetime.now().strftime('%Y%m%d')}.csv", 
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            st.download_button(
                "📄 Export PDF", 
                data=export_pdf(df), 
                file_name=f"anomalies_{datetime.now().strftime('%Y%m%d')}.pdf", 
                mime="application/pdf",
                use_container_width=True
            )

        # Dashboard tabs
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Trends", "📋 Details"])

        with tab1:  # Overview tab
            st.markdown("""
            <div class="section-header">
                <div class="icon">📊</div>
                <h2>Anomaly Overview</h2>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div class="section-header">
                    <div class="icon">⚠️</div>
                    <h3>By Severity</h3>
                </div>
                """, unsafe_allow_html=True)
                severity_counts = df['severity'].value_counts().reindex([e.value for e in Severity], fill_value=0)
                fig = px.pie(
                    severity_counts, 
                    names=severity_counts.index.str.capitalize(), 
                    values=severity_counts.values,
                    color=severity_counts.index,
                    color_discrete_map={
                        "low": "#10B981",
                        "medium": "#F59E0B",
                        "high": "#EF4444",
                        "critical": "#9C27B0"
                    }
                )
                fig.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📋</div>
                    <h3>By Status</h3>
                </div>
                """, unsafe_allow_html=True)
                status_counts = df['status'].value_counts().reindex([e.value for e in Status], fill_value=0)
                fig = px.bar(
                    status_counts,
                    x=status_counts.index.str.capitalize(),
                    y=status_counts.values,
                    color=status_counts.index,
                    color_discrete_map={
                        "open": "#FF9800",
                        "investigating": "#3B82F6",
                        "resolved": "#10B981",
                        "ignored": "#9E9E9E"
                    }
                )
                fig.update_layout(
                    xaxis_title="Status",
                    yaxis_title="Count",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab2:  # Trends tab
            st.markdown("""
            <div class="section-header">
                <div class="icon">📈</div>
                <h2>Anomaly Trends</h2>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📅</div>
                    <h3>Daily Trend</h3>
                </div>
                """, unsafe_allow_html=True)
                daily_counts = df.groupby(df['detected_at'].dt.date).size().reset_index(name='count')
                fig = px.line(
                    daily_counts, 
                    x='detected_at', 
                    y='count',
                    title="Anomalies Over Time",
                    markers=True
                )
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Number of Anomalies",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📊</div>
                    <h3>Severity Over Time</h3>
                </div>
                """, unsafe_allow_html=True)
                severity_trend = df.groupby([df['detected_at'].dt.date, 'severity']).size().reset_index(name='count')
                fig = px.line(
                    severity_trend,
                    x='detected_at',
                    y='count',
                    color='severity',
                    color_discrete_map={
                        "low": "#10B981",
                        "medium": "#F59E0B",
                        "high": "#EF4444",
                        "critical": "#9C27B0"
                    },
                    title="Severity Trends Over Time"
                )
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Count",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab3:  # Details tab
            st.markdown("""
            <div class="section-header">
                <div class="icon">📋</div>
                <h2>Anomaly Details</h2>
            </div>
            """, unsafe_allow_html=True)
            
            for _, row in df.iterrows():
                severity_class = f"severity-{row['severity']}"
                with st.container():
                    st.markdown(f"""
                    <div class="anomaly-card {severity_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="margin: 0;">{row['anomaly_type'].capitalize()} in {row['metric_name']}</h3>
                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                <span class="status-badge status-{row['status']}">{row['status'].capitalize()}</span>
                                <span style="color: {severity_color(row['severity'])}; font-weight: bold; padding: 0.3rem 0.8rem; border-radius: 20px; background-color: rgba(255,255,255,0.7);">
                                    {row['severity'].upper()}
                                </span>
                            </div>
                        </div>
                        <p><strong>Tenant:</strong> {row['tenant']} | <strong>Detected:</strong> {row['detected_at'].strftime('%Y-%m-%d %H:%M')}</p>
                        <p><strong>Value:</strong> {row['detected_value']} (Expected: {row['expected_value']}, Threshold: {row['threshold_value']})</p>
                        <p>{row['anomaly_description']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Action buttons
                    current_user = st.session_state.user_id
                    with st.expander("Actions", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_status = st.selectbox(
                                "Update Status",
                                options=[e.value for e in Status],
                                index=[e.value for e in Status].index(row["status"]),
                                key=f"status_{row['id']}"
                            )
                            if st.button("Update Status", key=f"update_{row['id']}", use_container_width=True):
                                update_anomaly_status(row['id'], new_status, current_user)
                                st.rerun()
                        
                        with col2:
                            new_assignee = st.selectbox(
                                "Assign To",
                                options=["Unassigned"] + list(admin_users.values()),
                                index=0 if pd.isna(row["assigned_to"]) or row["assigned_to"] not in admin_users.values()
                                    else list(admin_users.values()).index(row["assigned_to"]) + 1,
                                key=f"assign_{row['id']}"
                            )
                            if st.button("Assign", key=f"assign_btn_{row['id']}", use_container_width=True):
                                if new_assignee != "Unassigned":
                                    assignee_id = [k for k, v in admin_users.items() if v == new_assignee][0]
                                    assign_anomaly(row['id'], assignee_id, current_user)
                                    st.rerun()

                        # Show resolution logs
                        logs = get_resolution_logs(row['id'])
                        if logs:
                            st.markdown("""
                            <div class="section-header">
                                <div class="icon">📝</div>
                                <h4>Activity Log</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            for log in logs:
                                st.markdown(f"""
                                <div style="background-color: #F9FAFB; padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem;">
                                    <strong>{log[1].strftime('%Y-%m-%d %H:%M')}</strong>: {log[0]}
                                </div>
                                """, unsafe_allow_html=True)

    else:
        st.info("No anomalies found for the selected filters.")


def get_current_user_name(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
    except Exception as e:
        st.error(f"Error fetching user name: {e}")
    finally:
        conn.close()
    return result[0] if result else "Unknown User"

if __name__ == "__main__":
    render_anomaly_dashboard()