import logging
from datetime import datetime, timedelta
import time
import traceback
from typing import List
from contextlib import closing

from db.database import get_db_connection
from utils.email_utils import email_billing_report_to_admin

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/monthly_report_scheduler.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_first_of_month() -> bool:
    """Check if today is the first day of the month."""
    return datetime.now().day == 1

def get_all_tenant_ids() -> List[int]:
    """Retrieve all active tenant IDs from the database."""
    with closing(get_db_connection()) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM tenants WHERE is_active = TRUE")
            return [row[0] for row in cursor.fetchall()]

def calculate_report_period() -> tuple:
    """Calculate the start and end dates for the monthly report period."""
    today = datetime.now()
    end_date = (today.replace(day=1) - timedelta(days=1))  # Last day of previous month
    start_date = end_date.replace(day=1)  # First day of previous month
    return start_date.date(), end_date.date()

def process_tenant_report(tenant_id: int, start_date: datetime.date, end_date: datetime.date) -> bool:
    """Generate and email report for a single tenant."""
    try:
        logger.info(f"Processing report for tenant_id {tenant_id}")
        email_billing_report_to_admin(tenant_id, start_date, end_date)
        logger.info(f"Successfully processed tenant_id {tenant_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to process tenant_id {tenant_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def run_monthly_report() -> dict:
    """Execute monthly report generation for all tenants."""
    start_date, end_date = calculate_report_period()
    logger.info(f"Starting monthly billing reports for period {start_date} to {end_date}")
    
    tenant_ids = get_all_tenant_ids()
    if not tenant_ids:
        logger.warning("No active tenants found for report generation")
        return {'success': 0, 'failed': 0}
    
    results = {'success': 0, 'failed': 0}
    
    for tenant_id in tenant_ids:
        if process_tenant_report(tenant_id, start_date, end_date):
            results['success'] += 1
        else:
            results['failed'] += 1
            time.sleep(1)  # Brief pause between failures
    
    logger.info(
        f"Report generation completed. Success: {results['success']}, Failed: {results['failed']}"
    )
    return results

def retry_on_failure(max_retries: int = 3, initial_delay: int = 60) -> bool:
    """Retry the report generation with exponential backoff."""
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt}/{max_retries}")
            results = run_monthly_report()
            
            if results['failed'] == 0:
                return True
                
            # If any failures, consider retrying
            if attempt < max_retries:
                logger.warning(f"Will retry in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            
        except Exception as e:
            logger.error(f"Attempt {attempt} failed: {str(e)}")
            if attempt < max_retries:
                logger.warning(f"Will retry in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
    
    logger.error("All retry attempts failed")
    return False

def main():
    """Main execution function for the monthly report scheduler."""
    logger.info("==== Monthly Billing Scheduler Started ====")
    
    if is_first_of_month():
        logger.info("First of month detected - starting report generation")
        success = retry_on_failure()
        
        if not success:
            # Add notification logic here (email admin, etc.)
            logger.critical("Report generation failed after all retries")
    else:
        logger.info("Not first of month - no reports to generate")
    
    logger.info("==== Monthly Billing Scheduler Completed ====")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        logger.debug(traceback.format_exc())