from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
import time
import traceback

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/combined_monthly_scheduler.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_monthly_tasks():
    """Execute both monthly tasks: reports and invoice generation"""
    logger.info("==== Starting Monthly Combined Tasks ====")
    
    # Import and run the first script (monthly reports)
    try:
        from monthly_report import retry_on_failure  
        logger.info("Running monthly billing reports...")
        report_success = retry_on_failure()
        if not report_success:
            logger.error("Monthly reports failed after retries")
    except Exception as e:
        logger.error(f"Failed to run monthly reports: {str(e)}")
        logger.debug(traceback.format_exc())
    
    # Import and run the second script (invoice generation)
    try:
        from auto_generate_invoices import auto_generate_invoices
        logger.info("Running automatic invoice generation...")
        invoice_result = auto_generate_invoices()
        if not invoice_result["success"]:
            logger.error(f"Invoice generation failed: {invoice_result['errors']}")
        else:
            logger.info(f"Generated {invoice_result['count']} invoices successfully")
    except Exception as e:
        logger.error(f"Failed to run invoice generation: {str(e)}")
        logger.debug(traceback.format_exc())
    
    logger.info("==== Monthly Combined Tasks Completed ====")

def start_combined_scheduler():
    """Starts the background scheduler for both monthly tasks"""
    scheduler = BackgroundScheduler()

    # Run on the 1st of every month at 01:00 (30 minutes after reports)
    scheduler.add_job(
        run_monthly_tasks,
        CronTrigger(day=1, hour=1, minute=0),  # 1:00 AM on 1st of month
        id="combined_monthly_tasks_job",
        replace_existing=True,
        name="Monthly Reports and Invoice Generation"
    )

    scheduler.start()
    logger.info("Combined monthly scheduler started (runs on 1st of month at 01:00).")
    
    # Keep the scheduler running
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")

if __name__ == "__main__":
    try:
        start_combined_scheduler()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        logger.debug(traceback.format_exc())