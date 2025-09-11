# src/payment_logic.py

from datetime import datetime, timedelta
from decimal import Decimal
from db.database import get_db_connection
import logging
from enum import Enum

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentStatus(str, Enum):
    PAID = "paid"
    PARTIAL = "partial"
    UNPAID = "unpaid"
    OVERDUE = "overdue" 

class PaymentError(Exception):
    """Custom exception for payment-related errors"""
    pass

def record_payment(invoice_id: int, amount: Decimal, method: str = 'manual', notes: str = None) -> dict:
    """
    Records a payment for a given invoice and updates invoice status.
    Returns dict with success, payment_id, new_status, is_overdue, and remaining_balance.
    """
    if not isinstance(invoice_id, int) or invoice_id <= 0:
        raise ValueError("Invalid invoice ID")
    if not isinstance(amount, Decimal) or amount <= Decimal('0'):
        raise ValueError("Payment amount must be a positive Decimal")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        conn.autocommit = False
        
        # Get invoice details with lock - include created_at for overdue calculation
        cursor.execute("""
            SELECT id, total_invoiced, due_date, payment_status, is_overdue, created_at
            FROM invoices 
            WHERE id = %s 
            FOR UPDATE
        """, (invoice_id,))
        invoice = cursor.fetchone()
        
        if not invoice:
            raise PaymentError(f"Invoice {invoice_id} not found")
            
        invoice_id, total_amount, due_date, current_status, current_overdue, created_at = invoice
        
        # Calculate if invoice is overdue (consider grace period if needed)
        is_overdue = False
        if due_date:
            grace_period = timedelta(days=7)  # Optional grace period
            is_overdue = datetime.utcnow().date() > (due_date + grace_period)
        
        # Insert payment record
        cursor.execute("""
            INSERT INTO payments (invoice_id, amount, payment_method, notes, payment_date)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (invoice_id, amount, method, notes, datetime.utcnow()))
        
        payment_id = cursor.fetchone()[0]
        
        # Calculate new payment status
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) 
            FROM payments 
            WHERE invoice_id = %s
        """, (invoice_id,))
        total_paid = cursor.fetchone()[0]
        
        remaining_balance = total_amount - total_paid
        
        # Determine normalized status (now includes OVERDUE)
        if remaining_balance <= 0:
            new_status = PaymentStatus.PAID
            is_paid = True
            is_overdue = False  # Can't be overdue if paid
        elif is_overdue:
            new_status = PaymentStatus.OVERDUE
            is_paid = False
        elif total_paid > 0:
            new_status = PaymentStatus.PARTIAL
            is_paid = False
        else:
            new_status = PaymentStatus.UNPAID
            is_paid = False
        
        # Update invoice status
        cursor.execute("""
            UPDATE invoices 
            SET 
                payment_status = %s,
                is_paid = %s,
                is_overdue = %s,
                total_paid = %s,
                paid_at = CASE WHEN %s THEN %s ELSE paid_at END,
                credit_amount = CASE WHEN %s < 0 THEN ABS(%s) ELSE 0 END
            WHERE id = %s
        """, (
            new_status.value,
            is_paid,
            is_overdue,
            total_paid,
            remaining_balance <= 0,
            datetime.utcnow(),
            remaining_balance,
            remaining_balance,
            invoice_id
        ))
        
        conn.commit()
        return {
            'success': True,
            'payment_id': payment_id,
            'new_status': new_status,
            'is_overdue': is_overdue,
            'remaining_balance': max(Decimal('0'), remaining_balance)
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error recording payment: {str(e)}")
        raise PaymentError(f"Payment processing failed: {str(e)}")
    finally:
        if conn:
            conn.close()

def get_invoice_payment_summary(invoice_id: int) -> dict:
    """Returns payment summary for an invoice with normalized status"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                i.total_invoiced,
                i.payment_status,
                i.is_overdue,
                i.due_date,
                COALESCE(SUM(p.amount), 0) as paid_amount,
                i.credit_amount
            FROM invoices i
            LEFT JOIN payments p ON p.invoice_id = i.id
            WHERE i.id = %s
            GROUP BY i.id
        """, (invoice_id,))
        
        result = cursor.fetchone()
        if not result:
            raise PaymentError("Invoice not found")
            
        total, status, is_overdue, due_date, paid, credit = result
        remaining = total - paid
        
        return {
            'total_amount': total,
            'paid_amount': paid,
            'remaining_balance': remaining,
            'credit_amount': credit,
            'payment_status': status,
            'is_overdue': is_overdue,
            'due_date': due_date
        }
        
    except Exception as e:
        logger.error(f"Error getting payment summary: {str(e)}")
        raise PaymentError(f"Failed to get payment summary: {str(e)}")
    finally:
        if conn:
            conn.close()