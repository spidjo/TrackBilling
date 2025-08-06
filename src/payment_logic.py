# payment_logic.py
#
# This module provides logic for recording payments against invoices.
# It inserts payment records into the database and updates the invoice status to "paid"
# if the total payments meet or exceed the invoice amount.

from datetime import datetime
from db.database import get_db_connection

def record_payment(invoice_id, amount, method='manual', notes=None):
    """
    Records a payment for a given invoice. If the invoice is fully paid after this payment,
    marks the invoice as paid.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert payment record into the payments table
    cursor.execute("""
        INSERT INTO payments (invoice_id, amount, payment_method, notes)
        VALUES (?, ?, ?, ?)
    """, (invoice_id, amount, method, notes))

    # Retrieve the total amount due for the invoice
    cursor.execute("SELECT total_amount FROM invoices WHERE id = ?", (invoice_id,))
    total = cursor.fetchone()
    if total:
        total_amount = total[0]

        # Calculate the total amount paid so far for this invoice
        cursor.execute("""
            SELECT SUM(amount) FROM payments WHERE invoice_id = ?
        """, (invoice_id,))
        total_paid = cursor.fetchone()[0] or 0.0

        # If the invoice is fully paid or overpaid, mark it as paid
        if total_paid >= total_amount:
            cursor.execute("""
                UPDATE invoices SET is_paid = 1 WHERE id = ?
            """, (invoice_id,))

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    return True