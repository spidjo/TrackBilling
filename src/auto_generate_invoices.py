# src/auto_generate_invoices.py
import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager
from decimal import Decimal
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


@contextmanager
def database_connection():
    """Context manager for database connections with automatic cleanup."""
    from db.database import get_db_connection
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


class InvoiceGenerator:
    """Handles automatic generation of invoices using BillingEngine."""

    BATCH_SIZE = 100

    def __init__(self, billing_date: Optional[date] = None):
        """
        Initialize invoice generator.
        
        Args:
            billing_date: Optional date to use for billing period (defaults to 1st of previous month)
        """
        print("Initializing InvoiceGenerator...")
        from billing_engine import BillingEngine
        self.billing_engine = BillingEngine()
        
        # Set billing_date to 1st day of previous month if not provided
        if billing_date is None:
            today = date.today()
            first_day_of_current_month = today.replace(day=1)
            self.billing_date = first_day_of_current_month #- relativedelta(months=1)
        else:
            self.billing_date = billing_date
            
        self.billing_period = self.billing_date.strftime("%Y-%m")
        self.results = {
            "success": False,
            "count": 0,
            "errors": [],
            "warnings": []
        }

    def generate_invoices(self) -> Dict[str, any]:
        """Main entry point for invoice generation with duplicate prevention."""
        try:
            # First check if we've already processed this billing period
            if self._is_period_processed():
                logger.info(f"Invoices already generated for period {self.billing_period}")
                return {
                    "success": True,
                    "count": 0,
                    "errors": [],
                    "warnings": [f"Invoices already generated for {self.billing_period}"]
                }

            logger.info(f"Starting invoice generation for period {self.billing_period} (billing date: {self.billing_date})")
            self._process_tenants()
            self.results["success"] = self.results["count"] > 0 or not self.results["errors"]
            
            # Mark period as processed if successful
            if self.results["success"]:
                self._mark_period_processed()
                
            return self.results
        except Exception as e:
            error_msg = f"Critical error in invoice generation: {str(e)}"
            logger.critical(error_msg, exc_info=True)
            self.results["errors"].append(error_msg)
            self.results["success"] = False
            return self.results

    def _is_period_processed(self) -> bool:
        """Check if this billing period has already been processed."""
        with database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM invoice_generation_log
                WHERE period = %s
                AND status = 'completed'
                LIMIT 1
            """, (self.billing_period,))
            return cursor.fetchone() is not None

    def _mark_period_processed(self):
        """Mark this billing period as processed in the log."""
        with database_connection() as conn:
            cursor = conn.cursor()
            try:
                # First try to update existing record
                cursor.execute("""
                    UPDATE invoice_generation_log
                    SET 
                        generated_at = %s,
                        invoice_count = %s,
                        status = %s
                    WHERE period = %s
                """, (
                    datetime.now(),
                    self.results["count"],
                    "completed",
                    self.billing_period
                ))
                
                # If no rows were updated, insert new record
                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO invoice_generation_log (
                            period, 
                            generated_at, 
                            invoice_count,
                            status
                        )
                        VALUES (%s, %s, %s, %s)
                    """, (
                        self.billing_period,
                        datetime.now(),
                        self.results["count"],
                        "completed"
                    ))
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            
    def _process_tenants(self):
        """Process all active tenants in batches."""
        processed = 0
        while True:
            try:
                with database_connection() as conn:
                    tenants = self._fetch_tenant_batch(conn, processed)
                    if not tenants:
                        break

                    for tenant in tenants:
                        self._process_single_tenant(tenant[0])

                    processed += len(tenants)
                    logger.debug(f"Processed batch of {len(tenants)} tenants")

            except Exception as e:
                error_msg = f"Batch processing failed at offset {processed}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.results["errors"].append(error_msg)
                if processed + self.BATCH_SIZE > 1000:  # Safety limit
                    break
                continue

    def _fetch_tenant_batch(self, conn, offset: int) -> List[Tuple]:
        """Fetch a batch of active tenants that should be billed."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM tenants
            WHERE is_active = TRUE
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (self.BATCH_SIZE, offset))
        return cursor.fetchall()

    def _process_single_tenant(self, tenant_id: int):
        """Process a single tenant and generate invoices."""
        try:
            logger.info(f"Generating invoices for tenant {tenant_id}")
            generated_ids = self.billing_engine.generate_invoices(
                tenant_id=tenant_id,
                billing_period=self.billing_period
            )
            
            if generated_ids:
                self.results["count"] += len(generated_ids)
                logger.info(f"Generated {len(generated_ids)} invoices for tenant {tenant_id}")
            else:
                logger.info(f"No invoices generated for tenant {tenant_id}")

        except Exception as e:
            error_msg = f"Failed to process tenant {tenant_id}: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)


def auto_generate_invoices(billing_date: Optional[date] = None) -> Dict[str, any]:
    """
    Automatically generates invoices for all active subscriptions in all tenants.
    
    Args:
        billing_date: Optional date to use for billing (defaults to 1st of previous month)
    
    Returns:
        dict: {
            "success": bool (True if no critical errors),
            "count": int (number of invoices generated),
            "errors": list[str] (error messages),
            "warnings": list[str] (non-critical issues)
        }
    """
    logger.info("Starting automatic invoice generation")
    try:
        generator = InvoiceGenerator(billing_date)
        result = generator.generate_invoices()
        logger.info(
            f"Invoice generation completed. Generated {result['count']} invoices. "
            f"Errors: {len(result['errors'])}, Warnings: {len(result['warnings'])}"
        )
        return result
    except Exception as e:
        logger.critical(f"Fatal error in invoice generation: {str(e)}", exc_info=True)
        return {
            "success": False,
            "count": 0,
            "errors": [f"Fatal error: {str(e)}"],
            "warnings": []
        }