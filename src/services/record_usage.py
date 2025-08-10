from datetime import datetime
from db.database import get_db_connection
from utils.anomaly_detection import detect_anomalies
from services.email_alerts import send_alert_email
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_user_email(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def record_usage(user_id, tenant_id, metric_type, metric_subtype, quantity):
    try:
        quantity = float(quantity)
    except ValueError:
        logger.error(f"❌ Invalid quantity for user {user_id}: {quantity}")
        return

    usage_date = datetime.utcnow().strftime("%Y-%m-%d")
    usage_period = usage_date[:7]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insert into usage_metrics
        cursor.execute("""
            INSERT INTO usage_metrics (tenant_id, user_id, metric_type, metric_subtype, quantity, usage_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (tenant_id, user_id, metric_type, metric_subtype, quantity, usage_date))
        logger.info(f"📥 Usage recorded: user={user_id}, metric={metric_type}, qty={quantity}")

        # Upsert into usage_aggregates
        cursor.execute("""
            SELECT total_quantity FROM usage_aggregates
            WHERE tenant_id = %s AND user_id = %s AND metric_type = %s AND metric_subtype = %s AND period = %s
        """, (tenant_id, user_id, metric_type, metric_subtype, usage_period))
        row = cursor.fetchone()

        if row:
            cursor.execute("""
                UPDATE usage_aggregates
                SET total_quantity = total_quantity + %s
                WHERE tenant_id = %s AND user_id = %s AND metric_type = %s AND metric_subtype = %s AND period = %s
            """, (quantity, tenant_id, user_id, metric_type, metric_subtype, usage_period))
        else:
            cursor.execute("""
                INSERT INTO usage_aggregates (tenant_id, user_id, metric_type, metric_subtype, period, total_quantity)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (tenant_id, user_id, metric_type, metric_subtype, usage_period, quantity))

        conn.commit()

    except Exception as db_err:
        conn.rollback()
        logger.error(f"❌ DB error during usage recording: {db_err}")
    finally:
        conn.close()

    # Run anomaly detection
    try:
        anomaly = detect_anomalies(user_id, metric_type)
        if anomaly and anomaly.get("anomaly"):
            user_email = get_user_email(user_id)
            if user_email:
                subject = f"⚠️ Usage Alert: {metric_type} anomaly detected"
                body = (
                    f"Dear User,\n\n"
                    f"We detected a spike in your usage for '{metric_type}'.\n\n"
                    f"📊 Average (last 7 days): {anomaly['average']:.2f} units\n"
                    f"🚨 Latest entry: {anomaly['latest']} units\n\n"
                    f"Please review your usage in the dashboard.\n\n"
                    f"Regards,\nBilling Intelligence Platform"
                )
                send_alert_email(user_email, subject, body)
                logger.info(f"📧 Anomaly alert sent to {user_email}")
    except Exception as anomaly_err:
        logger.warning(f"⚠️ Anomaly detection failed: {anomaly_err}")
