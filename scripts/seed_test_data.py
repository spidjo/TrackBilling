import sqlite3
import bcrypt
from datetime import datetime


DB_PATH = "data/billing.db"  # Update if needed

def import_sample_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    hashed_pw = bcrypt.hashpw("testpass".encode(), bcrypt.gensalt())
    # --- Tenants ---
    tenants = [
        ("1", "Tenant Alpha", "Telecom", "Africa", "2024-01-01"),
        ("2", "Tenant Beta", "SaaS", "Europe", "2024-02-15"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO tenants (id, name, industry, region, created_at) VALUES (?, ?, ?, ?, ?)", tenants)

    # --- Users ---
    users = [
        ("admin_alpha", hashed_pw, "Alice", "Alpha", "AlphaTel", "admin@alpha.com", "admin", "1", "2024-01-01", 1, "token123"),
        ("user_alpha1", hashed_pw, "Bob", "Alpha", "AlphaTel", "user1@alpha.com", "client", "1", "2024-01-02", 1, "token124"),
        ("user_alpha2", hashed_pw, "Cara", "Alpha", "AlphaTel", "user2@alpha.com", "client", "1", "2024-01-02", 1, "token125"),
        ("admin_beta", hashed_pw, "Dan", "Beta", "BetaSoft", "admin@beta.com", "admin", "2", "2024-02-15", 1, "token126"),
        ("user_beta1", hashed_pw, "Eve", "Beta", "BetaSoft", "user1@beta.com", "client", "2", "2024-02-16", 1, "token127"),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO users 
        (username, password, first_name, last_name, company_name, email, role, tenant_id, registration_date, is_verified, verification_token)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, users)

    # --- Plans ---
    plans = [
        ("1", "Starter Plan", "Basic plan", 500.00, 1000, 0.50),
        ("1", "Growth Plan", "Mid-tier plan", 1000.00, 5000, 0.30),
        ("2", "Beta Basic", "SaaS starter", 300.00, 1500, 0.40),
    ]
    cursor.executemany("""
        INSERT INTO plans (tenant_id, name, description, monthly_fee, included_units, overage_rate) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, plans)

    # Get user and plan IDs
    user_map = {row[0]: row[1] for row in cursor.execute("SELECT username, id FROM users").fetchall()}
    plan_map = {row[0]: row[1] for row in cursor.execute("SELECT name, id FROM plans").fetchall()}

    # --- Subscriptions ---
    subscriptions = [
        (user_map["user_alpha1"], "1", plan_map["Growth Plan"], "2024-06-01", None, 1),
        (user_map["user_alpha2"], "1", plan_map["Starter Plan"], "2024-06-01", None, 1),
        (user_map["user_beta1"], "2", plan_map["Beta Basic"], "2024-06-01", None, 1),
    ]
    cursor.executemany("""
        INSERT INTO subscriptions (user_id, tenant_id, plan_id, start_date, end_date, is_active) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, subscriptions)

    # --- Usage Metrics ---
    usage_metrics = [
        ("1", user_map["user_alpha1"], "call_minutes", 300, "2024-06-03"),
        ("1", user_map["user_alpha1"], "sms", 150, "2024-06-07"),
        ("1", user_map["user_alpha2"], "call_minutes", 1200, "2024-06-10"),
        ("1", user_map["user_alpha2"], "data_mb", 800, "2024-06-15"),
        ("2", user_map["user_beta1"], "api_calls", 600, "2024-06-05"),
        ("2", user_map["user_beta1"], "storage_gb", 5, "2024-06-10"),
    ]
    cursor.executemany("""
        INSERT INTO usage_metrics (tenant_id, user_id, metric_type, quantity, usage_date) 
        VALUES (?, ?, ?, ?, ?)
    """, usage_metrics)

    # --- Invoices ---
    invoices = [
        ("1", user_map["user_alpha1"], "2024-06-30", "2024-06-01", "2024-06-30", 575.00, 1),
        ("1", user_map["user_alpha2"], "2024-06-30", "2024-06-01", "2024-06-30", 1200.00, 0),
        ("2", user_map["user_beta1"], "2024-06-30", "2024-06-01", "2024-06-30", 650.00, 1),
    ]
    cursor.executemany("""
        INSERT INTO invoices (tenant_id, user_id, invoice_date, period_start, period_end, total_amount, is_paid)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, invoices)

    # --- Invoice Items ---
    invoice_ids = {row[0]: row[1] for row in cursor.execute("SELECT user_id, id FROM invoices").fetchall()}
    invoice_items = [
        (invoice_ids[user_map["user_alpha1"]], "Call Minutes", 300, 0.50, 150.00),
        (invoice_ids[user_map["user_alpha1"]], "SMS", 150, 0.20, 30.00),
        (invoice_ids[user_map["user_alpha1"]], "Base Plan", 1, 395.00, 395.00),

        (invoice_ids[user_map["user_alpha2"]], "Call Minutes", 1200, 0.50, 600.00),
        (invoice_ids[user_map["user_alpha2"]], "Data (MB)", 800, 0.40, 320.00),
        (invoice_ids[user_map["user_alpha2"]], "Base Plan", 1, 280.00, 280.00),

        (invoice_ids[user_map["user_beta1"]], "API Calls", 600, 0.40, 240.00),
        (invoice_ids[user_map["user_beta1"]], "Storage (GB)", 5, 20.00, 100.00),
        (invoice_ids[user_map["user_beta1"]], "Base Plan", 1, 310.00, 310.00),
    ]
    cursor.executemany("""
        INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
        VALUES (?, ?, ?, ?, ?)
    """, invoice_items)

    conn.commit()
    conn.close()
    print("✅ Sample data imported successfully.")

if __name__ == "__main__":
    import_sample_data()
