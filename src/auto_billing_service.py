import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import List
from contextlib import closing

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import psycopg2
import psycopg2.extras

from billing_engine import BillingEngine
from utils.email_utils import email_billing_report_to_admin


# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/auto_billing_service.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    return psycopg2.connect(
        dbname="billing_db",
        user="postgres",
        password="admin",
        host="localhost",
        options="-c client_encoding=utf8 -c bytea_output=escape",
        cursor_factory=psycopg2.extras.DictCursor
    )

def get_all_tenant_ids() -> List[int]:
    """Retrieve all active tenant IDs from the database."""
    with closing(get_db_connection()) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM tenants WHERE is_active = TRUE")
            return [row[0] for row in cursor.fetchall()]


def calculate_report_period() -> tuple:
    """Get the previous month's first and last date."""
    today = datetime.now()
    end_date = today.replace(day=1) - timedelta(days=1)  # last day of prev month
    start_date = end_date.replace(day=1)  # first day of prev month
    return start_date.date(), end_date.date()


def process_tenant_billing(tenant_id: int, start_date, end_date) -> bool:
    """Generate invoice & email report for one tenant."""
    billing_engine = BillingEngine()
    try:
        logger.info(f"Running billing for tenant_id {tenant_id} ({start_date} → {end_date})")
        # Step 1: Generate invoice
        billing_engine.generate_invoices_for_all_tenants(tenant_filter=[tenant_id])
        # Step 2: Email billing report to tenant admin
        email_billing_report_to_admin(tenant_id, start_date, end_date)
        logger.info(f"Tenant {tenant_id} billing completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Billing failed for tenant_id {tenant_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def run_monthly_report():
    """Execute monthly report generation for all tenants."""
    start_date, end_date = calculate_report_period()
    logger.info(f"Starting monthly billing reports for period {start_date} to {end_date}")

    tenant_ids = get_all_tenant_ids()
    if not tenant_ids:
        logger.warning("No active tenants found for report generation")
        return {'success': 0, 'failed': 0}

    results = {'success': 0, 'failed': 0}
    for tenant_id in tenant_ids:
        if process_tenant_billing(tenant_id, start_date, end_date):
            results['success'] += 1
        else:
            results['failed'] += 1
            time.sleep(1)

    logger.info(f"Report generation completed. Success: {results['success']}, Failed: {results['failed']}")
    return results

def start_scheduler():
    """Starts the background scheduler for monthly billing."""
    scheduler = BackgroundScheduler()

    # Run on the 1st of every month at 00:30
    scheduler.add_job(
        run_monthly_report,
        CronTrigger(day=1, hour=0, minute=30),
        id="monthly_billing_job",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Auto-billing scheduler started (runs on 1st of month at 00:30).")

    # -------------------
    # Immediate Test Run
    # -------------------
    logger.info("Running immediate test billing job...")
    try:
        run_monthly_report()
    except Exception as e:
        logger.error(f"Immediate test run failed: {str(e)}")

    logger.info("Service is now waiting for next scheduled run...")
    
    try:
        while True:
            time.sleep(60)  # Keep the script alive
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    start_scheduler()
