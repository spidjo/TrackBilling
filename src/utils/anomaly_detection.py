# src/utils/anomaly_detection.py

from db.database import get_db_connection
from datetime import datetime, timedelta

def detect_anomalies(user_id, metric_type, threshold=2.0):
    conn = get_db_connection()
    cursor = conn.cursor()

    last_7_days = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT usage_date, quantity
        FROM usage_metrics
        WHERE user_id = ? AND metric_type = ? AND usage_date >= ?
        ORDER BY usage_date
    """, (user_id, metric_type, last_7_days))
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 3:
        return None

    quantities = [r[1] for r in rows]
    avg = sum(quantities[:-1]) / len(quantities[:-1])
    latest = quantities[-1]

    if latest > threshold * avg:
        return {
            "average": avg,
            "latest": latest,
            "anomaly": True
        }
    return None
