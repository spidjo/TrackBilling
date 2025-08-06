# auto_invoice_generator.py
import sqlite3
from datetime import datetime, timedelta
from billing_engine import generate_invoices

def generate_monthly_invoices():
    conn = sqlite3.connect("data/app.db")
    cursor = conn.cursor()

    # Get all active subscriptions
    cursor.execute("""
        SELECT id, user_id, plan_id, tenant_id FROM subscriptions
        WHERE is_active = 1
    """)
    subscriptions = cursor.fetchall()

    for sub_id, user_id, plan_id, tenant_id in subscriptions:
        try:
            print(f"🔄 Generating invoice for User ID: {user_id}")
            generate_invoices(user_id, tenant_id)
        except Exception as e:
            print(f"❌ Error invoicing user {user_id}: {e}")

    conn.close()

if __name__ == "__main__":
    generate_monthly_invoices()
