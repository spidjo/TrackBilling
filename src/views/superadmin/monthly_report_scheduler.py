# monthly_report_scheduler.py

import logging
from datetime import datetime, timedelta
import time
import traceback

from db.database import get_db_connection
from utils.email_utils import email_billing_report_to_admin

# --- Setup Logging ---
logging.basicConfig(
    filename="logs/monthly_report_scheduler.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def is_first_of_month():
    return datetime.today().day == 1

def get_all_tenant_ids():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tenants")
    tenants = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tenants

def run_monthly_report():
    today = datetime.today()
    start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    end_date = today.replace(day=1) - timedelta(days=1)

    logging.info("Preparing billing reports for %s to %s", start_date.date(), end_date.date())

    tenant_ids = get_all_tenant_ids()

    for tenant_id in tenant_ids:
        try:
            logging.info(f"Generating report for tenant_id {tenant_id}")
            email_billing_report_to_admin(tenant_id, start_date.date(), end_date.date())
            logging.info(f"Successfully emailed billing report to tenant_id {tenant_id}")
        except Exception as e:
            logging.error(f"❌ Failed to process tenant_id {tenant_id}: {str(e)}")
            logging.debug(traceback.format_exc())

def retry_on_failure(max_retries=3, delay_seconds=60):
    for attempt in range(1, max_retries + 1):
        try:
            run_monthly_report()
            break
        except Exception as e:
            logging.warning(f"Retry {attempt}/{max_retries} after failure: {e}")
            time.sleep(delay_seconds)
    else:
        logging.critical("❌ All retries failed. Manual intervention may be required.")

if __name__ == "__main__":
    logging.info("---- Monthly Billing Scheduler Started ----")

    if is_first_of_month():
        logging.info("Today is the first of the month. Starting report generation.")
        retry_on_failure()
    else:
        logging.info("Today is not the first of the month. Skipping report generation.")

    logging.info("---- Monthly Billing Scheduler Ended ----")
