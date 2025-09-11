import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal, getcontext, InvalidOperation
import os
import psycopg2
import psycopg2.extras
from scipy import io
from db.database import get_db_connection
from services.record_usage import get_user_email
from utils.pdf_utils import generate_invoice_pdf
from utils.pdf_generator import generate_pdf_invoice
from utils.email_service import send_invoice_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BillingEngine:
    def __init__(self):
        self.utc_now = datetime.utcnow()
        self.logger = logging.getLogger(__name__)

    def get_billing_period_range(self, billing_period: str) -> tuple[str, str]:
        """Calculate start and end dates for a billing period (YYYY-MM format)"""
        try:
            start_date = datetime.strptime(billing_period + "-01", "%Y-%m-%d")
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Invalid billing period format: {billing_period}. Error: {e}")
            raise ValueError("Billing period must be in YYYY-MM format")

    def get_invoice_summary(self, invoice_id: int) -> tuple[dict, list]:
        """Retrieve invoice and its items from database"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
                invoice = cursor.fetchone()
                if not invoice:
                    logger.warning(f"Invoice not found: {invoice_id}")
                    return None, None

                cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
                items = cursor.fetchall()
                return dict(invoice), [dict(item) for item in items]

    def _fetch_tenant_info(self, cursor, tenant_id: int) -> dict:
        """Fetch tenant information from database"""
        cursor.execute(
            "SELECT name, address, email, phone FROM tenants WHERE id = %s", 
            (tenant_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else {}

    def _fetch_client_info(self, cursor, user_id: int) -> dict:
        """Fetch client information from database"""
        cursor.execute("""
            SELECT first_name || ' ' || last_name AS name, 
                   company_name AS address, 
                   email
            FROM users WHERE id = %s
        """, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else {}

    def get_tenant_info(self, cursor, tenant_id: int) -> Dict[str, Any]:
        """Get tenant information with error handling"""
        try:
            cursor.execute("""
                SELECT name, address, email, phone, COALESCE(tax_id, '') AS tax_id
                FROM tenants WHERE id = %s
            """, (tenant_id,))
            row = cursor.fetchone()
            return {
                "name": row[0] if row else "MzansiTel",
                "address": row[1] if row else "",
                "email": row[2] if row else "billing@mzansitel.co.za",
                "phone": row[3] if row else "",
                "tax_id": row[4] if row else ""
            }
        except Exception as e:
            self.logger.error(f"Error fetching tenant info: {str(e)}")
            return {
                "name": "MzansiTel",
                "address": "",
                "email": "billing@mzansitel.co.za",
                "phone": "",
                "tax_id": ""
            }

    def get_client_info(self, cursor, user_id: int) -> Dict[str, Any]:
        """Get client information with error handling"""
        try:
            cursor.execute("""
                SELECT u.first_name || ' ' || u.last_name, 
                       u.company_name, 
                       u.email,
                       u.phone,
                       u.billing_address
                FROM users u
                WHERE u.id = %s
            """, (user_id,))
            row = cursor.fetchone()
            return {
                "name": row[0] if row else "",
                "company": row[1] if row else "",
                "email": row[2] if row else "",
                "phone": row[3] if row else "",
                "address": row[4] if row else ""
            }
        except Exception as e:
            self.logger.error(f"Error fetching client info: {str(e)}")
            return {
                "name": "",
                "company": "",
                "email": "",
                "phone": "",
                "address": ""
            }
            
    def _send_invoice_email(self, invoice_id: int, user_id: int, tenant_id: int) -> bool:
        """Generate and send invoice email"""
        try:
            invoice, items = self.get_invoice_summary(invoice_id)
            if not invoice:
                return False

            user_email = get_user_email(user_id)
            if not user_email:
                logger.error(f"No email found for user {user_id}")
                return False

            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    tenant_info = self._fetch_tenant_info(cursor, tenant_id)
                    client_info = self._fetch_client_info(cursor, user_id)

            logo_path = f"assets/{tenant_id}.png" if os.path.exists(
                f"assets/{tenant_id}.png"
            ) else None

            invoice_details = self.get_invoice_details(invoice_id)
            pdf_bytes = generate_pdf_invoice(invoice_details, tenant_id=tenant_id)
            # pdf_buffer = io.BytesIO(pdf_bytes)
            # pdf_buffer.seek(0)

            subject = f"Your Invoice #{invoice['id']} from {tenant_info.get('name', 'MzansiTel')}"
            
            send_invoice_email(
                to_email=user_email,
                subject=subject,
                client_name=client_info.get('name'),    
                invoice_id=invoice['id'],
                invoice_date=self.utc_now.strftime("%Y-%m-%d"),
                invoice_amount=invoice['total_invoiced'],
                pdf_bytes=pdf_bytes,
                is_paid=False,
                tenant_name=tenant_info.get('name')
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            return False

    # def generate_invoices1(self, tenant_id: int, billing_period: str) -> list[int]:
    #     """Generate invoices for all active subscriptions in a tenant for a billing period"""
    #     logger.info(f"Generating invoices for tenant {tenant_id} for period {billing_period}")
        
    #     try:
    #         start_date, end_date = self.get_billing_period_range(billing_period)
    #     except ValueError as e:
    #         logger.error(str(e))
    #         return []

    #     generated_ids = []
        
    #     with get_db_connection() as conn:
    #         with conn.cursor() as cursor:
    #             # Pre-fetch all active subscriptions with their plans
    #             cursor.execute("""
    #                 SELECT s.user_id, s.plan_id, p.name, p.monthly_fee, 
    #                        p.included_units, p.overage_rate
    #                 FROM subscriptions s
    #                 JOIN plans p ON s.plan_id = p.id
    #                 WHERE s.is_active AND p.tenant_id = %s
    #             """, (tenant_id,))
    #             subscriptions = cursor.fetchall()
                
    #             logger.info(f"Found {len(subscriptions)} active subscriptions for tenant {tenant_id}")

    #             for sub in subscriptions:
    #                 user_id, plan_id, plan_name, monthly_fee, included_units, overage_rate = sub

    #                 # Check if invoice already exists for this period
    #                 cursor.execute("""
    #                     SELECT id FROM invoices 
    #                     WHERE tenant_id = %s AND user_id = %s 
    #                     AND period_start = %s AND period_end = %s
    #                 """, (tenant_id, user_id, start_date, end_date))
    #                 if cursor.fetchone():
    #                     logger.info(f"Invoice already exists for user {user_id} period {billing_period}")
    #                     continue

    #                 # Get usage data
    #                 cursor.execute("""
    #                     SELECT SUM(usage_amount) FROM usage_records
    #                     WHERE tenant_id = %s AND user_id = %s 
    #                     AND usage_date BETWEEN %s AND %s
    #                 """, (tenant_id, user_id, start_date, end_date))
    #                 usage = cursor.fetchone()[0] or 0

    #                 # Calculate charges
    #                 overage_units = max(0, usage - included_units)
    #                 overage_cost = overage_units * overage_rate
    #                 total_invoiced = monthly_fee + overage_cost

    #                 # Insert invoice
    #                 cursor.execute("""
    #                     INSERT INTO invoices (
    #                         tenant_id, user_id, period_start, period_end, 
    #                         invoice_date, total_invoiced, is_paid
    #                     )
    #                     VALUES (%s, %s, %s, %s, %s, %s, False)
    #                     RETURNING id
    #                 """, (
    #                     tenant_id, user_id, start_date, end_date, 
    #                     self.utc_now.date(), total_invoiced, False
    #                 ))
    #                 invoice_id = cursor.fetchone()[0]

    #                 # Insert invoice items
    #                 cursor.execute("""
    #                     INSERT INTO invoice_items (
    #                         invoice_id, description, quantity, 
    #                         unit_price, total_price
    #                     )
    #                     VALUES (%s, %s, %s, %s, %s)
    #                 """, (
    #                     invoice_id, f"Base Plan: {plan_name}", 1, 
    #                     monthly_fee, monthly_fee
    #                 ))

    #                 if overage_units > 0:
    #                     cursor.execute("""
    #                         INSERT INTO invoice_items (
    #                             invoice_id, description, quantity, 
    #                             unit_price, total_price
    #                         )
    #                         VALUES (%s, %s, %s, %s, %s)
    #                     """, (
    #                         invoice_id, f"Overage: {overage_units} units", 
    #                         overage_units, overage_rate, overage_cost
    #                     ))

    #                 conn.commit()
    #                 generated_ids.append(invoice_id)
                    
    #                 # Send email
    #                 if not self._send_invoice_email(invoice_id, user_id, tenant_id):
    #                     logger.warning(f"Failed to send email for invoice {invoice_id}")

    #     return generated_ids

    def estimate_invoice_for_user(self, user_id: int, tenant_id: int) -> tuple[list, float]:
        """Estimate invoice for a user based on current month's usage"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get active subscription
                cursor.execute("""
                    SELECT s.plan_id, p.name, p.monthly_fee
                    FROM subscriptions s
                    JOIN plans p ON s.plan_id = p.id
                    WHERE s.user_id = %s AND s.is_active
                """, (user_id,))
                sub = cursor.fetchone()

                if not sub:
                    logger.info(f"No active subscription found for user {user_id}")
                    return [], 0.0

                plan_id, plan_name, monthly_fee = sub
                items = [{
                    "description": f"Base Plan: {plan_name}",
                    "quantity": 1,
                    "unit_price": monthly_fee,
                    "total_price": monthly_fee,
                    "date": self.utc_now.strftime("%Y-%m-%d")
                }]
                total = monthly_fee

                # Get plan metric limits
                cursor.execute("""
                    SELECT pml.metric_id, m.name, pml.metric_limit, pml.overage_rate
                    FROM plan_metric_limits pml
                    JOIN usage_metrics m ON m.id = pml.metric_id
                    WHERE pml.plan_id = %s
                """, (plan_id,))
                limits = cursor.fetchall()

                if not limits:
                    return items, total

                # Calculate usage for current month
                start_date = self.utc_now.replace(day=1).strftime("%Y-%m-%d")
                end_date = self.utc_now.strftime("%Y-%m-%d")

                for metric_id, metric_name, metric_limit, overage_rate in limits:
                    cursor.execute("""
                        SELECT SUM(usage_amount) FROM usage_records
                        WHERE tenant_id = %s AND user_id = %s 
                        AND metric_id = %s AND usage_date BETWEEN %s AND %s
                    """, (tenant_id, user_id, metric_id, start_date, end_date))
                    usage = cursor.fetchone()[0] or 0

                    overage = max(0, usage - metric_limit)
                    if overage > 0:
                        overage_cost = overage * overage_rate
                        items.append({
                            "description": f"Overage - {metric_name} (Limit: {metric_limit})",
                            "quantity": overage,
                            "unit_price": overage_rate,
                            "total_price": overage_cost,
                            "date": self.utc_now.strftime("%Y-%m-%d")
                        })
                        total += overage_cost

                return items, total

    def finalize_invoice_for_user(self, user_id: int, tenant_id: int) -> tuple[bool, str|int]:
        """Create and finalize an invoice for a specific user"""
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    # Check for active subscription
                    cursor.execute("""
                        SELECT plan_id FROM subscriptions 
                        WHERE user_id = %s AND is_active
                    """, (user_id,))
                    if not cursor.fetchone():
                        return False, "No active subscription found."

                    # Estimate invoice
                    items, estimated_total = self.estimate_invoice_for_user(user_id, tenant_id)
                    if not items:
                        return False, "No invoiceable items found."

                    # Insert invoice
                    cursor.execute("""
                        INSERT INTO invoices (
                            user_id, tenant_id, invoice_date, 
                            period_start, period_end, total_invoiced, is_paid
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, False)
                        RETURNING id
                    """, (
                        user_id, tenant_id, self.utc_now.date(),
                        self.utc_now.replace(day=1).date(), 
                        self.utc_now.date(),
                        estimated_total
                    ))
                    
                    invoice_id = cursor.fetchone()[0]

                    # Insert invoice items
                    for item in items:
                        cursor.execute("""
                            INSERT INTO invoice_items (
                                invoice_id, description, quantity, 
                                unit_price, total_price
                            )
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            invoice_id,
                            item["description"],
                            item["quantity"],
                            item["unit_price"],
                            item["total_price"]
                        ))

                    conn.commit()
                    # Send email
                    try:
                        logger.info(f"Sending invoice email for invoice {invoice_id} to user {user_id}")
                        self._send_invoice_email(invoice_id, user_id, tenant_id)
                    except Exception as e:
                        logger.error(f"Email failed for invoice {invoice_id}: {e}")
                        
                    return True, invoice_id

        except Exception as e:
            logger.error(f"Error finalizing invoice: {e}")
            return False, str(e)

    def generate_invoices(self, tenant_id: int, billing_period: str, batch_size: int = 100) -> list[int]:
        """Generate invoices with robust transaction handling"""
        logger.info(f"Generating invoices for tenant {tenant_id} for period {billing_period}")
        
        # Configure decimal handling
        getcontext().prec = 10
        getcontext().rounding = "ROUND_HALF_UP"
        
        try:
            start_date, end_date = self.get_billing_period_range(billing_period)
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"Invalid date range: {e}")
            return []

        generated_ids = []
        
        def to_decimal(value):
            """Safely convert to Decimal with error handling"""
            try:
                return Decimal(str(float(value))) if value is not None else Decimal('0')
            except (ValueError, TypeError, InvalidOperation) as e:
                logger.warning(f"Decimal conversion error for {value}: {e}")
                return Decimal('0')

        def execute_sql(cursor, query, params=None):
            """Execute SQL with error handling"""
            try:
                return cursor.execute(query, params) if params else cursor.execute(query)
            except psycopg2.Error as e:
                logger.error(f"SQL error: {e}")
                raise

        with get_db_connection() as conn:
            try:
                # Start transaction
                conn.autocommit = False
                
                with conn.cursor() as cursor:
                    try:
                        # Get advisory lock
                        execute_sql(cursor, "SELECT pg_try_advisory_xact_lock(%s)", (tenant_id % 2147483647,))
                        if not cursor.fetchone()[0]:
                            logger.error("Could not acquire advisory lock")
                            return []

                        # Get subscriptions
                        execute_sql(cursor, """
                            SELECT s.user_id, s.plan_id, p.name, p.monthly_fee,
                                pml.metric_id, m.name, pml.metric_limit, pml.overage_rate,
                                s.start_date, s.end_date
                            FROM subscriptions s
                            JOIN plans p ON s.plan_id = p.id
                            JOIN plan_metric_limits pml ON p.id = pml.plan_id
                            JOIN usage_metrics m ON pml.metric_id = m.id
                            WHERE s.is_active AND p.tenant_id = %s
                            ORDER BY s.user_id
                        """, (tenant_id,))
                        
                        subscriptions = cursor.fetchall()
                        if not subscriptions:
                            logger.info("No active subscriptions found")
                            return []

                        # Process subscriptions
                        from itertools import groupby
                        keyfunc = lambda x: (x[0], x[1])
                        grouped = groupby(sorted(subscriptions, key=keyfunc), key=keyfunc)

                        for (user_id, plan_id), metrics in grouped:
                            try:
                                metrics = list(metrics)
                                plan_name = metrics[0][2]
                                monthly_fee = to_decimal(metrics[0][3])
                                sub_start = metrics[0][8]
                                sub_end = metrics[0][9]

                                # Check for existing invoice
                                execute_sql(cursor, """
                                    SELECT id FROM invoices 
                                    WHERE tenant_id = %s AND user_id = %s 
                                    AND period_start = %s AND period_end = %s
                                    FOR UPDATE
                                """, (tenant_id, user_id, start_date, end_date))
                                if cursor.fetchone():
                                    logger.info(f"Skipping existing invoice for user {user_id}")
                                    continue

                                # Calculate proration
                                prorate_factor = Decimal('1.0')
                                if sub_start or sub_end:
                                    try:
                                        period_days = Decimal((end_date_dt - start_date_dt).days + 1)
                                        active_days = period_days
                                        if sub_start and sub_start > start_date_dt:
                                            active_days = Decimal((end_date_dt - sub_start).days + 1)
                                        if sub_end and sub_end < end_date_dt:
                                            active_days = Decimal((sub_end - start_date_dt).days + 1)
                                        prorate_factor = (active_days / period_days).quantize(Decimal('0.0001'))
                                    except Exception as e:
                                        logger.error(f"Proration error for user {user_id}: {e}")
                                        prorate_factor = Decimal('1.0')

                                # Calculate invoice
                                base_fee = (monthly_fee * prorate_factor).quantize(Decimal('0.01'))
                                total = base_fee
                                items = [{
                                    "description": f"Base Plan: {plan_name}",
                                    "quantity": 1,
                                    "unit_price": float(base_fee),
                                    "total_price": float(base_fee)
                                }]

                                # Process metrics
                                for metric in metrics:
                                    metric_id, metric_name = metric[4], metric[5]
                                    limit = (to_decimal(metric[6]) * prorate_factor).quantize(Decimal('0.0001'))
                                    rate = to_decimal(metric[7])
                                    
                                    execute_sql(cursor, """
                                        SELECT COALESCE(SUM(usage_amount), 0)
                                        FROM usage_records
                                        WHERE tenant_id = %s AND user_id = %s 
                                        AND metric_id = %s AND usage_date BETWEEN %s AND %s
                                    """, (tenant_id, user_id, metric_id, start_date, end_date))
                                    usage = to_decimal(cursor.fetchone()[0])

                                    overage = max(Decimal('0'), (usage - limit).quantize(Decimal('0.0001')))
                                    if overage > 0:
                                        cost = (overage * rate).quantize(Decimal('0.01'))
                                        items.append({
                                            "description": f"Overage - {metric_name}",
                                            "quantity": float(overage),
                                            "unit_price": float(rate),
                                            "total_price": float(cost)
                                        })
                                        total += cost

                                # Create invoice
                                execute_sql(cursor, """
                                    INSERT INTO invoices (
                                        tenant_id, user_id, period_start, period_end,
                                        invoice_date, total_invoiced, is_paid, payment_status
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, False, 'processing')
                                    RETURNING id
                                """, (
                                    tenant_id, user_id, start_date, end_date,
                                    self.utc_now.date(), float(total.quantize(Decimal('0.01')))
                                ))
                                invoice_id = cursor.fetchone()[0]

                                # Add items
                                for item in items:
                                    execute_sql(cursor, """
                                        INSERT INTO invoice_items (
                                            invoice_id, description, quantity,
                                            unit_price, total_price
                                        )
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (
                                        invoice_id,
                                        item["description"],
                                        item["quantity"],
                                        item["unit_price"],
                                        item["total_price"]
                                    ))

                                # Mark complete
                                execute_sql(cursor, """
                                    UPDATE invoices SET payment_status = 'completed'
                                    WHERE id = %s
                                """, (invoice_id,))

                                generated_ids.append(invoice_id)
                                conn.commit()
                                # Batch commit
                                # if len(generated_ids) % batch_size == 0:
                                #     conn.commit()
                                #     logger.info(f"Committed batch of {batch_size} invoices")

                                # Send email
                                try:
                                    logger.info(f"Sending invoice email for invoice {invoice_id} to user {user_id}")
                                    self._send_invoice_email(invoice_id, user_id, tenant_id)
                                except Exception as e:
                                    logger.error(f"Email failed for invoice {invoice_id}: {e}")

                            except Exception as e:
                                logger.error(f"Error processing user {user_id}: {e}")
                                conn.rollback()
                                continue

                        # Final commit
                        conn.commit()
                        logger.info(f"Successfully generated {len(generated_ids)} invoices")
                        return generated_ids

                    except Exception as e:
                        logger.error(f"Transaction error: {e}")
                        conn.rollback()
                        raise

            except Exception as e:
                logger.error(f"Database connection error: {e}")
                raise
            finally:
                try:
                    conn.autocommit = True
                except:
                    pass

        return generated_ids

    def get_invoice_details(self, invoice_id):
        """
        Returns invoice details dict with enhanced error handling.
        """
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Get invoice header
                cursor.execute("""
                    SELECT 
                        i.id, i.period_start, i.period_end, i.invoice_date,
                        i.total_invoiced, i.subtotal, i.tax_amount, i.is_paid,
                        i.due_date, i.created_at, i.pdf_generated, i.notes,
                        t.id, t.name, t.company_name, t.address,
                        t.email, t.phone, t.vat_number,
                        u.id, u.first_name, u.last_name,
                        u.company_name, u.email, u.username, i.tenant_id
                    FROM invoices i
                    JOIN tenants t ON i.tenant_id = t.id
                    JOIN users u ON i.user_id = u.id
                    WHERE i.id = %s
                """, (invoice_id,))

                invoice_data = cursor.fetchone()
                if not invoice_data:
                    raise ValueError(f"Invoice with ID {invoice_id} not found")

                # Get line items
                cursor.execute("""
                    SELECT 
                        description, quantity, unit_price, total_price, created_at
                    FROM invoice_items
                    WHERE invoice_id = %s
                    ORDER BY id
                """, (invoice_id,))

                items = []
                for item in cursor.fetchall():
                    try:
                        items.append({
                            "description": str(item[0]),
                            "quantity": float(item[1]),
                            "unit_price": float(item[2]),
                            "total_price": float(item[3]),
                            "date": item[4].strftime("%Y-%m-%d") if item[4] else ""
                        })
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error processing invoice item: {e}")
                        continue

                # Build result dictionary 
                result = {
                    "invoice_id": invoice_data[0],
                    "invoice_number": f"INV-{invoice_data[0]:05d}",
                    "period_start": invoice_data[1].strftime("%Y-%m-%d") if invoice_data[1] else "",
                    "period_end": invoice_data[2].strftime("%Y-%m-%d") if invoice_data[2] else "",
                    "invoice_date": invoice_data[3].strftime("%Y-%m-%d") if invoice_data[3] else "",
                    "total_invoiced": float(invoice_data[4]),
                    "subtotal": float(invoice_data[5]),
                    "tax_amount": float(invoice_data[6]) if invoice_data[6] else 0.0,
                    "is_paid": bool(invoice_data[7]),
                    "due_date": invoice_data[8].strftime("%Y-%m-%d") if invoice_data[8] else "",
                    "created_at": invoice_data[9].strftime("%Y-%m-%d %H:%M") if invoice_data[9] else "",
                    "pdf_generated": bool(invoice_data[10]),
                    "notes": str(invoice_data[11]) if invoice_data[11] else "",
                    "tenant": {
                        "id": invoice_data[12],
                        "name": str(invoice_data[13]),
                        "company_name": str(invoice_data[14]),
                        "address": str(invoice_data[15]),
                        "email": str(invoice_data[16]),
                        "phone": str(invoice_data[17]) if invoice_data[17] else "N/A",
                        "vat_number": str(invoice_data[18]) if invoice_data[18] else ""
                    },
                    "customer": {
                        "user_id": invoice_data[19],
                        "name": f"{invoice_data[20]} {invoice_data[21]}",
                        "first_name": str(invoice_data[20]),
                        "last_name": str(invoice_data[21]),
                        "company_name": str(invoice_data[22]),
                        "email": str(invoice_data[23]),
                        "username": str(invoice_data[24])
                    },
                    "items": items,
                    "payment_status": "Paid" if invoice_data[7] else "Unpaid"
                }

                return result

        except Exception as e:
            raise Exception(f"Failed to fetch invoice details: {str(e)}")
        finally:
            if conn:
                conn.close()