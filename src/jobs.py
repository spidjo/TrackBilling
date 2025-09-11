import scheduler
import apscheduler.schedulers.background

for job in scheduler.get_jobs():
    print(job)