import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Settings
target_size_mb = 0.5
filename = "usage_upload_test_1MB.csv"
num_rows = 1000  # Start with 1000 rows, adjust if needed

# Sample data for metrics and user IDs
metric_names = ['API Calls', 'SMS Messages', 'Data Storage']
user_ids = [str(i) for i in {53,54,55,57,58,59,61,62,63}]  # 25 unique user IDs

# Generate synthetic data
np.random.seed(42)

data = {
    'user_id': np.random.choice(user_ids, num_rows),
    'metric_name': np.random.choice(metric_names, num_rows),
    'usage_amount': np.random.randint(1, 1000, num_rows),
    'usage_date': [ (datetime(2025,1,1) + timedelta(days=np.random.randint(0, 260))).strftime('%Y-%m-%d') for _ in range(num_rows) ]
}

df = pd.DataFrame(data)

# Save to CSV and check size
df.to_csv(filename, index=False)

import os

filesize_mb = os.path.getsize(filename) / (1024 * 1024)
print(f"Generated file size: {filesize_mb:.2f} MB")

# Adjust rows if file size is off target
while filesize_mb < target_size_mb:
    # Double rows
    df = pd.concat([df, df], ignore_index=True)
    df.to_csv(filename, index=False)
    filesize_mb = os.path.getsize(filename) / (1024 * 1024)
    print(f"Updated file size: {filesize_mb:.2f} MB")

print(f"Final CSV file '{filename}' size: {filesize_mb:.2f} MB with {len(df)} rows")
