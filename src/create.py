import sqlite3
import bcrypt
import datetime

from streamlit import user

# Connect to the database (creates it if it doesn't exist)
conn = sqlite3.connect("data/billing.db")
cursor = conn.cursor()
# Create a users table (example)

hashed_pw = bcrypt.hashpw("testpass".encode(), bcrypt.gensalt())
registration_date = datetime.date.today().isoformat()
    

# cursor.execute("""ALTER TABLE usage_metrics ADD COLUMN metric_subtype TEXT;""")

# # Insert a sample tenant (example)
# cursor.execute("INSERT OR IGNORE INTO tenants (id, name, industry) VALUES (?, ?, ?)", 
#               ("tenant_1", "Example Company", "SaaS"))

# Insert an admin superadmin (example)
cursor.execute("""INSERT INTO users (username, password, first_name, last_name, company_name, email, registration_date, is_verified, verification_token, role)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "superadmin", hashed_pw, "Admin", "User", "Admin Company", "admin2@example.com", registration_date, 1, None, "superadmin"
))

# # Insert a sample user (example)
# cursor.execute("""INSERT INTO users (username, password, first_name, last_name, company_name, email, registration_date, is_verified, verification_token, role, tenant_id)
# VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
# """, (
#     "user1", hashed_pw, "Regular", "User", "User Company", "user1@example.com", registration_date, 1, None, "client", "tenant_1"
# ))

# # Insert a sample plan (example)
# cursor.execute("""INSERT INTO plans (id, name, description, monthly_fee, included_units, overage_rate, tenant_id)
# VALUES (?, ?, ?, ?, ?, ?, ?)
# """, (
#     "plan_1", "Basic Plan", "Basic subscription plan with limited features.", 10.00, 100, 0.10, "tenant_1"
# ))

# # Insert a sample subscription (example)
# cursor.execute("""INSERT INTO subscriptions (user_id, plan_id, tenant_id, start_date, end_date, is_active)
# VALUES (?, ?, ?, ?, ?, ?)
# """, (
#     "user1", "plan_1", "tenant_1", datetime.date.today().isoformat(), None, 1
# ))


conn.commit()
conn.close()
print("Table created successfully.")