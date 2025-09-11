import psycopg2
import random
from datetime import datetime, timedelta
from faker import Faker
import bcrypt

# Initialize Faker for fake data generation
fake = Faker()

def get_db_connection():
    """Create a database connection with proper configuration."""
    return psycopg2.connect(
        dbname="billing_db",
        user="postgres",
        password="admin",
        host="localhost",
        options="-c client_encoding=utf8 -c bytea_output=escape"
    )

def generate_tenants():
    """Generate tenant data."""
    tenants = [
        {"name": "Alpha", "company_name": "Alpha Telecom", "email": "alpha@example.com", 
         "region": "Africa", "phone": "+27123456789", "industry": "Telecommunications", 
         "logo_url": "alpha.png", "is_active": True, 
         "stripe_account_id": "acct_123alpha", "billing_contact": "John Smith", "vat_number": "ZA123456789"},
        
        {"name": "Beta", "company_name": "Beta SaaS", "email": "beta@example.com", 
         "region": "Europe", "phone": "+44123456789", "industry": "Software", 
         "logo_url": "beta.png", "is_active": True, 
         "stripe_account_id": "acct_456beta", "billing_contact": "Sarah Johnson", "vat_number": "GB987654321"},
        
        {"name": "Gamma", "company_name": "Gamma Logistics", "email": "gamma@example.com", 
         "region": "North America", "phone": "+11234567890", "industry": "Logistics", 
         "logo_url": "gamma.png", "is_active": True, 
         "stripe_account_id": "acct_789gamma", "billing_contact": "Michael Brown", "vat_number": "US456123789"}
    ]
    print("Generated tenants data")
    return tenants

def generate_users(tenant_ids):
    """Generate user data for each tenant."""
    hashed_pw = bcrypt.hashpw("testpass".encode(), bcrypt.gensalt()).decode('utf-8')
    users = []
    
    for tenant_id in tenant_ids:
        # Admin user
        users.append({
            "tenant_id": tenant_id,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "company_name": f"Tenant {tenant_id} Company",
            "username": f"admin{tenant_id}",
            "password": hashed_pw,
            "email": f"admin{tenant_id}@example.com",
            "role": "admin",
            "is_active": 1,
            "is_verified": 1,
            "last_login": fake.date_time_this_year()
        })
        
        # 2-3 client users per tenant
        for _ in range(random.randint(2, 3)):
            users.append({
                "tenant_id": tenant_id,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "company_name": f"Tenant {tenant_id} Company",
                "username": fake.user_name(),
                "password": hashed_pw,
                "email": fake.email(),
                "role": "client",
                "is_active": 1,
                "is_verified": 1,
                "last_login": fake.date_time_this_year()
            })
    
    print(f"Generated {len(users)} users for {len(tenant_ids)} tenants")
    return users

def generate_plans(tenant_ids):
    """Generate plans for each tenant."""
    plans = []
    plan_templates = [
        {"name": "Basic", "monthly_fee": 50.00, "included_units": 1000, "overage_rate": 0.05},
        {"name": "Pro", "monthly_fee": 150.00, "included_units": 5000, "overage_rate": 0.03},
        {"name": "Enterprise", "monthly_fee": 500.00, "included_units": 20000, "overage_rate": 0.02}
    ]
    
    for tenant_id in tenant_ids:
        for template in plan_templates:
            plans.append({
                "tenant_id": tenant_id,
                "name": template["name"],
                "description": f"{template['name']} plan for tenant {tenant_id}",
                "monthly_fee": template["monthly_fee"],
                "included_units": template["included_units"],
                "overage_rate": template["overage_rate"],
                "is_active": True,
                "billing_cycle": "monthly"
            })
    
    print(f"Generated {len(plans)} plans")
    return plans

def generate_usage_metrics(tenant_ids):
    """Generate usage metrics for each tenant."""
    metrics = []
    metric_templates = [
        {"name": "API Calls", "metric_type": "count", "unit": "calls"},
        {"name": "SMS Messages", "metric_type": "count", "unit": "messages"},
        {"name": "Data Storage", "metric_type": "storage", "unit": "GB"}
    ]
    
    for tenant_id in tenant_ids:
        for template in metric_templates:
            metrics.append({
                "tenant_id": tenant_id,
                "name": template["name"],
                "metric_type": template["metric_type"],
                "metric_name": template["name"].lower().replace(" ", "_"),
                "unit": template["unit"],
                "description": f"{template['name']} metric for tenant {tenant_id}"
            })
    
    print(f"Generated {len(metrics)} usage metrics")
    return metrics

def generate_subscriptions(conn, users, plans):
    """Generate subscriptions for users."""
    subscriptions = []
    user_plans = {}
    
    # Get all plans from database with their IDs
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, tenant_id, name FROM plans")
        db_plans = cursor.fetchall()
    
    # Group users by tenant
    tenant_users = {}
    for user in users:
        if user["tenant_id"] not in tenant_users:
            tenant_users[user["tenant_id"]] = []
        tenant_users[user["tenant_id"]].append(user)
    
    # Assign plans to users
    for tenant_id, user_list in tenant_users.items():
        tenant_plans = [p for p in db_plans if p[1] == tenant_id]
        
        for user in user_list:
            # Admin users get higher-tier plans
            if user["role"] == "admin":
                plan = random.choice([p for p in tenant_plans if p[2] in ["Pro", "Enterprise"]])
            else:
                plan = random.choice(tenant_plans)
            
            subscriptions.append({
                "user_id": user["id"],
                "plan_id": plan[0],
                "tenant_id": tenant_id,
                "start_date": fake.date_between(start_date='-1y', end_date='today'),
                "end_date": None,
                "is_active": True
            })
            user_plans[user["id"]] = plan[0]
    
    print(f"Generated {len(subscriptions)} subscriptions")
    return subscriptions, user_plans

def generate_usage_records(conn, users, user_plans, months=1):
    """Generate usage records for multiple months."""
    usage_records = []
    
    # Get all metrics from database
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, tenant_id, metric_name FROM usage_metrics")
        metrics = cursor.fetchall()
    
    for month in range(months):
        usage_date = (datetime.now() - timedelta(days=30*(month+1))).replace(day=1).date()
        
        for user in users:
            tenant_id = user["tenant_id"]
            tenant_metrics = [m for m in metrics if m[1] == tenant_id]
            
            for metric in tenant_metrics:
                # Generate usage amount based on plan
                plan_id = user_plans.get(user["id"])
                base_usage = random.randint(50, 200)
                
                # Scale usage based on plan tier (we'll get this from DB)
                if plan_id:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT name FROM plans WHERE id = %s", (plan_id,))
                        plan_name = cursor.fetchone()[0]
                    
                    if plan_name == "Basic":
                        usage_amount = base_usage
                    elif plan_name == "Pro":
                        usage_amount = base_usage * 5
                    else:  # Enterprise
                        usage_amount = base_usage * 20
                
                usage_records.append({
                    "tenant_id": tenant_id,
                    "user_id": user["id"],
                    "metric_id": metric[0],
                    "usage_amount": usage_amount,
                    "metric_name": metric[2],
                    "usage_date": usage_date
                })
    
    print(f"Generated {len(usage_records)} usage records for {months} months")
    return usage_records

def generate_invoices(users, months=1):
    """Generate invoices for multiple months."""
    invoices = []
    
    for month in range(months):
        period_end = (datetime.now() - timedelta(days=30*month)).replace(day=1).date()
        period_start = (period_end - timedelta(days=30)).replace(day=1)
        invoice_date = period_end
        
        for user in users:
            # Generate random invoice amount
            subtotal = round(random.uniform(50, 1000), 2)
            tax_amount = round(subtotal * 0.1, 2)
            total_amount = subtotal + tax_amount
            
            # Random payment status
            is_paid = random.choice([True, False])
            
            invoices.append({
                "tenant_id": user["tenant_id"],
                "user_id": user["id"],
                "period_start": period_start,
                "period_end": period_end,
                "invoice_date": invoice_date,
                "total_amount": total_amount,
                "is_paid": is_paid,
                "due_date": invoice_date + timedelta(days=30),
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "payment_status": "paid" if is_paid else "unpaid",
                "amount": total_amount
            })
    
    print(f"Generated {len(invoices)} invoices for {months} months")
    return invoices

def generate_payments(invoices):
    """Generate payments for paid invoices."""
    payments = []
    
    for invoice in invoices:
        if invoice["is_paid"]:
            payments.append({
                "user_id": invoice["user_id"],
                "invoice_id": invoice["id"],
                "amount": invoice["total_amount"],
                "payment_date": fake.date_time_between(
                    start_date=invoice["invoice_date"], 
                    end_date=invoice["due_date"]
                ),
                "payment_method": random.choice(["credit_card", "bank_transfer", "paypal"]),
                "receipt_path": f"/receipts/invoice_{invoice['id']}.pdf",
                "is_verified": True
            })
    
    print(f"Generated {len(payments)} payments")
    return payments

def insert_data(conn, table_name, data):
    """Insert data into a table and return the inserted records with their IDs."""
    inserted_records = []
    with conn.cursor() as cursor:
        for record in data:
            columns = ', '.join(record.keys())
            placeholders = ', '.join(['%s'] * len(record))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING id"
            
            try:
                cursor.execute(query, list(record.values()))
                inserted_id = cursor.fetchone()[0]
                record['id'] = inserted_id
                inserted_records.append(record)
                conn.commit()
            except Exception as e:
                print(f"Error inserting into {table_name}: {e}")
                conn.rollback()
                raise
    
    print(f"Inserted {len(inserted_records)} records into {table_name}")
    return inserted_records

def main(months=3):
    """Main function to generate and insert test data."""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return
    
    try:
        # Generate and insert tenants
        tenants = generate_tenants()
        inserted_tenants = insert_data(conn, "tenants", tenants)
        tenant_ids = [t['id'] for t in inserted_tenants]
        
        # Generate and insert users
        users = generate_users(tenant_ids)
        inserted_users = insert_data(conn, "users", users)
        
        # Generate and insert plans
        plans = generate_plans(tenant_ids)
        inserted_plans = insert_data(conn, "plans", plans)
        
        # Generate and insert usage metrics
        metrics = generate_usage_metrics(tenant_ids)
        inserted_metrics = insert_data(conn, "usage_metrics", metrics)
        
        # Generate and insert subscriptions
        subscriptions, user_plans = generate_subscriptions(conn, inserted_users, inserted_plans)
        inserted_subscriptions = insert_data(conn, "subscriptions", subscriptions)
        
        # Generate and insert usage records for multiple months
        usage_records = generate_usage_records(conn, inserted_users, user_plans, months)
        insert_data(conn, "usage_records", usage_records)
        
        # Generate and insert invoices for multiple months
        invoices = generate_invoices(inserted_users, months)
        inserted_invoices = insert_data(conn, "invoices", invoices)
        
        # Generate and insert payments
        payments = generate_payments(inserted_invoices)
        insert_data(conn, "payments", payments)
        
        print("Test data generation completed successfully!")
        
    except Exception as e:
        print(f"Error during data generation: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Run with 3 months of historical data by default
    main(months=3)