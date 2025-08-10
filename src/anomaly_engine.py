import sqlite3
from datetime import datetime, timedelta
from db.database import get_db_connection

THRESHOLD_SPIKE = 2.0
THRESHOLD_DROP = 0.5
HISTORY_DAYS = 30

def detect_anomalies():
    print("Starting anomaly detection...")
    conn = get_db_connection()
    cursor = conn.cursor()
    # Get recent usage
    cursor.execute("""
        SELECT ur.id, ur.tenant_id, ur.user_id, ur.metric_id, ur.usage_amount, ur.usage_date
        FROM usage_records ur
        WHERE ur.usage_date >= date('now', '-1 day')
    """)
    recent_usage = cursor.fetchall()

    for record in recent_usage:
        ur_id, tenant_id, user_id, metric_id, usage_amount, usage_date = record

        # Calculate historical average for the past 30 days
        cursor.execute("""
            SELECT AVG(usage_amount)
            FROM usage_records
            WHERE metric_id = %s
              AND usage_date BETWEEN date(%s, %s) AND date(%s, '-1 day')
        """, (metric_id, usage_date, f"-{HISTORY_DAYS} days", usage_date))

        avg_usage = cursor.fetchone()[0] or 0

        print(f"Checking usage {usage_amount} against average {avg_usage} for metric {metric_id}")
        anomaly_type = None
        if avg_usage > 0:
            ratio = usage_amount / avg_usage
            if ratio > THRESHOLD_SPIKE:
                anomaly_type = 'spike'
            elif ratio < THRESHOLD_DROP:
                anomaly_type = 'drop'

        if anomaly_type:
            # Insert anomaly
            cursor.execute("""
                INSERT INTO anomalies (
                    tenant_id, user_id,  metric_id,
                    anomaly_type, anomaly_description,
                    detected_value, expected_value, threshold_value, detected_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                tenant_id, user_id, metric_id,
                anomaly_type,
                f"{anomaly_type.title()} detected: usage = {usage_amount:.2f}, avg = {avg_usage:.2f}",
                usage_amount, avg_usage,
                THRESHOLD_SPIKE if anomaly_type == 'spike' else THRESHOLD_DROP
            ))

    conn.commit()
    conn.close()
    print(f"Anomaly detection complete: {len(recent_usage)} records scanned.")



detect_anomalies()