from apscheduler.schedulers.background import BackgroundScheduler

def my_job():
    print("Job executed!")

scheduler = BackgroundScheduler()


# Get all scheduled jobs
jobs = scheduler.get_jobs()
for job in jobs:
    print(f"Job Name: {job.name}, Next Run Time: {job.next_run_time}, Trigger: {job.trigger}")
