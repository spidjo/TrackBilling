import streamlit as st
import pandas as pd
from db.database import get_db_connection
from datetime import datetime

# Custom CSS for better styling
st.markdown("""
<style>
    .log-card {
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .status-success {
        border-left: 4px solid #4CAF50;
    }
    .status-failure {
        border-left: 4px solid #F44336;
    }
    .status-pending {
        border-left: 4px solid #FFC107;
    }
    .log-table {
        font-size: 0.9rem;
    }
    .filter-container {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def fetch_resend_attempts():
    """Fetch resend attempts with pagination support"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                v.id, 
                u.username, 
                u.email, 
                v.timestamp, 
                v.ip_address, 
                v.status, 
                v.reason,
                v.attempt_count
            FROM verification_resend_log v
            JOIN users u ON v.user_id = u.id
            ORDER BY v.timestamp DESC
            LIMIT 1000
        ''')
        rows = cursor.fetchall()
        columns = [
            "Log ID", "Username", "Email", "Timestamp", 
            "IP Address", "Status", "Reason", "Attempt Count"
        ]
        return pd.DataFrame(rows, columns=columns)

def apply_filters(df, username_filter, status_filter, date_range):
    """Apply filters to the dataframe"""
    if username_filter != "All":
        df = df[df["Username"] == username_filter]
    if status_filter != "All":
        df = df[df["Status"] == status_filter]
    if date_range:
        start_date, end_date = date_range
        df = df[
            (df["Timestamp"] >= pd.to_datetime(start_date)) & 
            (df["Timestamp"] <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
        ]
    return df

def format_status(status):
    """Format status with color coding"""
    status_colors = {
        "success": "🟢",
        "failed": "🔴",
        "pending": "🟡"
    }
    return f"{status_colors.get(status.lower(), '⚪')} {status.capitalize()}"

def resend_log_view():
    """Main log viewer interface"""
    st.set_page_config(page_title="🔍 Verification Resend Log", layout="wide")
    st.title("🔍 Verification Resend Log")
    st.caption("Audit trail for all verification email resend attempts")

    # Load data with spinner
    with st.spinner("Loading resend logs..."):
        df = fetch_resend_attempts()
    
    # Convert timestamp to datetime
    if not df.empty:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    # Filters section
    with st.expander("🔎 Filter Options", expanded=True):
        with st.container():
            col1, col2, col3 = st.columns(3)
            
            with col1:
                username_filter = st.selectbox(
                    "Username",
                    ["All"] + sorted(df["Username"].unique().tolist()),
                    help="Filter by specific user"
                )
            
            with col2:
                status_filter = st.selectbox(
                    "Status",
                    ["All"] + sorted(df["Status"].unique().tolist()),
                    help="Filter by resend status"
                )
            
            with col3:
                date_range = st.date_input(
                    "Date Range",
                    value=(datetime.now() - pd.Timedelta(days=7), datetime.now()),
                    help="Filter by date range"
                )

    # Apply filters
    filtered_df = apply_filters(df, username_filter, status_filter, date_range)

    # Display metrics
    if not filtered_df.empty:
        success_rate = (filtered_df["Status"] == "success").mean() * 100
        avg_attempts = filtered_df["Attempt Count"].mean()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Attempts", len(filtered_df))
        with col2:
            st.metric("✅ Success Rate", f"{success_rate:.1f}%")
        with col3:
            st.metric("🔄 Avg Attempts", f"{avg_attempts:.1f}")

    # Display logs
    if not filtered_df.empty:
        st.subheader("📜 Resend Attempt Logs")
        
        # Format status for display
        display_df = filtered_df.copy()
        display_df["Status"] = display_df["Status"].apply(format_status)
        
        # Convert timestamp to readable format
        display_df["Timestamp"] = display_df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Show detailed view toggle
        detailed_view = st.toggle("Show Detailed View", value=False)
        
        if detailed_view:
            # Card view for detailed inspection
            for _, row in filtered_df.iterrows():
                status_class = f"status-{row['Status'].lower()}"
                with st.container():
                    st.markdown(f"""
                    <div class="log-card {status_class}">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <strong>{row['Username']}</strong> ({row['Email']})<br>
                                <small>{row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</small>
                            </div>
                            <div>
                                {format_status(row['Status'])} • Attempt #{row['Attempt Count']}
                            </div>
                        </div>
                        <div style="margin-top: 0.5rem;">
                            <strong>IP:</strong> {row['IP Address']}<br>
                            <strong>Reason:</strong> {row['Reason'] or 'N/A'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            # Compact table view
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Log ID": None,
                    "Attempt Count": "Attempts"
                }
            )
        
        # Export options
        st.download_button(
            label="📥 Download Filtered Logs (CSV)",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name=f"verification_resend_log_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("No logs found matching your filters")

if __name__ == "__main__":
    resend_log_view()