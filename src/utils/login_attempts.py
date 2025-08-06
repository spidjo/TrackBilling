import time
from collections import defaultdict

# username → [timestamps]
attempt_log = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 minutes

def is_rate_limited(username):
    now = time.time()
    recent_attempts = [ts for ts in attempt_log[username] if now - ts < WINDOW_SECONDS]
    attempt_log[username] = recent_attempts

    if len(recent_attempts) >= MAX_ATTEMPTS:
        return True
    return False

def log_attempt(username):
    attempt_log[username].append(time.time())
