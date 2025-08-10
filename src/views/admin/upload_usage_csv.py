import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO
from db.database import get_db_connection
from utils.session_guard import require_login
from utils.ui_helpers import loading_spinner, show_toast

def render_upload_usage_csv():
    """Admin interface for bulk uploading usage data with enhanced UX"""
    # Page configuration
    require_login("admin")
    st.set_page_config(
        page_title="Upload Usage Data",
        layout="wide",
        page_icon="📤"
    )
    
    user = st.session_state.get("user")
    if not user:
        st.stop()
    
    tenant_id = user["tenant_id"]
    st.title("📤 Bulk Upload Usage Data")
    st.markdown("---")

    # Download template section
    with st.expander("📥 Download CSV Template", expanded=True):
        st.markdown("""
            **Required CSV Format:**
            - `user_id`: User ID from your system
            - `metric_name`: Name of the usage metric
            - `usage_amount`: Numeric value of usage
            - `usage_date`: Date in YYYY-MM-DD format
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
            mime="text/csv"
        )

    # File upload section
    uploaded_file = st.file_uploader(
        "Upload your CSV file",
        type=["csv"],
        help="Upload a CSV file with usage data"
    )

    if not uploaded_file:
        st.stop()

    # Process the uploaded file
    with loading_spinner("Processing your file..."):
        try:
            # Read CSV with error handling
            try:
                df = pd.read_csv(uploaded_file)
            except Exception as e:
                raise ValueError(f"Invalid CSV file: {str(e)}")

            # Validate required columns
            required_cols = {"user_id", "metric_name", "usage_amount", "usage_date"}
            missing_cols = required_cols - set(df.columns)
            if missing_cols:
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

            # Prepare data for batch insert
            valid_records = []
            validation_errors = []

            for index, row in df.iterrows():
                row_num = index + 2  # Account for header row
                try:
                    # Validate and transform data
                    user_id = int(row["user_id"])
                    metric_name = str(row["metric_name"]).strip()
                    usage_amount = int(row["usage_amount"])
                    
                    # Case-insensitive metric name matching
                    metric_id = metric_map.get(metric_name.lower())
                    if not metric_id:
                        raise ValueError(f"Unknown metric: {metric_name}")
                    
                    # Parse date with multiple format support
                    try:
                        usage_date = datetime.strptime(str(row["usage_date"]), "%Y-%m-%d").date()
                    except ValueError:
                        raise ValueError("Invalid date format. Use YYYY-MM-DD")

                    # Add to batch
                    valid_records.append((
                        user_id, tenant_id, metric_id, 
                        metric_name, usage_amount, usage_date
                    ))

                except Exception as e:
                    validation_errors.append({
                        "row": row_num,
                        "error": str(e),
                        "user_id": str(row.get("user_id", "")),
                        "metric": str(row.get("metric_name", ""))
                    })

            # Show validation results
            if validation_errors:
                st.warning(f"⚠️ Found {len(validation_errors)} invalid rows")
                
                # Display error details in expandable section
                with st.expander("View validation errors", expanded=False):
                    error_df = pd.DataFrame(validation_errors)
                    st.dataframe(
                        error_df[["row", "user_id", "metric", "error"]],
                        column_config={
                            "row": "Row #",
                            "user_id": "User ID",
                            "metric": "Metric",
                            "error": "Error"
                        },
                        use_container_width=True,
                        hide_index=True
                    )

            # Batch insert valid records
            if valid_records:
                with st.spinner(f"Uploading {len(valid_records)} valid records..."):
                    try:
                        cursor.executemany("""
                            INSERT INTO usage_records (
                                user_id, tenant_id, metric_id,
                                metric_name, usage_amount, usage_date
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, valid_records)
                        conn.commit()
                        
                        show_toast(
                            f"✅ Successfully uploaded {len(valid_records)} records",
                            "success"
                        )
                        
                        # Show summary stats
                        st.markdown("### 📊 Upload Summary")
                        col1, col2 = st.columns(2)
                        col1.metric("Total Rows Processed", len(df))
                        col2.metric("Successfully Uploaded", len(valid_records))
                        
                        if validation_errors:
                            st.metric("Failed Rows", len(validation_errors))

                    except Exception as e:
                        conn.rollback()
                        raise ValueError(f"Database error during upload: {str(e)}")

        except Exception as e:
            show_toast(f"❌ Upload failed: {str(e)}", "error")
            st.error(f"Error: {str(e)}")

        finally:
            if 'conn' in locals():
                conn.close()

if __name__ == "__main__":
    render_upload_usage_csv()