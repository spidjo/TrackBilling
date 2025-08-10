from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib import colors
import os
from datetime import datetime

def generate_pdf_invoice(invoice_details, save_path="invoices"):
    """
    Generates a professional PDF invoice with all details
    Args:
        invoice_details (dict): Dictionary containing all invoice details from get_invoice_details()
        save_path (str): Directory to save the PDF (default: "invoices")
    Returns:
        str: Path to the generated PDF file
    Raises:
        ValueError: If invoice_details is invalid or missing required fields
        IOError: If there are file system errors
    """
    try:
        # Validate input data structure
        if not invoice_details or not isinstance(invoice_details, dict):
            raise ValueError("Invalid invoice details: Expected dictionary")
        
        # Check for required fields
        required_fields = [
            'invoice_id', 'invoice_number', 'invoice_date', 'due_date',
            'payment_status', 'tenant', 'customer', 'items', 'subtotal',
            'total_amount'
        ]
        for field in required_fields:
            if field not in invoice_details:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate nested structures
        if not isinstance(invoice_details['items'], list):
            raise ValueError("Invoice items must be a list")
        
        # Create output directory if it doesn't exist
        os.makedirs(save_path, exist_ok=True)
        
        # Generate file path
        file_path = os.path.join(save_path, f"invoice_{invoice_details['invoice_id']}.pdf")
        
        # Create PDF canvas with error handling
        try:
            c = canvas.Canvas(file_path, pagesize=letter)
            width, height = letter
            
            # [Rest of your PDF generation code remains the same...]
            # Header
            c.setFont("Helvetica-Bold", 18)
            c.drawString(50, height-50, "INVOICE")
            
            # Invoice info
            c.setFont("Helvetica", 10)
            c.drawRightString(width-50, height-50, f"Invoice #: {invoice_details['invoice_number']}")
            c.drawRightString(width-50, height-70, f"Date: {invoice_details['invoice_date']}")
            c.drawRightString(width-50, height-90, f"Due Date: {invoice_details['due_date']}")
            c.drawRightString(width-50, height-110, f"Status: {invoice_details['payment_status']}")
            
            # [Continue with all your existing layout code...]
            
            # Save the PDF
            c.save()
            
            # Update database status
            update_pdf_generated_status(invoice_details['invoice_id'])
            
            return file_path
            
        except Exception as canvas_error:
            # Clean up partially created file
            if os.path.exists(file_path):
                os.remove(file_path)
            raise Exception(f"PDF generation failed: {str(canvas_error)}")
            
    except Exception as e:
        # Convert all exceptions to a consistent error message
        raise Exception(f"Failed to generate PDF invoice: {str(e)}")

def update_pdf_generated_status(invoice_id):
    """Updates the database to mark invoice as PDF generated"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE invoices 
            SET pdf_generated = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (invoice_id,))
        conn.commit()
    except Exception as e:
        # Don't fail the whole operation if status update fails
        print(f"Warning: Could not update PDF status for invoice {invoice_id}: {str(e)}")
    finally:
        if conn:
            conn.close()