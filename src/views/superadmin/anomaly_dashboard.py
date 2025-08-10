import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any
from db.database import get_db_connection
from utils.session_guard import require_login
from utils.session import init_session_state
from utils.email_utils import send_email
from functools import wraps
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Initialize session state
init_session_state()

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

# Custom CSS for better styling
st.markdown("""
<style>
    .anomaly-card {
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .severity-low { border-left: 5px solid #4CAF50; }
    .severity-medium { border-left: 5px solid #FFC107; }
    .severity-high { border-left: 5px solid #F44336; }
    .severity-critical { border-left: 5px solid #9C27B0; }
    .metric-badge {
        background-color: #2196F3;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        display: inline-block;
    }
    .status-badge {
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        display: inline-block;
    }
    .status-open { background-color: #FF9800; color: white; }
    .status-investigating { background-color: #2196F3; color: white; }
    .status-resolved { background-color: #4CAF50; color: white; }
    .status-ignored { background-color: #9E9E9E; color: white; }
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
        user = st.session_state.get("user")
        if user and user["role"] != "superadmin":
            query += " AND a.tenant_id = %s"
            params.append(user["tenant_id"])
            if user["role"] == "TeamMember":
                query += " AND a.assigned_to_user_id = %s"
                params.append(user["id"])
        
        # Status filter
        if status_filter != "All":
            query += " AND a.status = %s"
            params.append(status_filter)

        query += " ORDER BY a.detected_at DESC"
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
            return df
        return pd.DataFrame()

def update_anomaly_status(anomaly_id: int, new_status: str, user: Dict[str, Any]) -> None:
    """Update anomaly status and log the change."""
    with get_db_connection() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE anomalies SET status = %s WHERE id = %s", 
                (new_status, anomaly_id)
            )
            log_resolution_comment(
                anomaly_id, 
                f"Status changed to {new_status} by {user.get('name', 'System')}",
                performed_by=user.get("name", "System")
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
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE anomalies SET assigned_to = %s WHERE id = %s", 
                (assigned_to_id, anomaly_id)
            )
            log_resolution_comment(
                anomaly_id,
                f"Assigned to user ID {assigned_to_id} by {user.get('name', 'System')}",
                performed_by=user.get("name", "System")
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
        "low": "#4CAF50",
        "medium": "#FFC107",
        "high": "#F44336",
        "critical": "#9C27B0"
    }.get(severity.lower(), "#9E9E9E")

def status_color(status: str) -> str:
    """Get color for status."""
    return {
        "open": "#FF9800",
        "investigating": "#2196F3",
        "resolved": "#4CAF50",
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
    st.set_page_config(page_title="🔍 Anomaly Dashboard", layout="wide")
    require_login('superadmin', 'admin')

    st.title("🔍 Anomaly Dashboard")
    st.markdown("Monitor, investigate, and resolve detected anomalies across your platform.")
    
    # Sidebar filters
    with st.sidebar:
        st.subheader("🔍 Filters")
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
            st.metric("Total Anomalies", len(df))
        with col2:
            st.metric("Open", len(df[df['status'] == 'open']))
        with col3:
            st.metric("Investigating", len(df[df['status'] == 'investigating']))
        with col4:
            st.metric("Resolved", len(df[df['status'] == 'resolved']))

        # Export buttons
        st.download_button(
            "📥 Export CSV", 
            data=export_csv(df), 
            file_name=f"anomalies_{datetime.now().strftime('%Y%m%d')}.csv", 
            mime="text/csv",
            use_container_width=True
        )

        # Dashboard tabs
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Trends", "📋 Details"])

        with tab1:  # Overview tab
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("By Severity")
                severity_counts = df['severity'].value_counts().reindex([e.value for e in Severity], fill_value=0)
                fig = px.pie(
                    severity_counts, 
                    names=severity_counts.index.str.capitalize(), 
                    values=severity_counts.values,
                    color=severity_counts.index,
                    color_discrete_map={
                        "low": "#4CAF50",
                        "medium": "#FFC107",
                        "high": "#F44336",
                        "critical": "#9C27B0"
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("By Status")
                status_counts = df['status'].value_counts().reindex([e.value for e in Status], fill_value=0)
                fig = px.bar(
                    status_counts,
                    x=status_counts.index.str.capitalize(),
                    y=status_counts.values,
                    color=status_counts.index,
                    color_discrete_map={
                        "open": "#FF9800",
                        "investigating": "#2196F3",
                        "resolved": "#4CAF50",
                        "ignored": "#9E9E9E"
                    }
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab2:  # Trends tab
            st.subheader("Daily Trend")
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

        with tab3:  # Details tab
            st.subheader("Anomaly Details")
            
            for _, row in df.iterrows():
                severity_class = f"severity-{row['severity']}"
                with st.container():
                    st.markdown(f"""
                    <div class="anomaly-card {severity_class}">
                        <div style="display: flex; justify-content: space-between;">
                            <h3>{row['anomaly_type'].capitalize()} in {row['metric_name']}</h3>
                            <div>
                                <span class="status-badge status-{row['status']}">{row['status'].capitalize()}</span>
                                <span style="color: {severity_color(row['severity'])}; font-weight: bold;">{row['severity'].upper()}</span>
                            </div>
                        </div>
                        <p><strong>Tenant:</strong> {row['tenant']} | <strong>Detected:</strong> {row['detected_at'].strftime('%Y-%m-%d %H:%M')}</p>
                        <p><strong>Value:</strong> {row['detected_value']} (Expected: {row['expected_value']}, Threshold: {row['threshold_value']})</p>
                        <p>{row['anomaly_description']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Action buttons
                    current_user = st.session_state.get("user", {})
                    with st.expander("Actions", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_status = st.selectbox(
                                "Update Status",
                                options=[e.value for e in Status],
                                index=[e.value for e in Status].index(row["status"]),
                                key=f"status_{row['id']}"
                            )
                            if st.button("Update", key=f"update_{row['id']}"):
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
                            if st.button("Assign", key=f"assign_btn_{row['id']}"):
                                if new_assignee != "Unassigned":
                                    assignee_id = [k for k, v in admin_users.items() if v == new_assignee][0]
                                    assign_anomaly(row['id'], assignee_id, current_user)
                                    st.rerun()

                        # Show resolution logs
                        logs = get_resolution_logs(row['id'])
                        if logs:
                            st.subheader("Activity Log")
                            for log in logs:
                                st.markdown(f"**{log[1]}**: {log[0]}")

    else:
        st.info("No anomalies found for the selected filters.")

if __name__ == "__main__":
    render_anomaly_dashboard()