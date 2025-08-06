import streamlit as st
import pandas as pd
import altair as alt
from db.database import get_db_connection

def admin_dashboard():
    st.title("📊 Admin Dashboard – Tenant Overview")

    tenant_id = st.session_state.get("tenant_id")
    conn = get_db_connection()
    cursor = conn.cursor()



    # --- Tabs Layout ---
    usage_tab, invoices_tab, users_tab, alerts_tab = st.tabs([
        "📦 Usage Summary", "🧾 Invoices", "👥 Users", "🔔 Alerts"
    ])

    with usage_tab:
        # --- Filters ---
        st.sidebar.subheader("🔍 Filters")
        cursor.execute("SELECT DISTINCT user_id FROM usage_records WHERE tenant_id = ?", (tenant_id,))
        user_options = [r[0] for r in cursor.fetchall()]
        selected_user = st.sidebar.selectbox("Filter by User", ["All"] + user_options)
        date_range = st.sidebar.date_input("Date Range", [])
        metric_type = st.sidebar.text_input("Metric Type Filter")

        query = """
            SELECT usage_date, user_id, metric_name, usage_amount
            FROM usage_records
            WHERE tenant_id = ?
        """
        params = [tenant_id]
        if selected_user != "All":
            query += " AND user_id = ?"
            params.append(selected_user)
        if metric_type:
            query += " AND metric_name LIKE ?"
            params.append(f"%{metric_type}%")
        if len(date_range) == 2:
            query += " AND usage_date BETWEEN ? AND ?"
            params.extend([date_range[0].isoformat(), date_range[1].isoformat()])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=["Date", "User", "Metric", "Quantity"])
        df["Date"] = pd.to_datetime(df["Date"])
        df["Month"] = df["Date"].dt.to_period("M").astype(str)

        st.subheader("📦 Usage Summary")
        st.metric("📈 Total Usage", f"{df['Quantity'].sum()} units")

        cursor.execute("""
            SELECT included_units FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.tenant_id = ? AND s.is_active = 1
            LIMIT 1
        """, (tenant_id,))
        plan = cursor.fetchone()
        included_units = plan[0] if plan else 0
        overage = max(0, df["Quantity"].sum() - included_units)
        st.metric("🚨 Estimated Overage", f"{overage} units", delta_color="inverse")

        monthly_usage = df.groupby(["Month", "User"])["Quantity"].sum().reset_index()
        usage_chart = alt.Chart(monthly_usage).mark_line(point=True).encode(
            x="Month:T", y="Quantity:Q", color="User:N",
            tooltip=["Month", "User", "Quantity"]
        ).properties(width=700, height=350)
        st.altair_chart(usage_chart, use_container_width=True)

        st.subheader("⬇️ Export Usage")
        st.download_button("Download Filtered Usage CSV", df.to_csv(index=False), file_name="tenant_usage_export.csv", mime="text/csv")

        cursor.execute("""
            SELECT COUNT(*) FROM payments p
            JOIN users u ON p.user_id = u.id
            WHERE p.is_verified = 0 AND u.tenant_id = ?
        """, (tenant_id,))
        pending_count = cursor.fetchone()[0]

        if pending_count > 0:
            st.warning(f"🔔 You have {pending_count} payment(s) pending verification.")
    
        sidebar_title = "🛠️ Notifications"
        if pending_count > 0:
            sidebar_title += f" 🔴 ({pending_count})"

        st.sidebar.title(sidebar_title)

    with invoices_tab:
        st.subheader("🧾 Invoice Status Overview")
        cursor.execute("SELECT user_id, invoice_date, total_amount, is_paid FROM invoices WHERE tenant_id = ?", (tenant_id,))
        invoices = cursor.fetchall()

        if invoices:
            inv_df = pd.DataFrame(invoices, columns=["User", "Date", "Amount", "Paid"])
            inv_df["Date"] = pd.to_datetime(inv_df["Date"])
            inv_df["Month"] = inv_df["Date"].dt.to_period("M").astype(str)
            inv_df["Paid"] = inv_df["Paid"].apply(lambda x: "✅" if x else "❌")
            st.dataframe(inv_df.sort_values("Date", ascending=False), use_container_width=True)

            status_counts = inv_df["Paid"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            chart = alt.Chart(status_counts).mark_bar().encode(
                x="Status:N", y="Count:Q", color="Status:N"
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No invoices found for this tenant.")

    with users_tab:
        st.subheader("🧍 User Management")
        cursor.execute("SELECT id, username, email, is_active FROM users WHERE tenant_id = ?", (tenant_id,))
        user_rows = cursor.fetchall()
        user_df = pd.DataFrame(user_rows, columns=["User ID", "Username", "Email", "Active"])
        st.dataframe(user_df, use_container_width=True)

        st.markdown("### 🔐 Reset User Password")
        selected_user_id = st.selectbox("Select User", user_df["User ID"].tolist())
        new_password = st.text_input("New Password", type="password")
        if st.button("Reset Password"):
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, selected_user_id))
            conn.commit()
            st.success(f"Password reset for user ID {selected_user_id}")

        st.subheader("🔎 Detailed Usage by User")
        user_to_analyze = st.selectbox("Select User to Analyze", user_options)
        if user_to_analyze != "All":
            cursor.execute("""
                SELECT usage_date, metric_name, usage_amount
                FROM usage_records
                WHERE tenant_id = ? AND user_id = ?
                ORDER BY usage_date DESC
            """, (tenant_id, user_to_analyze))
            usage_rows = cursor.fetchall()
            if usage_rows:
                detail_df = pd.DataFrame(usage_rows, columns=["Date", "Metric", "Quantity"])
                detail_df["Date"] = pd.to_datetime(detail_df["Date"])
                st.dataframe(detail_df, use_container_width=True)

                heat_df = detail_df.copy()
                heat_df["Day"] = heat_df["Date"].dt.date
                pivot = heat_df.pivot_table(index="Day", columns="Metric", values="Quantity", aggfunc="sum").fillna(0)
                st.write("📆 Heatmap of Daily Metric Usage")
                st.dataframe(pivot)

                chart_data = detail_df.groupby(["Date", "Metric"])["Quantity"].sum().reset_index()
                usage_trend = alt.Chart(chart_data).mark_line(point=True).encode(
                    x="Date:T", y="Quantity:Q", color="Metric:N",
                    tooltip=["Date", "Metric", "Quantity"]
                ).properties(title=f"📈 Usage Trend for {user_to_analyze}", height=350)
                st.altair_chart(usage_trend, use_container_width=True)
            else:
                st.info("No usage found for this user.")

    with alerts_tab:
        st.subheader("🔔 Admin Notifications")

        # 1. Overdue Invoices
        st.markdown("### ❌ Overdue Invoices")
        cursor.execute("""
            SELECT u.username, i.id, i.due_date, i.total_amount
            FROM invoices i
            JOIN users u ON i.user_id = u.id
            WHERE i.is_paid = 0 AND i.due_date < DATE('now') AND u.tenant_id = ?
            ORDER BY i.due_date ASC
        """, (tenant_id,))
        overdue = cursor.fetchall()
        if overdue:
            for row in overdue:
                st.warning(f"Client **{row[0]}** has overdue invoice #{row[1]} (Due: {row[2]}, R{row[3]:.2f})")
        else:
            st.success("✅ No overdue invoices.")

        # 2. High Usage
        st.markdown("### 🚨 High Usage Clients (>90%)")
        cursor.execute("""
            SELECT u.username, p.included_units, COALESCE(SUM(um.usage_amount), 0)
            FROM users u
            JOIN subscriptions s ON u.id = s.user_id AND s.is_active = 1
            JOIN plans p ON s.plan_id = p.id
            LEFT JOIN usage_records um ON u.id = um.user_id AND um.usage_date BETWEEN DATE('now', 'start of month') AND DATE('now')
            WHERE u.tenant_id = ?
            GROUP BY u.username, p.included_units
            HAVING SUM(um.usage_amount) >= 0.9 * p.included_units
        """, (tenant_id,))
        alerts = cursor.fetchall()
        if alerts:
            for row in alerts:
                pct = (row[2] / row[1]) * 100 if row[1] else 0
                st.warning(f"Client **{row[0]}** has used {row[2]} of {row[1]} units (**{pct:.0f}%**) this month")
        else:
            st.success("✅ No high usage clients.")

        # 3. Inactive Users
        st.markdown("### 💤 Inactive Clients (No Usage This Month)")

        cursor.execute("""
            SELECT u.username FROM users u
            WHERE u.tenant_id = ? AND u.id NOT IN (
                SELECT DISTINCT user_id FROM usage_records
                WHERE usage_date BETWEEN DATE('now', 'start of month') AND DATE('now')
                AND tenant_id = ?
            )
        """, (tenant_id, tenant_id))
        inactive = cursor.fetchall()

        if inactive:
            for (username,) in inactive:
                st.info(f"Client **{username}** has no usage this month")
        else:
            st.success("✅ All users have recorded usage this month")


    conn.close()
