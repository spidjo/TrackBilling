import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from db.database import get_db_connection
from utils.ui_helpers import loading_spinner, show_toast

def admin_dashboard():
    """Admin dashboard with comprehensive tenant overview and management"""
    # Page configuration
    st.set_page_config(
        page_title="Admin Dashboard",
        layout="wide",
        page_icon="📊"
    )
    
    if 'tenant_id' not in st.session_state:
        st.error("Access denied. Please log in as admin.")
        st.stop()

    tenant_id = st.session_state.tenant_id

    # Initialize session state for filters
    if 'filter_user' not in st.session_state:
        st.session_state.filter_user = "All"
    if 'filter_date_range' not in st.session_state:
        st.session_state.filter_date_range = [
            datetime.now() - timedelta(days=30),
            datetime.now()
        ]

    # Main dashboard layout
    st.title(f"📊 Admin Dashboard – Tenant Overview")
    st.markdown("---")

    # Database connection with loading spinner
    with loading_spinner("Loading dashboard data..."):
        conn = get_db_connection()
        cursor = conn.cursor()

        # --- Common Data Fetching ---
        # Get all users for filters
        cursor.execute("""
            SELECT id, username FROM users 
            WHERE tenant_id = %s AND is_active = 1
            ORDER BY username
        """, (tenant_id,))
        all_users = cursor.fetchall()
        user_options = ["All"] + [f"{user[1]} (ID: {user[0]})" for user in all_users]

        # Get current plan limits
        cursor.execute("""
            SELECT p.included_units FROM plans p
            JOIN subscriptions s ON p.id = s.plan_id
            WHERE s.tenant_id = %s AND s.is_active = TRUE
            LIMIT 1
        """, (tenant_id,))
        plan = cursor.fetchone()
        included_units = plan[0] if plan else 0

        # --- Tabs Layout ---
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Usage Analytics", 
            "🧾 Billing & Invoices", 
            "👥 User Management", 
            "🚨 Alerts & Notifications"
        ])

        with tab1:
            # Usage Analytics Tab
            st.subheader("Usage Analytics", divider="blue")
            
            # Filters sidebar
            with st.sidebar:
                st.subheader("🔍 Filters")
                st.session_state.filter_user = st.selectbox(
                    "Filter by User",
                    user_options,
                    index=user_options.index(st.session_state.filter_user)
                )
                st.session_state.filter_date_range = st.date_input(
                    "Date Range",
                    value=st.session_state.filter_date_range,
                    max_value=datetime.now()
                )
                
                metric_filter = st.text_input("Filter by Metric Name")

            # Apply filters to data
            user_filter = st.session_state.filter_user.split("(ID: ")[1][:-1] if st.session_state.filter_user != "All" else None
            date_filter = st.session_state.filter_date_range if len(st.session_state.filter_date_range) == 2 else None

            # Get usage data
            query = """
                SELECT 
                    ur.usage_date,
                    u.username,
                    ur.metric_name,
                    ur.usage_amount
                FROM usage_records ur
                JOIN users u ON ur.user_id = u.id
                WHERE ur.tenant_id = %s
            """
            params = [tenant_id]

            if user_filter:
                query += " AND ur.user_id = %s"
                params.append(user_filter)
            if metric_filter:
                query += " AND ur.metric_name ILIKE %s"
                params.append(f"%{metric_filter}%")
            if date_filter:
                query += " AND ur.usage_date BETWEEN %s AND %s"
                params.extend(date_filter)

            query += " ORDER BY ur.usage_date DESC"
            cursor.execute(query, tuple(params))
            usage_data = cursor.fetchall()

            if not usage_data:
                st.info("No usage data found for selected filters")
            else:
                # Create DataFrame
                df = pd.DataFrame(usage_data, columns=["Date", "User", "Metric", "Quantity"])
                df["Date"] = pd.to_datetime(df["Date"])
                df["Month"] = df["Date"].dt.to_period("M").astype(str)

                # Summary Metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Usage", f"{df['Quantity'].sum():,} units")
                with col2:
                    overage = max(0, df["Quantity"].sum() - included_units)
                    st.metric("Estimated Overage", f"{overage:,} units", 
                            delta_color="inverse" if overage > 0 else "normal")
                with col3:
                    st.metric("Unique Metrics", df["Metric"].nunique())

                # Visualizations
                st.subheader("Usage Trends", divider="gray")
                
                # Time series chart
                trend_data = df.groupby(["Date", "Metric"])["Quantity"].sum().reset_index()
                trend_chart = alt.Chart(trend_data).mark_area(opacity=0.7).encode(
                    x="Date:T",
                    y="Quantity:Q",
                    color="Metric:N",
                    tooltip=["Date", "Metric", "Quantity"]
                ).properties(height=400)
                st.altair_chart(trend_chart, use_container_width=True)

                # Top users chart
                st.subheader("Usage by User", divider="gray")
                user_data = df.groupby("User")["Quantity"].sum().reset_index().sort_values("Quantity", ascending=False)
                user_chart = alt.Chart(user_data).mark_bar().encode(
                    x="User:N",
                    y="Quantity:Q",
                    color=alt.Color("User:N", legend=None),
                    tooltip=["User", "Quantity"]
                ).properties(height=300)
                st.altair_chart(user_chart, use_container_width=True)

                # Export options
                with st.expander("📤 Export Data"):
                    st.download_button(
                        "Download Usage Data (CSV)",
                        df.to_csv(index=False),
                        file_name=f"usage_data_{tenant_id}.csv",
                        mime="text/csv"
                    )

        with tab2:
            # Billing & Invoices Tab
            st.subheader("Billing Overview", divider="blue")
            
            # Invoice status summary
            cursor.execute("""
                SELECT 
                    i.id,
                    u.username,
                    i.invoice_date,
                    i.total_amount,
                    i.is_paid,
                    COALESCE(SUM(p.amount), 0) as paid_amount
                FROM invoices i
                JOIN users u ON i.user_id = u.id
                LEFT JOIN payments p ON i.id = p.invoice_id
                WHERE i.tenant_id = %s
                GROUP BY i.id, u.username
                ORDER BY i.invoice_date DESC
                LIMIT 50
            """, (tenant_id,))
            invoices = cursor.fetchall()

            if not invoices:
                st.info("No invoices found for this tenant")
            else:
                # Create DataFrame
                inv_df = pd.DataFrame(invoices, columns=[
                    "ID", "User", "Date", "Total", "Paid", "Paid Amount"
                ])
                inv_df["Date"] = pd.to_datetime(inv_df["Date"])
                inv_df["Status"] = inv_df.apply(
                    lambda x: "✅ Paid" if x["Paid"] else "⚠️ Partial" if x["Paid Amount"] > 0 else "❌ Unpaid",
                    axis=1
                )

                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Invoices", len(inv_df))
                with col2:
                    paid_invoices = inv_df[inv_df["Paid"]].shape[0]
                    st.metric("Paid Invoices", f"{paid_invoices} ({paid_invoices/len(inv_df):.0%})")
                with col3:
                    outstanding = inv_df[~inv_df["Paid"]]["Total"].sum()
                    st.metric("Outstanding Amount", f"R{outstanding:,.2f}")

                # Invoice table with filters
                st.subheader("Invoice Details", divider="gray")
                
                status_filter = st.multiselect(
                    "Filter by Status",
                    options=["✅ Paid", "⚠️ Partial", "❌ Unpaid"],
                    default=["✅ Paid", "⚠️ Partial", "❌ Unpaid"]
                )
                
                filtered_df = inv_df[inv_df["Status"].isin(status_filter)]
                st.dataframe(
                    filtered_df[["ID", "User", "Date", "Total", "Paid Amount", "Status"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ID": "Invoice #",
                        "Date": st.column_config.DateColumn(),
                        "Total": st.column_config.NumberColumn(format="R%.2f"),
                        "Paid Amount": st.column_config.NumberColumn(format="R%.2f")
                    }
                )

                # Visualizations
                st.subheader("Payment Trends", divider="gray")
                
                # Payment status pie chart
                status_counts = inv_df["Status"].value_counts().reset_index()
                pie_chart = alt.Chart(status_counts).mark_arc().encode(
                    theta="count:Q",
                    color="Status:N",
                    tooltip=["Status", "count"]
                ).properties(height=300)
                st.altair_chart(pie_chart, use_container_width=True)

        with tab3:
            # User Management Tab
            st.subheader("User Management", divider="blue")
            
            # User table
            cursor.execute("""
                SELECT 
                    id,
                    username,
                    email,
                    is_active,
                    last_login
                FROM users
                WHERE tenant_id = %s
                ORDER BY username
            """, (tenant_id,))
            users = cursor.fetchall()
            
            if not users:
                st.info("No users found for this tenant")
            else:
                user_df = pd.DataFrame(users, columns=[
                    "ID", "Username", "Email", "Active", "Last Login"
                ])
                user_df["Last Login"] = pd.to_datetime(user_df["Last Login"])
                
                st.dataframe(
                    user_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ID": "User ID",
                        "Active": st.column_config.CheckboxColumn(),
                        "Last Login": st.column_config.DatetimeColumn()
                    }
                )

                # User actions
                st.subheader("User Actions", divider="gray")
                
                with st.expander("🔄 Reset Password"):
                    selected_user = st.selectbox(
                        "Select User",
                        [f"{row[1]} (ID: {row[0]})" for row in users]
                    )
                    user_id = selected_user.split("(ID: ")[1][:-1]
                    
                    new_password = st.text_input("New Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    
                    if st.button("Reset Password", type="primary"):
                        if new_password != confirm_password:
                            st.error("Passwords do not match")
                        elif len(new_password) < 8:
                            st.error("Password must be at least 8 characters")
                        else:
                            cursor.execute(
                                "UPDATE users SET password = %s WHERE id = %s",
                                (new_password, user_id)
                            )
                            conn.commit()
                            show_toast("Password reset successfully", "success")

                with st.expander("📊 User Usage Report"):
                    selected_user = st.selectbox(
                        "Select User for Report",
                        [f"{row[1]} (ID: {row[0]})" for row in users]
                    )
                    user_id = selected_user.split("(ID: ")[1][:-1]
                    
                    cursor.execute("""
                        SELECT 
                            usage_date,
                            metric_name,
                            usage_amount
                        FROM usage_records
                        WHERE user_id = %s
                        ORDER BY usage_date DESC
                        LIMIT 100
                    """, (user_id,))
                    user_usage = cursor.fetchall()
                    
                    if user_usage:
                        usage_df = pd.DataFrame(user_usage, columns=["Date", "Metric", "Quantity"])
                        st.dataframe(usage_df, use_container_width=True)
                        
                        # Usage heatmap
                        heat_df = usage_df.copy()
                        heat_df["Date"] = pd.to_datetime(heat_df["Date"])
                        heat_df["Day"] = heat_df["Date"].dt.date
                        pivot = heat_df.pivot_table(
                            index="Day",
                            columns="Metric",
                            values="Quantity",
                            aggfunc="sum"
                        ).fillna(0)
                        
                        st.subheader("Daily Usage Heatmap")
                        st.dataframe(pivot.style.background_gradient(cmap="YlOrRd"), use_container_width=True)
                    else:
                        st.info("No usage data found for this user")

        with tab4:
            # Alerts & Notifications Tab
            st.subheader("Alerts Dashboard", divider="blue")
            
            # Overdue invoices
            with st.expander("❌ Overdue Invoices", expanded=True):
                cursor.execute("""
                    SELECT 
                        i.id,
                        u.username,
                        i.due_date,
                        i.total_amount,
                        i.invoice_date
                    FROM invoices i
                    JOIN users u ON i.user_id = u.id
                    WHERE i.is_paid = FALSE 
                    AND i.due_date < CURRENT_DATE
                    AND u.tenant_id = %s
                    ORDER BY i.due_date ASC
                """, (tenant_id,))
                overdue = cursor.fetchall()
                
                if overdue:
                    for inv_id, username, due_date, amount, inv_date in overdue:
                        days_overdue = (datetime.now().date() - due_date).days
                        with st.container(border=True):
                            st.markdown(f"""
                                **Invoice #{inv_id}**  
                                **Client:** {username}  
                                **Amount Due:** R{amount:,.2f}  
                                **Due Date:** {due_date} ({days_overdue} days overdue)  
                                **Issued:** {inv_date}
                            """)
                else:
                    st.success("✅ No overdue invoices")

            # High usage alerts
            with st.expander("🚨 High Usage Clients (>90%)", expanded=True):
                cursor.execute("""
                    SELECT 
                        u.username,
                        p.included_units,
                        COALESCE(SUM(ur.usage_amount), 0) as usage
                    FROM users u
                    JOIN subscriptions s ON u.id = s.user_id AND s.is_active
                    JOIN plans p ON s.plan_id = p.id
                    LEFT JOIN usage_records ur ON u.id = ur.user_id 
                        AND ur.usage_date BETWEEN date_trunc('month', CURRENT_DATE) AND CURRENT_DATE
                    WHERE u.tenant_id = %s
                    GROUP BY u.username, p.included_units
                    HAVING SUM(ur.usage_amount) >= 0.9 * p.included_units
                """, (tenant_id,))
                high_usage = cursor.fetchall()
                
                if high_usage:
                    for username, limit, usage in high_usage:
                        pct = (usage / limit) * 100
                        with st.container(border=True):
                            st.markdown(f"""
                                **Client:** {username}  
                                **Usage:** {usage:,.0f} of {limit:,.0f} units ({pct:.0f}%)  
                                **Overage:** {max(0, usage - limit):,.0f} units
                            """)
                else:
                    st.success("✅ No high usage clients")

            # Inactive users
            with st.expander("💤 Inactive Users (No Recent Usage)", expanded=True):
                cursor.execute("""
                    SELECT u.username, MAX(ur.usage_date) as last_usage
                    FROM users u
                    LEFT JOIN usage_records ur ON u.id = ur.user_id
                    WHERE u.tenant_id = %s
                    GROUP BY u.username
                    HAVING MAX(ur.usage_date) IS NULL OR MAX(ur.usage_date) < CURRENT_DATE - INTERVAL '30 days'
                """, (tenant_id,))
                inactive = cursor.fetchall()
                
                if inactive:
                    for username, last_usage in inactive:
                        with st.container(border=True):
                            if last_usage:
                                days_inactive = (datetime.now().date() - last_usage).days
                                st.markdown(f"""
                                    **Client:** {username}  
                                    **Last Activity:** {last_usage} ({days_inactive} days ago)
                                """)
                            else:
                                st.markdown(f"""
                                    **Client:** {username}  
                                    **Last Activity:** Never
                                """)
                else:
                    st.success("✅ All users have recent activity")

        conn.close()

# if __name__ == "__main__":
#     admin_dashboard()