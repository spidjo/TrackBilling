import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/job_viewer.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_scheduler_jobs(scheduler):
    """Retrieve and display all scheduled jobs"""
    jobs = scheduler.get_jobs()
    
    if not jobs:
        print("No scheduled jobs found.")
        return
    
    print(f"\n{'='*80}")
    print(f"SCHEDULED JOBS REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    for i, job in enumerate(jobs, 1):
        print(f"\nJOB #{i}:")
        print(f"  ID: {job.id}")
        print(f"  Name: {job.name or 'Unnamed'}")
        print(f"  Function: {job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)}")
        print(f"  Next run: {job.next_run_time}")
        print(f"  Trigger: {job.trigger}")
        print(f"  Pending: {job.pending}")
        
        # Get job details
        try:
            job_details = {
                'args': job.args,
                'kwargs': job.kwargs,
                'max_instances': job.max_instances,
                'misfire_grace_time': job.misfire_grace_time,
                'coalesce': job.coalesce
            }
            print(f"  Details: {json.dumps(str(job_details), indent=4)}")
        except Exception as e:
            print(f"  Details: Error retrieving - {str(e)}")
    
    print(f"\nTotal jobs: {len(jobs)}")
    print(f"{'='*80}")

def get_job_details(scheduler, job_id):
    """Get detailed information about a specific job"""
    try:
        job = scheduler.get_job(job_id)
        if job:
            print(f"\n{'='*60}")
            print(f"DETAILS FOR JOB: {job_id}")
            print(f"{'='*60}")
            
            details = {
                'id': job.id,
                'name': job.name,
                'function': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                'next_run_time': str(job.next_run_time),
                'trigger': str(job.trigger),
                'pending': job.pending,
                'args': job.args,
                'kwargs': job.kwargs,
                'max_instances': job.max_instances,
                'misfire_grace_time': job.misfire_grace_time,
                'coalesce': job.coalesce
            }
            
            for key, value in details.items():
                print(f"{key.replace('_', ' ').title():<20}: {value}")
            
            # Show trigger details if available
            if hasattr(job.trigger, '__str__'):
                print(f"\nTrigger details:")
                print(f"  {str(job.trigger)}")
                
        else:
            print(f"Job with ID '{job_id}' not found.")
            
    except JobLookupError:
        print(f"Job with ID '{job_id}' not found.")
    except Exception as e:
        print(f"Error retrieving job details: {str(e)}")

def pause_job(scheduler, job_id):
    """Pause a specific job"""
    try:
        scheduler.pause_job(job_id)
        print(f"Job '{job_id}' paused successfully.")
    except JobLookupError:
        print(f"Job with ID '{job_id}' not found.")
    except Exception as e:
        print(f"Error pausing job: {str(e)}")

def resume_job(scheduler, job_id):
    """Resume a paused job"""
    try:
        scheduler.resume_job(job_id)
        print(f"Job '{job_id}' resumed successfully.")
    except JobLookupError:
        print(f"Job with ID '{job_id}' not found.")
    except Exception as e:
        print(f"Error resuming job: {str(e)}")

def remove_job(scheduler, job_id):
    """Remove a job from the scheduler"""
    try:
        scheduler.remove_job(job_id)
        print(f"Job '{job_id}' removed successfully.")
    except JobLookupError:
        print(f"Job with ID '{job_id}' not found.")
    except Exception as e:
        print(f"Error removing job: {str(e)}")

def view_scheduler_status(scheduler):
    """Display scheduler status information"""
    print(f"\n{'='*50}")
    print("SCHEDULER STATUS")
    print(f"{'='*50}")
    print(f"Running: {scheduler.running}")
    print(f"Started: {scheduler.state}")
    print(f"Job Store: {type(scheduler._jobstores['default']).__name__}")
    print(f"Number of jobs: {len(scheduler.get_jobs())}")
    print(f"{'='*50}")

def interactive_menu(scheduler):
    """Interactive menu for job management"""
    while True:
        print(f"\n{'='*50}")
        print("APSCHEDULER JOB MANAGER")
        print(f"{'='*50}")
        print("1. View all jobs")
        print("2. View scheduler status")
        print("3. Get job details")
        print("4. Pause job")
        print("5. Resume job")
        print("6. Remove job")
        print("7. Refresh")
        print("8. Exit")
        print(f"{'='*50}")
        
        choice = input("Enter your choice (1-8): ").strip()
        
        if choice == '1':
            get_scheduler_jobs(scheduler)
            
        elif choice == '2':
            view_scheduler_status(scheduler)
            
        elif choice == '3':
            job_id = input("Enter job ID: ").strip()
            if job_id:
                get_job_details(scheduler, job_id)
            else:
                print("Please enter a valid job ID.")
                
        elif choice == '4':
            job_id = input("Enter job ID to pause: ").strip()
            if job_id:
                pause_job(scheduler, job_id)
            else:
                print("Please enter a valid job ID.")
                
        elif choice == '5':
            job_id = input("Enter job ID to resume: ").strip()
            if job_id:
                resume_job(scheduler, job_id)
            else:
                print("Please enter a valid job ID.")
                
        elif choice == '6':
            job_id = input("Enter job ID to remove: ").strip()
            if job_id:
                confirm = input(f"Are you sure you want to remove job '{job_id}'? (y/N): ").strip().lower()
                if confirm == 'y':
                    remove_job(scheduler, job_id)
                else:
                    print("Operation cancelled.")
            else:
                print("Please enter a valid job ID.")
                
        elif choice == '7':
            print("Refreshing...")
            
        elif choice == '8':
            print("Exiting job manager.")
            break
            
        else:
            print("Invalid choice. Please enter a number between 1-8.")

def simple_job_viewer(scheduler):
    """Simple function to just view jobs without interactive menu"""
    print("Simple Job Viewer - Current Scheduled Jobs:")
    print("-" * 50)
    jobs = scheduler.get_jobs()
    
    for job in jobs:
        status = "PAUSED" if job.next_run_time is None else "ACTIVE"
        print(f"ID: {job.id}")
        print(f"Name: {job.name or 'N/A'}")
        print(f"Function: {job.func.__name__ if hasattr(job.func, '__name__') else 'Unknown'}")
        print(f"Next run: {job.next_run_time}")
        print(f"Status: {status}")
        print(f"Trigger: {job.trigger}")
        print("-" * 30)

# Main execution 
if __name__ == "__main__":
    # Initialize the scheduler (assuming it's already running in your application)
    # If you need to create a new instance, use:
    # scheduler = BackgroundScheduler()
    # scheduler.start()
    
    # For this script, we'll assume the scheduler is passed or we need to connect to existing one
    # In practice, you might need to share the scheduler instance
    
    print("APScheduler Job Viewer")
    print("Note: This script needs access to the scheduler instance.")
    print("You'll need to modify it to get your actual scheduler instance.")
    
    # Example usage if you have the scheduler instance:
    # scheduler = your_existing_scheduler_instance
    # get_scheduler_jobs(scheduler)
    # interactive_menu(scheduler)
    
    # Alternative: Create a minimal scheduler for demonstration
    demo_scheduler = BackgroundScheduler()
    demo_scheduler.start()
    
    # Add a demo job
    # def demo_task():
    #     print("Demo task executed")
    
    # demo_scheduler.add_job(
    #     demo_task,
    #     'interval',
    #     minutes=5,
    #     id='demo_job',
    #     name='Demo Task'
    # )
    
    print("\nDemo mode - showing example with demo job:")
    get_scheduler_jobs(demo_scheduler)
    
    # Clean up demo scheduler
    demo_scheduler.shutdown()