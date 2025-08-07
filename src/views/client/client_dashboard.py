# src/views/client_dashboard.py

import streamlit as st
import pandas as pd
import altair as alt
from db.database import get_db_connection
from utils.session import init_session_state
from billing_engine import get_invoice_summary, generate_invoice_pdf
from io import StringIO, BytesIO
from datetime import datetime
from PyPDF2 import PdfReader
import base64

def get_tenant_info(tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, address, email, phone FROM tenants WHERE id = ?", (tenant_id,))
    row = cursor.fetchone()
    if row:
        return {
            "name": row[0],
            "address": row[1],
            "email": row[2],
            "phone": row[3],
        }
    conn.close()
    return {}

def get_client_info(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT first_name || ' ' || last_name AS name, company_name AS address, email
        FROM users WHERE id = ?
    """, (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            "name": row[0],
            "address": row[1],
            "email": row[2]
        }
    conn.close()
    return {}

def get_user_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (user_id,))
    user_row = cursor.fetchone()
    conn.close()
    return user_row[0] if user_row else None

def client_dashboard():
    init_session_state()

    if not st.session_state.get("authenticated"):
        st.warning("🔒 Please log in to view your dashboard.")
        st.stop()

    user_id = st.session_state.username
    tenant_id = st.session_state.tenant_id
    included_units = 0  # Fallback if no subscription exists

    st.title("📊 Client Dashboard")

    client_info = get_client_info(user_id=user_id)
    tenant_info = get_tenant_info(tenant_id=tenant_id)
    
    included_units = 0  # default fallback if no active plan found
    tabs = st.tabs(["📦 Plan Overview", "📊 Usage Analytics", "🧾 Latest Invoice", "📜 Invoice History", "🔔 Notifications"])

    # --- Plan Overview ---
    with tabs[0]:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.name, p.description, p.monthly_fee, p.included_units, p.overage_rate, s.start_date
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.user_id = ? AND s.is_active = 1
            ORDER BY s.start_date DESC LIMIT 1
        """, (get_user_id(user_id),))
        plan = cursor.fetchone()
        conn.close()

        if not plan:
            st.warning("🚫 You are not subscribed to a plan.")
        else:
            plan_name, description, monthly_fee, included_units, overage_rate, start_date = plan

            with st.expander("📦 Plan Summary", expanded=True):
                st.markdown(f"**Plan Name:** `{plan_name}`")
                st.markdown(f"**Monthly Fee:** `${monthly_fee:.2f}`")
                st.markdown(f"**Included Units:** {included_units}")
                st.markdown(f"**Overage Rate:** `${overage_rate:.2f}` per unit")
                st.markdown(f"**Start Date:** {start_date}")

    # --- Usage Analytics ---
    with tabs[1]:
        conn = get_db_connection()
        cursor = conn.cursor()

        st.subheader("🔍 Filter Usage")
        metric_filter = st.text_input("Filter by Metric Type (optional):")
        date_range = st.date_input("Date Range", [])

        query = """
            SELECT usage_date, metric_name, usage_amount
            FROM usage_records
            WHERE user_id = ? AND tenant_id = ?
        """
        params = [get_user_id(user_id), tenant_id]

        if metric_filter:
            query += " AND metric_type LIKE ?"
            params.append(f"%{metric_filter}%")

        if len(date_range) == 2:
            query += " AND usage_date BETWEEN ? AND ?"
            params.extend([date_range[0].isoformat(), date_range[1].isoformat()])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            st.info("No usage data found for selected filters.")
        else:
            df = pd.DataFrame(rows, columns=["Date", "Metric", "Quantity"])
            df["Date"] = pd.to_datetime(df["Date"])
            df["Month"] = df["Date"].dt.to_period("M").astype(str)

            st.subheader("📈 Usage Heatmap")
            heatmap_data = df.groupby([df["Date"].dt.date, "Metric"])["Quantity"].sum().reset_index()
            heatmap_data.columns = ["Date", "Metric", "Total Usage"]

            chart = alt.Chart(heatmap_data).mark_rect().encode(
                x=alt.X('Date:T', title="Date"),
                y=alt.Y('Metric:N', title="Metric"),
                color=alt.Color('Total Usage:Q', scale=alt.Scale(scheme='blues')),
                tooltip=['Date', 'Metric', 'Total Usage']
            ).properties(width=700, height=300)

            st.altair_chart(chart, use_container_width=True)

            st.subheader("📅 Monthly Usage per Metric")
            monthly_usage = df.groupby(["Month", "Metric"])["Quantity"].sum().reset_index()
            line_chart = alt.Chart(monthly_usage).mark_line(point=True).encode(
                x="Month:T",
                y="Quantity:Q",
                color="Metric:N",
                tooltip=["Month", "Metric", "Quantity"]
            ).properties(width=700, height=300)

            st.altair_chart(line_chart, use_container_width=True)

            st.subheader("📊 Overage Units per Month")
            monthly_total = df.groupby("Month")["Quantity"].sum().reset_index()
            monthly_total["Overage"] = monthly_total["Quantity"].apply(lambda x: max(0, x - included_units))

            overage_chart = alt.Chart(monthly_total).mark_bar().encode(
                x="Month:T",
                y="Overage:Q",
                tooltip=["Month", "Overage"]
            ).properties(width=700, height=300)

            st.altair_chart(overage_chart, use_container_width=True)

            st.subheader("⬇️ Export Usage Data")
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download CSV",
                data=csv_buffer.getvalue(),
                file_name=f"{user_id}_usage_export.csv",
                mime="text/csv"
            )

    # --- Latest Invoice ---
    with tabs[2]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM invoices
            WHERE user_id = ? ORDER BY invoice_date DESC LIMIT 1
        """, (get_user_id(user_id),))
        row = cursor.fetchone()
        conn.close()

        if row:
            invoice_id = row[0]
            invoice, items = get_invoice_summary(invoice_id)

            st.markdown(f"**Invoice ID:** `{invoice['id']}`")
            st.markdown(f"**Period:** `{invoice['period_start']}` to `{invoice['period_end']}`")
            st.markdown(f"**Amount Due:** R{invoice['total_amount']:.2f}")
            st.markdown(f"**Status:** {'✅ Paid' if invoice['is_paid'] else '❌ Unpaid'}")

            with st.expander("📋 Invoice Line Items", expanded=True):
                for item in items:
                    st.markdown(f"- {item['description']}: {item['quantity']} × R{item['unit_price']:.2f}")
        else:
            st.info("No invoices available.")

    # --- Invoice History ---
    with tabs[3]:
        st.subheader("📜 Historical Invoice History")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Filters
        with st.expander("🔍 Filter Options", expanded=True):
            date_range = st.date_input("Filter by Date Range", [])
            status_filter = st.selectbox("Filter by Status", ["All", "Paid", "Unpaid"])

        query = "SELECT id, invoice_date, period_start, period_end, total_amount, is_paid FROM invoices WHERE user_id = ?"
        params = [get_user_id(user_id)]

        if len(date_range) == 2:
            query += " AND invoice_date BETWEEN ? AND ?"
            params.extend([date_range[0].isoformat(), date_range[1].isoformat()])

        if status_filter == "Paid":
            query += " AND is_paid = 1"
        elif status_filter == "Unpaid":
            query += " AND is_paid = 0"

        query += " ORDER BY invoice_date DESC"

        cursor.execute(query, tuple(params))
        invoices = cursor.fetchall()
        conn.close()

        if not invoices:
            st.info("No invoices match the selected filters.")
        else:
            df_inv = pd.DataFrame(invoices, columns=["ID", "Date", "Start", "End", "Amount", "Paid"])
            df_inv["Status"] = df_inv["Paid"].map({1: "✅ Paid", 0: "❌ Unpaid"})
            df_inv_display = df_inv[["ID", "Date", "Start", "End", "Amount", "Status"]]
            st.dataframe(df_inv_display, use_container_width=True)

            # Download all as CSV
            st.download_button(
                label="⬇️ Download All Invoices as CSV",
                data=df_inv_display.to_csv(index=False),
                file_name=f"{user_id}_invoice_history.csv",
                mime="text/csv"
            )

            # View PDF inline
            selected_id = st.selectbox("Select Invoice ID to Preview PDF", df_inv["ID"])
            if selected_id:
                invoice, items = get_invoice_summary(selected_id)
                pdf_bytes = generate_invoice_pdf(invoice, items, tenant_info=tenant_info, client_info=client_info, logo_path="src/assets/logo.png")

                b64 = base64.b64encode(pdf_bytes.getvalue()).decode('utf-8')
                pdf_display = f"""
                    <iframe src="data:application/pdf;base64,{b64}" width="100%" height="600px" type="application/pdf"></iframe>
                """
                st.markdown(pdf_display, unsafe_allow_html=True)

                st.download_button(
                    label="📄 Download Selected PDF",
                    data=pdf_bytes.getvalue(),
                    file_name=f"invoice_{selected_id}.pdf",
                    mime="application/pdf"
                )

    # --- Notifications ---
    with tabs[4]:  
        st.subheader("🔔 Notifications")

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Overdue Invoices
        st.markdown("### ❌ Overdue Invoices")
        cursor.execute("""
            SELECT id, invoice_date, due_date, total_amount
            FROM invoices
            WHERE user_id = ? AND is_paid = 0 AND due_date < DATE('now')
            ORDER BY due_date ASC
        """, (user_id,))
        overdue = cursor.fetchall()

        if overdue:
            for inv in overdue:
                inv_id, inv_date, due_date, total = inv
                st.warning(f"Invoice #{inv_id} is overdue since {due_date} — Amount: R{total:.2f}")
        else:
            st.success("✅ No overdue invoices.")

        # 2. Usage Threshold Alert
        st.markdown("### 📊 Usage Threshold")

        # Get current month start and end
        today = datetime.now()
        first_day = today.replace(day=1).date().isoformat()
        last_day = today.date().isoformat()

        cursor.execute("""
            SELECT COALESCE(SUM(usage_amount), 0)
            FROM usage_records
            WHERE user_id = ? AND tenant_id = ? AND usage_date BETWEEN ? AND ?
        """, (get_user_id(user_id), tenant_id, first_day, last_day))
        monthly_usage = cursor.fetchone()[0] or 0

        if included_units > 0:
            usage_pct = (monthly_usage / included_units) * 100
        else:
            usage_pct = 0
        
        if usage_pct >= 100:
            st.error(f"⚠️ You have **exceeded** your usage limit! ({monthly_usage} units used / {included_units} included)")
        elif usage_pct >= 80:
            st.warning(f"⏳ You have used **{usage_pct:.1f}%** of your monthly units. Consider upgrading.")
        else:
            st.info(f"📉 Usage is within limits: {monthly_usage} units used.")

        conn.close()
