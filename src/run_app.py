# src/run_app.py
import subprocess
import signal
import sys
import time

processes = []

def start_process(cmd):
    print(f"Starting: {' '.join(cmd)}")
    p = subprocess.Popen(cmd)
    processes.append(p)
    return p

def stop_all(signum, frame):
    print("Stopping all processes...")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(2)
    for p in processes:
        if p.poll() is None:
            p.kill()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop_all)
    signal.signal(signal.SIGINT, stop_all)

    # Start Streamlit
    start_process([
        "/home/ubuntu/sgltrack/venv/bin/streamlit", "run", "src/main.py",
        "--server.port=8501", "--server.headless=true"
    ])

    # Start FastAPI (verify_email.py)
    start_process([
        "/home/ubuntu/sgltrack/venv/bin/uvicorn", "src.verify_email:app",
        "--host", "127.0.0.1", "--port", "8000", "--workers", "1"
    ])

    # Wait forever
    while True:
        time.sleep(5)
