# auto_generate_invoices.py
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from db.database import get_db_connection

def auto_generate_invoices():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
 
        today = date.today()
        period_start = today.replace(day=1)
        period_end = today

        # Get all active subscriptions
        cursor.execute("""
            SELECT s.id, s.user_id, s.plan_id, s.tenant_id, p.monthly_fee
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.is_active
        """)
        subscriptions = cursor.fetchall()

        results = {
            "success": False,
            "count": 0,
            "errors": []
        }

        for sub_id, user_id, plan_id, tenant_id, monthly_fee in subscriptions:
            try:
                # Start transaction
                conn.autocommit = False

                # Fetch plan metric limits
                cursor.execute("""
                    SELECT pm.id, pm.metric_name, pml.included_units, pml.overage_rate
                    FROM plan_metric_limits pml
                    JOIN plan_metrics pm ON pml.metric_id = pm.id
                    WHERE pml.plan_id = %s
                """, (plan_id,))
                metric_limits = cursor.fetchall()

                total_amount = monthly_fee
                invoice_items = []

                # Add base monthly fee
                invoice_items.append({
                    "description": "Monthly Subscription Fee",
                    "quantity": 1,
                    "unit_price": monthly_fee,
                    "total_price": monthly_fee
                })

                # Calculate overages
                for metric_id, metric_name, included_units, overage_rate in metric_limits:
                    cursor.execute("""
                        SELECT COALESCE(SUM(usage_amount), 0)
                        FROM usage_records
                        WHERE user_id = %s AND metric_id = %s
                        AND usage_date BETWEEN %s AND %s
                    """, (user_id, metric_id, period_start, period_end))
                    usage = cursor.fetchone()[0]

                    if usage > included_units:
                        overage = usage - included_units
                        overage_total = overage * overage_rate
                        total_amount += overage_total

                        invoice_items.append({
                            "description": f"Overage: {metric_name}",
                            "quantity": overage,
                            "unit_price": overage_rate,
                            "total_price": overage_total
                        })

                # Create invoice
                cursor.execute("""
                    INSERT INTO invoices (tenant_id, user_id, period_start, period_end, total_amount)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (tenant_id, user_id, period_start, period_end, total_amount))
                
                invoice_row = cursor.fetchone()
                if not invoice_row:
                    raise Exception("Failed to create invoice record")
                
                invoice_id = invoice_row[0]

                # Create invoice items
                for item in invoice_items:
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

                # Commit transaction
                conn.commit()
                results["count"] += 1
                print(f"✅ Invoice generated for user_id {user_id} (Invoice #{invoice_id})")

            except Exception as e:
                conn.rollback()
                error_msg = f"Failed to generate invoice for user {user_id}: {str(e)}"
                results["errors"].append(error_msg)
                print(f"❌ {error_msg}")
                continue

        results["success"] = True if results["count"] > 0 else False
        return results

    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()