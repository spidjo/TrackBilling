import sqlite3
from datetime import datetime, timedelta
import os
from database import get_db_connection
from services.record_usage import get_user_email
from utils.pdf_utils import generate_invoice_pdf
from utils.email_utils import send_invoice_email

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
            SELECT SUM(quantity) FROM usage_metrics
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

        try:
            pdf_bytes = generate_invoice_pdf(invoice, items, tenant_info, client_info, logo_path)
            pdf_bytes.seek(0)

            subject = f"Your Invoice #{invoice['id']} from {tenant_info.get('name', 'MzansiTel')}"
            body = f"""
            Dear {client_info.get('name', 'Customer')},

            Attached is your invoice #{invoice['id']} dated {invoice['invoice_date']}.

            Amount Due: R{invoice['total_amount']:.2f}
            Status: {'Paid' if invoice['is_paid'] else 'Unpaid'}

            Please see the invoice for full details.

            Regards,
            {tenant_info.get('name', 'MzansiTel')} Billing Team
            """

            smtp_settings = {
                "host": os.getenv("SMTP_HOST") or "",
                "port": int(os.getenv("SMTP_PORT") or 0),
                "username": os.getenv("SMTP_USERNAME") or "",
                "password": os.getenv("SMTP_PASSWORD") or "",
                "sender": os.getenv("EMAIL_SENDER") or "",
            }

            if not all(smtp_settings.values()):
                raise ValueError("Incomplete SMTP configuration. Check environment variables.")

            send_invoice_email(
                'siphiwolu@gmail.com', subject, body,
                pdf_bytes, f"invoice_{invoice['id']}.pdf", smtp_settings
            )

        except Exception as email_error:
            print(f"⚠️ Email not sent for user {user_id}: {str(email_error)}")

    conn.close()
    return generated_ids
