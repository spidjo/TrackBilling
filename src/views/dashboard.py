def get_tenant_name(tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM tenants WHERE id = ?", (tenant_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "Unknown Tenant"

def dashboard():
    st.subheader("📊 Dashboard")

    tenant_id = st.session_state.get("tenant_id")
    tenant_name = get_tenant_name(tenant_id)

    st.markdown(f"**Tenant:** `{tenant_name}`")
