# src/views/admin/admin_tenant_billing_report.py
import streamlit as st
from datetime import date, datetime
from utils.session import init_session_state, validate_session
from utils.report_utils import generate_tenant_billing_report_pdf, generate_superadmin_pdf_report
from utils.ui_helpers import display_loading_animation
from db.database import get_db_connection

# Apply the same custom CSS as admin_dashboard.py
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
    
    .report-card {
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        border-left: 4px solid var(--info);
    }
</style>
""", unsafe_allow_html=True)

def admin_tenant_billing_report():
    """Admin interface for generating billing reports"""
    init_session_state()
    if not validate_session():
        st.warning("🔒 Your session has expired. Please log in again.")
        st.stop()

    st.set_page_config(
        page_title="Billing Analytics", 
        layout="wide",
        page_icon="📊"
    )

    tenant_id = st.session_state.tenant_id
    is_superadmin = st.session_state.role == "superadmin"

    # Enhanced header matching admin_dashboard.py style
    title = "📊 Tenant Billing Analytics" if not is_superadmin else "📈 Multi-Tenant Billing Dashboard"
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #1F2937;">{title}</h1>
        <div style="margin-left: auto; display: flex; align-items: center;">
            <span style="margin-right: 1rem; color: #6B7280;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    today = date.today()
    default_start = today.replace(day=1)
    default_end = today

    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            # Date selection form
            with st.form("report_params"):
                st.markdown("""
                <div class="section-header">
                    <div class="icon">📅</div>
                    <h2>Report Parameters</h2>
                </div>
                """, unsafe_allow_html=True)
                
                start_date = st.date_input(
                    "Start Date*",
                    value=default_start,
                    max_value=today,
                    help="Select the start of the reporting period"
                )
                end_date = st.date_input(
                    "End Date*",
                    value=default_end,
                    max_value=today,
                    min_value=start_date,
                    help="Select the end of the reporting period"
                )

                # Superadmin-specific filters
                tenant_filter = None
                if is_superadmin:
                    tenant_options = get_tenant_options()
                    tenant_filter = st.multiselect(
                        "Filter Tenants",
                        options=tenant_options,
                        default=[],
                        help="Select specific tenants to include"
                    )

                submitted = st.form_submit_button(
                    "Generate Report",
                    type="primary",
                    use_container_width=True
                )

        with col2:
            # Help section
            with st.container(border=True):
                st.markdown("""
                <div class="section-header">
                    <div class="icon">ℹ️</div>
                    <h2>Report Guide</h2>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("""
                **This report provides:**
                - 📅 Billing summary for selected period
                - 💰 Revenue and payment analytics
                - 👥 User activity metrics
                - 📈 Comparative performance data
                """)
                if is_superadmin:
                    st.markdown("**Superadmin Features:**")
                    st.markdown("- 🔍 Cross-tenant comparisons")
                    st.markdown("- 🏆 Performance benchmarking")

    if submitted:
        with st.spinner("Compiling your report..."):
            try:
                # Convert date to datetime at midnight for full day coverage
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
                
                # Display loading animation while generating
                with display_loading_animation():
                    if is_superadmin:
                        pdf_bytes = generate_superadmin_pdf_report(
                            start_datetime,
                            end_datetime,
                            tenant_filter if tenant_filter else None
                        )
                        filename = f"MultiTenant_Report_{start_date}_to_{end_date}.pdf"
                    else:
                        pdf_bytes = generate_tenant_billing_report_pdf(
                            tenant_id,
                            start_datetime,
                            end_datetime
                        )
                        tenant_name = get_tenant_name(tenant_id) or f"Tenant_{tenant_id}"
                        filename = f"{tenant_name}_Report_{start_date}_to_{end_date}.pdf"

                if not pdf_bytes:
                    st.markdown("""
                    <div class="alert-card alert-danger">
                        <p><strong>⚠️ Report generation failed:</strong> Empty PDF generated</p>
                    </div>
                    """, unsafe_allow_html=True)
                    return

                st.markdown("""
                <div class="alert-card alert-success">
                    <p><strong>✅ Report generated successfully!</strong></p>
                </div>
                """, unsafe_allow_html=True)

                # Download + preview
                with st.container():
                    st.download_button(
                        label="⬇️ Download Full Report",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

                    with st.expander("🔍 Report Preview", expanded=True):
                        if is_superadmin:
                            display_superadmin_preview(start_date, end_date, tenant_filter)
                        else:
                            display_tenant_preview(tenant_id, start_date, end_date)

            except Exception as e:
                st.markdown(f"""
                <div class="alert-card alert-danger">
                    <p><strong>⚠️ Report generation failed:</strong> {str(e)}</p>
                </div>
                """, unsafe_allow_html=True)
                if is_superadmin:
                    st.exception(e)


def get_tenant_options():
    """Fetch tenant options for superadmin filter"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM tenants ORDER BY name")
        return [f"{row[1]} (ID: {row[0]})" for row in cursor.fetchall()]
    except Exception as e:
        st.markdown(f"""
        <div class="alert-card alert-danger">
            <p><strong>Failed to load tenant options:</strong> {e}</p>
        </div>
        """, unsafe_allow_html=True)
        return []
    finally:
        if conn:
            conn.close()


def get_tenant_name(tenant_id):
    """Fetch tenant name by ID"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM tenants WHERE id = %s", (tenant_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        st.markdown(f"""
        <div class="alert-card alert-danger">
            <p><strong>Failed to fetch tenant name:</strong> {e}</p>
        </div>
        """, unsafe_allow_html=True)
        return None
    finally:
        if conn:
            conn.close()

def display_tenant_preview(tenant_id, start_date, end_date):
    """Display key metrics preview for single tenant"""
    conn = None
    try:
        print(f"Loading tenant preview for ID: {tenant_id} from {start_date} to {end_date}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert to datetime for SQL query
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE invoice_date BETWEEN %s AND %s) AS invoice_count,
                COALESCE(SUM(total_invoiced) FILTER (WHERE invoice_date BETWEEN %s AND %s), 0) AS total_billed,
                COALESCE(SUM(total_invoiced) FILTER (WHERE invoice_date BETWEEN %s AND %s AND is_paid), 0) AS total_paid
            FROM invoices
            WHERE tenant_id = %s
        """, (start_dt, end_dt, start_dt, end_dt, start_dt, end_dt, tenant_id))
        row = cursor.fetchone()
        
        if not row:
            st.markdown("""
            <div class="alert-card alert-info">
                <p><strong>ℹ️ No invoice data available for the selected period.</strong></p>
            </div>
            """, unsafe_allow_html=True)
            return

        invoice_count = row[0] or 0
        total_billed = float(row[1] or 0.0)
        total_paid = float(row[2] or 0.0)
        paid_pct = (total_paid / total_billed * 100) if total_billed else 0.0

        # Display metrics in cards
        st.markdown("""
        <div class="section-header">
            <div class="icon">📊</div>
            <h2>Key Metrics</h2>
        </div>
        """, unsafe_allow_html=True)
        
        cols = st.columns(4)
        with cols[0]:
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Invoices</h3>
                <h2>{invoice_count:,}</h2>
            </div>
            """, unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Total Billed</h3>
                <h2>R{total_billed:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"""
            <div class="metric-card {'metric-positive' if paid_pct > 75 else 'metric-warning'}">
                <h3>Paid Amount</h3>
                <h2>R{total_paid:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f"""
            <div class="metric-card {'metric-positive' if paid_pct > 75 else 'metric-warning'}">
                <h3>Paid %</h3>
                <h2>{paid_pct:.1f}%</h2>
            </div>
            """, unsafe_allow_html=True)

        # Revenue trend chart
        cursor.execute("""
            SELECT invoice_date::date AS d, COALESCE(SUM(total_invoiced),0) AS day_total
            FROM invoices
            WHERE tenant_id = %s AND invoice_date BETWEEN %s AND %s
            GROUP BY d
            ORDER BY d
        """, (tenant_id, start_dt, end_dt))
        rows = cursor.fetchall()
        
        if rows:
            st.markdown("""
            <div class="section-header">
                <div class="icon">📈</div>
                <h2>Revenue Trend</h2>
            </div>
            """, unsafe_allow_html=True)
            
            dates = [r[0].strftime("%Y-%m-%d") for r in rows]
            totals = [float(r[1]) for r in rows]
            st.line_chart(data={"Date": dates, "Amount": totals}, x="Date", y="Amount")
        else:
            st.markdown("""
            <div class="alert-card alert-info">
                <p><strong>ℹ️ No daily revenue data available</strong></p>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.markdown(f"""
        <div class="alert-card alert-danger">
            <p><strong>Failed to load tenant preview:</strong> {e}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.get("role") == "superadmin":
            st.exception(e)
    finally:
        if conn:
            conn.close()


def display_superadmin_preview(start_date, end_date, tenant_filter=None):
    """Display aggregated preview for superadmin"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Convert to datetime for SQL query
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        base_query = """
            SELECT
                COUNT(*) AS invoice_count,
                COALESCE(SUM(total_invoiced), 0) AS total_billed,
                COALESCE(SUM(CASE WHEN is_paid THEN total_invoiced ELSE 0 END), 0) AS total_paid
            FROM invoices
            {where_clause}
        """
        where_clause = "WHERE invoice_date BETWEEN %s AND %s"
        params = [start_dt, end_dt]

        if tenant_filter:
            # Extract IDs from tenant filter strings
            ids = []
            for t in tenant_filter:
                if "ID:" in t:
                    try:
                        ids.append(int(t.split("ID:")[1].strip(" )")))
                    except Exception:
                        pass
            if ids:
                where_clause += " AND tenant_id = ANY(%s)"
                params.append(ids)

        query = base_query.format(where_clause=where_clause)
        cursor.execute(query, tuple(params))
        row = cursor.fetchone()
        
        if not row:
            st.markdown("""
            <div class="alert-card alert-info">
                <p><strong>ℹ️ No invoice data available for the selected period.</strong></p>
            </div>
            """, unsafe_allow_html=True)
            return

        invoice_count = row[0] or 0
        total_billed = float(row[1] or 0.0)
        total_paid = float(row[2] or 0.0)
        paid_pct = (total_paid / total_billed * 100) if total_billed else 0.0

        # Display metrics in cards
        st.markdown("""
        <div class="section-header">
            <div class="icon">📊</div>
            <h2>Aggregate Metrics</h2>
        </div>
        """, unsafe_allow_html=True)
        
        cols = st.columns(4)
        with cols[0]:
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Total Invoices</h3>
                <h2>{invoice_count:,}</h2>
            </div>
            """, unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f"""
            <div class="metric-card metric-neutral">
                <h3>Total Billed</h3>
                <h2>R{total_billed:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"""
            <div class="metric-card {'metric-positive' if paid_pct > 75 else 'metric-warning'}">
                <h3>Total Paid</h3>
                <h2>R{total_paid:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f"""
            <div class="metric-card {'metric-positive' if paid_pct > 75 else 'metric-warning'}">
                <h3>Paid %</h3>
                <h2>{paid_pct:.1f}%</h2>
            </div>
            """, unsafe_allow_html=True)

        # Top performers section
        st.markdown("""
        <div class="section-header">
            <div class="icon">🏆</div>
            <h2>Top Performers</h2>
        </div>
        """, unsafe_allow_html=True)
        
        top_query = """
            SELECT t.name, COALESCE(SUM(i.total_invoiced),0) as revenue
            FROM invoices i
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.invoice_date BETWEEN %s AND %s
            {tenant_filter}
            GROUP BY t.id, t.name
            ORDER BY revenue DESC
            LIMIT 5
        """
        
        tenant_filter_clause = ""
        top_params = [start_dt, end_dt]
        
        if tenant_filter:
            tenant_filter_clause = "AND t.id = ANY(%s)"
            top_params.append(ids)
        
        cursor.execute(top_query.format(tenant_filter=tenant_filter_clause), tuple(top_params))
        top = cursor.fetchall()
        
        if top:
            cols = st.columns(5)
            for idx, (name, rev) in enumerate(top):
                with cols[idx % 5]:
                    st.markdown(f"""
                    <div class="metric-card metric-positive">
                        <h3>{name}</h3>
                        <h2>R{float(rev):,.2f}</h2>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert-card alert-info">
                <p><strong>ℹ️ No tenant revenue data for the selected period.</strong></p>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.markdown(f"""
        <div class="alert-card alert-danger">
            <p><strong>Failed to load superadmin preview:</strong> {e}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.get("role") == "superadmin":
            st.exception(e)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    admin_tenant_billing_report()   