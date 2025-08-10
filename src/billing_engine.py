# src/billing_engine.py
from datetime import datetime, timedelta
import os   
import psycopg2
import psycopg2.extras
from db.database import get_db_connection
from services.record_usage import get_user_email
from utils.pdf_utils import generate_invoice_pdf
from utils.email_service import send_invoce_email


def get_billing_period_range(billing_period):
    start_date = datetime.strptime(billing_period + "-01", "%Y-%m-%d")
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def get_invoice_summary(invoice_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)  # Use DictCursor
    
    cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
    invoice = cursor.fetchone()
    if not invoice:
        conn.close()
        return None, None

    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
    items = cursor.fetchall()
    conn.close()
    
    # Convert to regular dict if needed
    return dict(invoice), [dict(item) for item in items]

def get_tenant_info(cursor, tenant_id):
    cursor.execute("SELECT name, address, email, phone FROM tenants WHERE id = %s", (tenant_id,))
    row = cursor.fetchone()
    if row:
        return {
            "name": row[0],
            "address": row[1],
            "email": row[2],
            "phone": row[3],
        }
    return {}

def get_client_info(cursor, user_id):
    cursor.execute("""
        SELECT first_name || ' ' || last_name AS name, company_name AS address, email
        FROM users WHERE id = %s
    """, (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            "name": row[0],
            "address": row[1],
            "email": row[2]
        }
    return {}

def generate_invoices(tenant_id, billing_period):
    print(f"Generating invoices for tenant {tenant_id} for period {billing_period}")
    start_date, end_date = get_billing_period_range(billing_period)
    conn = get_db_connection()
    cursor = conn.cursor()

    generated_ids = []

    cursor.execute("""
        SELECT s.user_id, s.plan_id, p.name, p.monthly_fee, p.included_units, p.overage_rate
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.is_active AND p.tenant_id = %s
    """, (tenant_id,))
    subscriptions = cursor.fetchall()
    print(f"Found {len(subscriptions)} active subscriptions for tenant {tenant_id}")

    for sub in subscriptions:
        user_id, plan_id, plan_name, monthly_fee, included_units, overage_rate = sub

        # Get usage data
        cursor.execute("""
            SELECT SUM(usage_amount) FROM usage_records
            WHERE tenant_id = %s AND user_id = %s AND usage_date BETWEEN %s AND %s
        """, (tenant_id, user_id, start_date, end_date))
        usage = cursor.fetchone()[0] or 0

        # Calculate charges
        overage_units = max(0, usage - included_units)
        overage_cost = overage_units * overage_rate
        total_amount = monthly_fee + overage_cost

        # Insert invoice and get the ID using RETURNING
        cursor.execute("""
            INSERT INTO invoices (tenant_id, user_id, period_start, period_end, invoice_date, total_amount, is_paid)
            VALUES (%s, %s, %s, %s, CURRENT_DATE, %s, False)
            RETURNING id
        """, (tenant_id, user_id, start_date, end_date, total_amount))
        invoice_id = cursor.fetchone()[0]

        # Now insert invoice items with the valid invoice_id
        cursor.execute("""
            INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
            VALUES (%s, %s, %s, %s, %s)
        """, (invoice_id, f"Base Plan: {plan_name}", 1, monthly_fee, monthly_fee))

        if overage_units > 0:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (invoice_id, f"Overage: {overage_units} units", overage_units, overage_rate, overage_cost))

        conn.commit()
        generated_ids.append(invoice_id)
        
        invoice, items = get_invoice_summary(invoice_id)
        if invoice is None:
            print(f"❌ Could not fetch summary for invoice_id: {invoice_id}")
            continue

        user_email = get_user_email(user_id)
        tenant_info = get_tenant_info(cursor, tenant_id)
        client_info = get_client_info(cursor, user_id)
        logo_path = f"assets/logos/{tenant_id}.png" if os.path.exists(f"assets/logos/{tenant_id}.png") else None

        client_name = client_info.get('name')
        tenant_name = tenant_info.get('name')
        try:
            pdf_buffer = generate_invoice_pdf(invoice, items, tenant_info, client_info, logo_path)
            pdf_buffer.seek(0)

            subject = f"Your Invoice #{invoice['id']} from {tenant_info.get('name', 'MzansiTel')}"
            
            pdf_bytes = pdf_buffer.getvalue()
            
            send_invoce_email(to_email=user_email, subject=subject, client_name=client_name, invoice_id=invoice['id'],
                              invoice_date=datetime.utcnow().strftime("%Y-%m-%d"), invoice_amount=invoice['total_amount'], pdf_bytes=pdf_bytes, 
                              is_paid=False, tenant_name=tenant_name)
            

        except Exception as email_error:
            print(f"⚠️ Email not sent for user {user_id}: {str(email_error)}")

    conn.close()
    return generated_ids

def generate_invoice_for_user(user_id, tenant_id, billing_period):
    """
    Create a real invoice for a single user and commit to DB.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    start_date, end_date = get_billing_period_range(billing_period)

    # Ensure user has active subscription
    cursor.execute("""
        SELECT s.plan_id FROM subscriptions s
        WHERE s.user_id = %s AND s.is_active
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    plan_id = row[0]
    items, total_amount = estimate_invoice_for_user(user_id, tenant_id)

    try:
        # Insert invoice and get the ID using RETURNING
        cursor.execute("""
            INSERT INTO invoices (tenant_id, user_id, period_start, period_end, invoice_date, total_amount, is_paid)
            VALUES (%s, %s, %s, %s, CURRENT_DATE, %s, False)
            RETURNING id
        """, (tenant_id, user_id, start_date, end_date, total_amount))
        
        invoice_row = cursor.fetchone()
        if not invoice_row:
            raise ValueError("Invoice insertion failed - no ID returned")
            
        invoice_id = invoice_row[0]

        # Insert invoice items
        for item in items:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                invoice_id,
                item["description"],
                item["quantity"],
                item["unit_price"],
                item["total_price"]
            ))

        conn.commit()
        return invoice_id
        
    except Exception as e:
        conn.rollback()
        print(f"Error generating invoice: {str(e)}")
        return None
    finally:
        conn.close()


def estimate_invoice_for_user(user_id, tenant_id):
    """
    Estimate the current invoice for a user based on usage vs plan limits (preview only).
    Returns:
        - List of itemized line items
        - Total estimated cost
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get active subscription for user
    cursor.execute("""
        SELECT s.plan_id, p.name, p.monthly_fee
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.user_id = %s AND s.is_active
    """, (user_id,))
    sub = cursor.fetchone()

    if not sub:
        conn.close()
        return [], 0.0

    plan_id, plan_name, monthly_fee = sub

    # 1. Start with the monthly base fee
    items = [{
        "description": f"Base Plan: {plan_name}",
        "quantity": 1,
        "unit_price": monthly_fee,
        "total_price": monthly_fee,
        "date": datetime.now().strftime("%Y-%m-%d")
    }]
    total = monthly_fee

    # 2. Get plan metric limits and overage rates
    cursor.execute("""
        SELECT pml.metric_id, m.name, pml.metric_limit, pml.overage_rate
        FROM plan_metric_limits pml
        JOIN usage_metrics m ON m.id = pml.metric_id
        WHERE pml.plan_id = %s
    """, (plan_id,))
    limits = cursor.fetchall()

    if not limits:
        conn.close()
        return items, total  # Plan has no usage-based charges

    # 3. For each metric, get total usage for current month
    today = datetime.now()
    start_date = today.replace(day=1).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    for metric_id, metric_name, metric_limit, overage_rate in limits:
        cursor.execute("""
            SELECT SUM(usage_amount) FROM usage_records
            WHERE tenant_id = %s AND user_id = %s AND metric_id = %s AND usage_date BETWEEN %s AND %s
        """, (tenant_id, user_id, metric_id, start_date, end_date))
        usage = cursor.fetchone()[0] or 0

        overage = max(0, usage - metric_limit)
        overage_cost = overage * overage_rate if overage > 0 else 0.0

        # Add line if there's overage
        if overage > 0:
            items.append({
                "description": f"Overage - {metric_name} (Limit: {metric_limit})",
                "quantity": overage,
                "unit_price": overage_rate,
                "total_price": overage_cost,
                "date": today.strftime("%Y-%m-%d")
            })
            total += overage_cost
    conn.close()
    return items, total


def finalize_invoice_for_user(user_id, tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # Step 1: Get active subscription
        cursor.execute("""
            SELECT plan_id FROM subscriptions 
            WHERE user_id = %s AND is_active
        """, (user_id,))
        sub = cursor.fetchone()
        if not sub:
            return False, "No active subscription found."

        plan_id = sub[0]

        # Step 2: Estimate invoice
        items, estimated_total = estimate_invoice_for_user(user_id, tenant_id)
        if not items:
            return False, "No invoiceable items found."

        now = datetime.utcnow()
        invoice_date = now.strftime("%Y-%m-%d")
        period_start = now.replace(day=1).strftime("%Y-%m-%d")
        period_end = now.strftime("%Y-%m-%d")

        # Step 3: Insert invoice record
        cursor.execute("""
            INSERT INTO invoices (user_id, tenant_id, invoice_date, period_start, period_end, total_amount, is_paid)
            VALUES (%s, %s, %s, %s, %s, %s, False)
            RETURNING id
        """, (user_id, tenant_id, invoice_date, period_start, period_end, estimated_total))
        
        invoice_row = cursor.fetchone()
        if not invoice_row:
            raise ValueError("Invoice insertion failed - no ID returned")
            
        invoice_id = invoice_row[0]

        # Step 4: Insert invoice items
        for item in items:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                invoice_id,
                item["description"],
                item["quantity"],
                item["unit_price"],
                item["total_price"]
            ))

        conn.commit()
        return True, invoice_id
        
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def auto_generate_invoices():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    today = datetime.utcnow().date()
    current_month = today.strftime("%Y-%m")

    # Get all active subscriptions
    cursor.execute("""
        SELECT user_id, plan_id, tenant_id 
        FROM subscriptions 
        WHERE is_active
    """)
    subscriptions = cursor.fetchall()

    for sub in subscriptions:
        user_id, plan_id, tenant_id = sub
        
        # Skip if invoice already exists for this month
        cursor.execute("""
            SELECT 1 FROM invoices
            WHERE user_id = %s AND date_trunc('month', invoice_date) = date_trunc('month', %s::date)
        """, (user_id, today))
        if cursor.fetchone():
            continue

        # Estimate invoice
        items, estimated_total = estimate_invoice_for_user(user_id, tenant_id)
        if not items:
            continue

        # Insert invoice 
        cursor.execute("""
            INSERT INTO invoices (user_id, tenant_id, invoice_date, period_start, period_end, total_amount, is_paid)
            VALUES (%s, %s, %s, %s, %s, %s, False)
            RETURNING id
        """, (
            user_id, 
            tenant_id, 
            today, 
            today.replace(day=1), 
            today,
            estimated_total
        ))
        invoice_id = cursor.fetchone()[0]

        # Insert invoice items
        for item in items:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                invoice_id,
                item['description'],
                item['quantity'],
                item['unit_price'],
                item['total_price']
            ))

        print(f"Generated invoice {invoice_id} for user {user_id}")

    conn.commit()
    conn.close()