def start_separate_schedulers():
    """Starts separate schedulers for each task"""
    scheduler = BackgroundScheduler()

    # Monthly reports at 00:30
    scheduler.add_job(
        main,  # Your existing main function from first script
        CronTrigger(day=1, hour=0, minute=30),
        id="monthly_billing_job",
        replace_existing=True
    )

    # Invoice generation at 01:00
    scheduler.add_job(
        lambda: auto_generate_invoices(),
        CronTrigger(day=1, hour=1, minute=0),
        id="monthly_invoice_job",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Separate schedulers started for monthly tasks")