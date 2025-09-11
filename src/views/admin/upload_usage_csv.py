import streamlit as st
import pandas as pd
from datetime import datetime
import math
from db.database import get_db_connection
from utils.email_utils import send_usage_alert_email
from utils.session import init_session_state, validate_session
from utils.ui_helpers import loading_spinner, show_toast

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
    
    .upload-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    }
    
    .validation-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: white;
        border-left: 4px solid var(--info);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    }
    
    .error-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: #FEE2E2;
        border-left: 4px solid var(--danger);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    }
    
    .success-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: #D1FAE5;
        border-left: 4px solid var(--secondary);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
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
</style>
""", unsafe_allow_html=True)

# Constants
MAX_FILE_SIZE_MB = 20  # 20MB max file size
CHUNK_SIZE = 1000  # Number of records per batch insert

def render_upload_usage_csv():
    """Professional admin interface for bulk uploading usage data"""
    # Page configuration
    init_session_state()
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()

    st.set_page_config(
        page_title="Upload Usage Data",
        layout="wide",
        page_icon="📤"
    )

    tenant_id = st.session_state.tenant_id
    if tenant_id is None:
        st.stop()

    # Dashboard header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">📤 Bulk Upload Usage Data</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Tenant ID: {tenant_id}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # Initialize session state for confirmation
    if 'confirmed' not in st.session_state:
        st.session_state.confirmed = False
    if 'processing_started' not in st.session_state:
        st.session_state.processing_started = False

    # Download template section
    with st.expander("📥 Download CSV Template", expanded=True):
        st.markdown("""
        <div class="section-header">
            <div class="icon">📝</div>
            <h2>CSV Template & Instructions</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        ### Required CSV Format
        - **`user_id`**: User ID from your system (must exist in your tenant)
        - **`metric_name`**: Name of the usage metric
        - **`usage_amount`**: Numeric value of usage
        - **`usage_date`**: Date in YYYY-MM-DD format
        
        ### File Requirements
        - Max file size: 20MB
        - CSV format with header row
        - UTF-8 encoding recommended
        """)
        
        template_data = {
            'user_id': [123, 456],
            'metric_name': ['api_calls', 'storage_mb'],
            'usage_amount': [100, 500],
            'usage_date': ['2023-01-01', '2023-01-01']
        }
        template_df = pd.DataFrame(template_data)
        
        st.download_button(
            label="Download Template CSV",
            data=template_df.to_csv(index=False),
            file_name="usage_upload_template.csv",
            mime="text/csv",
            use_container_width=True
        )

    # File upload section
    st.markdown("""
    <div class="section-header">
        <div class="icon">📤</div>
        <h2>Upload Usage Data</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        uploaded_file = st.file_uploader(
            "Upload your CSV file",
            type=["csv"],
            help="Upload a CSV file with usage data",
            key="file_uploader"
        )

    if uploaded_file is None:
        st.stop()

    # Check file size
    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"File size exceeds maximum limit of {MAX_FILE_SIZE_MB}MB")
        st.stop()

    # Process the uploaded file
    with loading_spinner("Validating your file..."):
        try:
            # Read CSV with error handling
            try:
                df = pd.read_csv(uploaded_file)
                if df.empty:
                    raise ValueError("Uploaded file is empty")
            except Exception as e:
                raise ValueError(f"Invalid CSV file: {str(e)}")

            # Validate required columns
            required_cols = {"user_id", "metric_name", "usage_amount", "usage_date"}
            missing_cols = required_cols - set(df.columns)
            if len(missing_cols) > 0:
                raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

            # Get database connection
            conn = get_db_connection()
            cursor = conn.cursor()

            # Pre-fetch all valid metrics for this tenant
            cursor.execute("""
                SELECT id, name FROM usage_metrics 
                WHERE tenant_id = %s
            """, (tenant_id,))
            metric_map = {name.lower(): mid for mid, name in cursor.fetchall()}

            # Pre-fetch all valid user IDs for this tenant
            cursor.execute("""
                SELECT id FROM users 
                WHERE tenant_id = %s AND is_active = 1
            """, (tenant_id,))
            valid_user_ids = {str(user_id[0]) for user_id in cursor.fetchall()}

            # Prepare data for batch insert
            valid_records = []
            validation_errors = []
            invalid_user_ids = set()

            for index, row in df.iterrows():
                row_num = index + 2  # Account for header row
                try:
                    # Validate user_id exists and belongs to tenant
                    user_id = str(row["user_id"]).strip()
                    if user_id not in valid_user_ids:
                        invalid_user_ids.add(user_id)
                        raise ValueError(f"User ID {user_id} not found in tenant or inactive")
                    
                    # Validate and transform other fields
                    metric_name = str(row["metric_name"]).strip()
                    try:
                        usage_amount = int(float(row["usage_amount"]))  # Handle float values
                    except (ValueError, TypeError):
                        raise ValueError("Usage amount must be a number")
                    
                    # Case-insensitive metric name matching
                    metric_id = metric_map.get(metric_name.lower())
                    if metric_id is None:
                        raise ValueError(f"Unknown metric: {metric_name}")
                    
                    # Parse date with multiple format support
                    try:
                        usage_date = datetime.strptime(str(row["usage_date"]), "%Y-%m-%d").date()
                    except ValueError:
                        raise ValueError("Invalid date format. Use YYYY-MM-DD")

                    # Add to batch
                    valid_records.append((
                        int(user_id), tenant_id, metric_id, 
                        metric_name, usage_amount, usage_date
                    ))

                except Exception as e:
                    validation_errors.append({
                        "row": row_num,
                        "error": str(e),
                        "user_id": str(row.get("user_id", "")),
                        "metric": str(row.get("metric_name", ""))
                    })

            # Show validation summary before processing
            with st.container():
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📋</div>
                    <h2>Validation Summary</h2>
                </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Total Rows", len(df))
                with cols[1]:
                    valid_percentage = (len(valid_records)/len(df)) if len(df) > 0 else 0
                    st.metric("Valid Rows", len(valid_records), 
                            delta=f"{valid_percentage:.1%} valid")
                with cols[2]:
                    st.metric("Invalid Rows", len(validation_errors),
                            delta_color="inverse")

            if len(invalid_user_ids) > 0:
                with st.expander("⚠️ Invalid User IDs Found", expanded=False):
                    st.warning(f"Found {len(invalid_user_ids)} invalid user IDs")
                    st.dataframe(
                        pd.DataFrame(sorted(invalid_user_ids), 
                        columns=["Invalid User IDs"])
                    )

            if len(validation_errors) > 0:
                with st.expander("🔍 View Validation Errors", expanded=False):
                    error_df = pd.DataFrame(validation_errors)
                    
                    # Group similar errors for better reporting
                    error_summary = error_df["error"].value_counts().reset_index()
                    error_summary.columns = ["Error Type", "Count"]
                    
                    st.markdown("#### Error Summary")
                    st.dataframe(
                        error_summary, 
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.markdown("#### Detailed Errors")
                    st.dataframe(
                        error_df[["row", "user_id", "metric", "error"]],
                        column_config={
                            "row": st.column_config.NumberColumn("Row #"),
                            "user_id": "User ID",
                            "metric": "Metric",
                            "error": st.column_config.TextColumn("Error", width="large")
                        },
                        use_container_width=True,
                        hide_index=True
                    )

            # Confirmation step
            if not st.session_state.processing_started:
                if len(valid_records) > 0:
                    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
                    
                    with st.container():
                        st.warning("⚠️ Please review the validation results before proceeding")
                        
                        confirm_cols = st.columns([1, 2, 1])
                        with confirm_cols[1]:
                            if st.button(
                                "✅ Confirm & Process Upload", 
                                type="primary", 
                                use_container_width=True,
                                disabled=len(valid_records) == 0,
                                key="confirm_upload"
                            ):
                                st.session_state.confirmed = True
                                st.session_state.processing_started = True
                                st.rerun()
                        
                        if st.button(
                            "❌ Cancel Upload", 
                            use_container_width=True,
                            disabled=len(valid_records) == 0,
                            key="cancel_upload"
                        ):
                            st.session_state.confirmed = False
                            st.session_state.processing_started = False
                            st.rerun()

            # Processing after confirmation
            if st.session_state.confirmed and st.session_state.processing_started:
                st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
                
                with st.container():
                    st.success("Processing your upload...")
                    
                    # Batch insert valid records in chunks
                    total_inserted = 0
                    num_chunks = math.ceil(len(valid_records) / CHUNK_SIZE)
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_placeholder = st.empty()
                    
                    for i in range(num_chunks):
                        chunk_start = i * CHUNK_SIZE
                        chunk_end = (i + 1) * CHUNK_SIZE
                        current_chunk = valid_records[chunk_start:chunk_end]
                        
                        status_text.text(f"Processing chunk {i+1} of {num_chunks} ({len(current_chunk)} records)...")
                        progress_bar.progress((i + 1) / num_chunks)
                        
                        try:
                            cursor.executemany("""
                                INSERT INTO usage_records (
                                    user_id, tenant_id, metric_id,
                                    metric_name, usage_amount, usage_date
                                )
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, current_chunk)
                            conn.commit()
                            total_inserted += len(current_chunk)
                            
                            # Update results display after each chunk
                            with results_placeholder.container():
                                st.markdown("### 🚀 Upload Progress")
                                progress_cols = st.columns(3)
                                progress_cols[0].metric("Total Processed", total_inserted)
                                remaining = len(valid_records) - total_inserted
                                progress_cols[1].metric("Remaining", remaining if remaining > 0 else 0)
                                completion = (total_inserted/len(valid_records))*100 if len(valid_records) > 0 else 0
                                progress_cols[2].metric("Completion", f"{completion:.1f}%")
                                
                        except Exception as e:
                            conn.rollback()
                            # Log which chunk failed
                            validation_errors.append({
                                "row": f"Chunk {i+1}",
                                "error": f"Database error: {str(e)}",
                                "user_id": "Multiple",
                                "metric": "Multiple"
                            })
                            status_text.error(f"Error processing chunk {i+1}: {str(e)}")
                            break
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Final results display
                    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
                    
                    with st.container():
                        st.markdown("""
                        <div class="section-header">
                            <div class="icon">📊</div>
                            <h2>Upload Results</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if total_inserted > 0:
                            show_toast(
                                f"✅ Successfully uploaded {total_inserted} records",
                                "success"
                            )
                            
                            cols = st.columns(3)
                            cols[0].metric("Total Processed", len(df))
                            success_rate = (total_inserted/len(df)) if len(df) > 0 else 0
                            cols[1].metric("Successfully Uploaded", total_inserted,
                                         delta=f"{success_rate:.1%} success rate")
                            cols[2].metric("Failed Rows", len(validation_errors),
                                          delta_color="inverse")
                            
                            affected_metric_ids = list({rec[2] for rec in valid_records})  # metric_id is rec[2]
                            check_and_trigger_usage_alerts(conn, tenant_id, affected_metric_ids)
                            
                            with st.expander("📋 View Sample of Inserted Data", expanded=False):
                                sample_size = min(5, len(valid_records))
                                sample_df = pd.DataFrame(
                                    valid_records[:sample_size],
                                    columns=["user_id", "tenant_id", "metric_id", 
                                            "metric_name", "usage_amount", "usage_date"]
                                )
                                st.dataframe(
                                    sample_df,
                                    use_container_width=True,
                                    hide_index=True
                                )
                        
                        # Reset confirmation state
                        st.session_state.confirmed = False
                        st.session_state.processing_started = False

        except Exception as e:
            show_toast(f"❌ Upload failed: {str(e)}", "error")
            st.error(f"Error: {str(e)}")
            
            # Reset confirmation state on error
            st.session_state.confirmed = False
            st.session_state.processing_started = False

        finally:
            if 'conn' in locals():
                conn.close()


def check_and_trigger_usage_alerts(conn, tenant_id, metric_ids):
    """
    Checks usage against plan limits for given metrics and sends alerts.
    Works with single metric_id or a list of metric_ids.
    Avoids duplicate alerts using alerts table.
    """
    cursor = conn.cursor()

    # Ensure metric_ids is always a list
    if isinstance(metric_ids, (int, str)):
        metric_ids = [metric_ids]
    elif isinstance(metric_ids, set):
        metric_ids = list(metric_ids)
    elif not metric_ids:
        return  # Nothing to check

    # Build placeholders for IN clause dynamically
    placeholders = ','.join(['%s'] * len(metric_ids))

    query = f"""
        SELECT ur.user_id, u.first_name || ' ' || u.last_name AS username, 
               ur.metric_id, SUM(ur.usage_amount) as total_usage,
               pm.metric_limit, u.email, um.name as metric_name
        FROM usage_records ur
        JOIN users u ON u.id = ur.user_id
        JOIN usage_metrics um ON um.id = ur.metric_id
        JOIN plan_metric_limits pm 
          ON pm.metric_id = ur.metric_id
         AND pm.plan_id = (
            SELECT s.plan_id
            FROM subscriptions s
            WHERE s.user_id = ur.user_id
            ORDER BY s.start_date DESC
            LIMIT 1
         )
        WHERE ur.tenant_id = %s
          AND ur.metric_id IN ({placeholders})
        GROUP BY ur.user_id, u.first_name, u.last_name, 
                 ur.metric_id, pm.metric_limit, u.email, um.name
    """

    params = [tenant_id] + metric_ids
    cursor.execute(query, params)

    for user_id, username, metric_id, total_usage, metric_limit, email, metric_name in cursor.fetchall():
        if metric_limit is not None and total_usage > metric_limit:
            # Check if we already sent this alert recently (last 24 hours)
            cursor.execute("""
                SELECT 1 FROM alerts
                WHERE tenant_id = %s AND user_id = %s 
                  AND metric_id = %s AND alert_type = 'USAGE_LIMIT'
                  AND created_at > NOW() - INTERVAL '24 HOURS'
            """, (tenant_id, user_id, metric_id))
            if cursor.fetchone():
                continue  # Skip duplicate alert

            # Send the alert email
            send_usage_alert_email(
                to_email=email,
                username=username,
                metric_name=metric_name,
                usage=total_usage,
                limit=metric_limit
            )

            # Log the alert
            cursor.execute("""
                INSERT INTO alerts (tenant_id, user_id, metric_id, alert_type, message, created_at)
                VALUES (%s, %s, %s, 'USAGE_LIMIT', %s, NOW())
            """, (
                tenant_id, user_id, metric_id,
                f"{metric_name} usage exceeded limit: {total_usage}/{metric_limit}"
            ))
            conn.commit()


if __name__ == "__main__":
    render_upload_usage_csv()