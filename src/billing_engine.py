import sqlite3
from datetime import datetime, timedelta
import os   
from db.database import get_db_connection
from services.record_usage import get_user_email
from utils.pdf_utils import generate_invoice_pdf
from utils.email_service import send_invoce_email


# def get_user_id(user_id):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT id FROM users WHERE username = ?", (user_id,))
#     user_row = cursor.fetchone()
#     conn.close()
#     return user_row[0] if user_row else None

def get_billing_period_range(billing_period):
    start_date = datetime.strptime(billing_period + "-01", "%Y-%m-%d")
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def get_invoice_summary(invoice_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    invoice = cursor.fetchone()
    if not invoice:
        conn.close()
        return None, None

    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    items = cursor.fetchall()
    conn.close()
    return dict(invoice), [dict(item) for item in items]

def get_tenant_info(cursor, tenant_id):
    cursor.execute("SELECT name, address, email, phone FROM tenants WHERE id = ?", (tenant_id,))
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
        FROM users WHERE id = ?
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
    start_date, end_date = get_billing_period_range(billing_period)
    conn = get_db_connection()
    cursor = conn.cursor()

    generated_ids = []

    cursor.execute("""
        SELECT s.user_id, s.plan_id, p.name, p.monthly_fee, p.included_units, p.overage_rate
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.is_active = 1 AND p.tenant_id = ?
    """, (tenant_id,))
    subscriptions = cursor.fetchall()

    for sub in subscriptions:
        user_id, plan_id, plan_name, monthly_fee, included_units, overage_rate = sub

        cursor.execute("""
            SELECT SUM(usage_amount) FROM usage_records
            WHERE tenant_id = ? AND user_id = ? AND usage_date BETWEEN ? AND ?
        """, (tenant_id, user_id, start_date, end_date))
        usage = cursor.fetchone()[0] or 0

        overage_units = max(0, usage - included_units)
        overage_cost = overage_units * overage_rate
        total_amount = monthly_fee + overage_cost

        cursor.execute("""
            INSERT INTO invoices (tenant_id, user_id, period_start, period_end, invoice_date, total_amount, is_paid)
            VALUES (?, ?, ?, ?, DATE('now'), ?, 0)
        """, (tenant_id, user_id, start_date, end_date, total_amount))
        invoice_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?)
        """, (invoice_id, f"Base Plan: {plan_name}", 1, monthly_fee, monthly_fee))

        if overage_units > 0:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?, ?)
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
                              is_paid=0, tenant_name=tenant_name)
            

        except Exception as email_error:
            print(f"⚠️ Email not sent for user {user_id}: {str(email_error)}")

    conn.close()
    return generated_ids

def generate_invoice_for_user(user_id, tenant_id, billing_period):
    """
    Create a real invoice for a single user and commit to DB.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    start_date, end_date = get_billing_period_range(billing_period)

    # Ensure user has active subscription
    cursor.execute("""
        SELECT s.plan_id FROM subscriptions s
        WHERE s.user_id = ? AND s.is_active = 1
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    plan_id = row[0]
    # Estimate again using same logic
    items, total_amount = estimate_invoice_for_user(user_id, tenant_id)

    cursor.execute("""
        INSERT INTO invoices (tenant_id, user_id, period_start, period_end, invoice_date, total_amount, is_paid)
        VALUES (?, ?, ?, ?, DATE('now'), ?, 0)
    """, (tenant_id, user_id, start_date, end_date, total_amount))
    invoice_id = cursor.lastrowid

    for item in items:
        cursor.execute("""
            INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?)
        """, (
            invoice_id,
            item["description"],
            item["quantity"],
            item["unit_price"],
            item["total_price"]
        ))

    conn.commit()
    conn.close()
    return invoice_id


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
        WHERE s.user_id = ? AND s.is_active = 1
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
        WHERE pml.plan_id = ?
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
            WHERE tenant_id = ? AND user_id = ? AND metric_id = ? AND usage_date BETWEEN ? AND ?
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
    cursor = conn.cursor()

    # Step 1: Get active subscription
    cursor.execute("""
        SELECT plan_id FROM subscriptions 
        WHERE user_id = ? AND is_active = 1
    """, (user_id,))
    sub = cursor.fetchone()
    if not sub:
        conn.close()
        return False, "No active subscription found."

    plan_id = sub[0]

    # Step 2: Estimate invoice again (safety)
    items, estimated_total = estimate_invoice_for_user(user_id, tenant_id)
    if not items:
        conn.close()
        return False, "No invoiceable items found."

    now = datetime.utcnow()
    invoice_date = now.strftime("%Y-%m-%d")
    period_start = now.replace(day=1).strftime("%Y-%m-%d")
    period_end = now.strftime("%Y-%m-%d")

    # Step 3: Insert invoice record
    cursor.execute("""
        INSERT INTO invoices (user_id, tenant_id, invoice_date, period_start, period_end, total_amount, is_paid)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (user_id, tenant_id, invoice_date, period_start, period_end, estimated_total))
    invoice_id = cursor.lastrowid

    # Step 4: Insert invoice items
    for item in items:
        cursor.execute("""
            INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?)
        """, (
            invoice_id,
            item["description"],
            item["quantity"],
            item["unit_price"],
            item["total_price"]
        ))

    conn.commit()
    conn.close()
    return True, invoice_id


def auto_generate_invoices():
    conn = get_db_connection()
    cursor = conn.cursor()

    today = datetime.utcnow().strftime("%Y-%m-%d")
    start_period = datetime.utcnow().replace(day=1).strftime("%Y-%m-%d")
    end_period = datetime.utcnow().strftime("%Y-%m-%d")

    # Get all active subscriptions
    cursor.execute("""
        SELECT user_id, plan_id, tenant_id 
        FROM subscriptions 
        WHERE is_active = 1
    """)
    subscriptions = cursor.fetchall()

    for user_id, plan_id, tenant_id in subscriptions:
        # Skip if invoice already exists for this user for the current period
        cursor.execute("""
            SELECT 1 FROM invoices
            WHERE user_id = ? AND strftime('%Y-%m', invoice_date) = strftime('%Y-%m', ?)
        """, (user_id, today))
        if cursor.fetchone():
            continue  # Already billed this period

        # Estimate invoice
        items, estimated_total = estimate_invoice_for_user(user_id, tenant_id)
        if not items:
            continue

        # Insert invoice
        cursor.execute("""
            INSERT INTO invoices (user_id, tenant_id, invoice_date, period_start, period_end, total_amount, is_paid)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (get_user_id(user_id), tenant_id, today, start_period, end_period, estimated_total))
        invoice_id = cursor.lastrowid

        # Insert invoice items
        for item in items:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?, ?)
            """, (
                invoice_id,
                item['description'],
                item['quantity'],
                item['unit_price'],
                item['total_price']
            ))

    conn.commit()
    conn.close()
