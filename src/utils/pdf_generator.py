from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import os.path
from datetime import datetime

def generate_pdf_invoice(invoice_details, tenant_id = None):
    """
    Generates a professional PDF invoice with all details and returns PDF bytes
    Args:
        invoice_details (dict): Dictionary containing all invoice details from get_invoice_details()
        tenant_id (int): The ID of the tenant for branding purposes
    Returns:
        bytes: PDF file content as bytes 
    Raises:
        ValueError: If invoice_details is invalid or missing required fields
    """
    # Validate input data structure
    if not invoice_details or not isinstance(invoice_details, dict):
        raise ValueError("Invalid invoice details: Expected dictionary")
    
    # Check for required fields
    required_fields = [
        'invoice_id', 'invoice_number', 'invoice_date', 'due_date',
        'payment_status', 'tenant', 'customer', 'items', 'subtotal',
        'total_invoiced'
    ]
    for field in required_fields:
        if field not in invoice_details:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate nested structures
    if not isinstance(invoice_details['items'], list):
        raise ValueError("Invoice items must be a list")
    
    # Create a bytes buffer for the PDF
    buffer = io.BytesIO()
    
    try:
        # Create PDF canvas with larger margins
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Set up styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1,  # centered
            spaceAfter=20,
            textColor=colors.HexColor("#2c3e50")
        )
        
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor("#3498db"),
            spaceAfter=10
        )
        
        # Add company logo (if available)
        try:
            logo_path = f"assets/{tenant_id}.png"  # Example path
            if os.path.exists(logo_path):
                c.drawImage(logo_path, 50, height-80, width=2*inch, height=0.5*inch, preserveAspectRatio=True)
        except:
            pass  # Logo is optional
        
        # Invoice title and header
        title = Paragraph("TAX INVOICE", title_style)
        title.wrapOn(c, width-100, height)
        title.drawOn(c, 50, height-100)
        
        # Draw a line under the title
        c.setStrokeColor(colors.HexColor("#3498db"))
        c.setLineWidth(1)
        c.line(50, height-110, width-50, height-110)
        
        # Invoice info in two columns
        right_column_x = width - 50
        label_x = right_column_x - 150  # Space for labels
        value_x = right_column_x - 10   # Space for values
        
        # Set consistent vertical positions
        y_position = height - 130
        line_height = 20
        
        # Draw labels and values in proper columns
        c.setFont("Helvetica-Bold", 10)
        c.drawString(label_x, y_position, "Invoice Number:")
        c.setFont("Helvetica", 10)
        c.drawString(value_x, y_position, invoice_details['invoice_number'])
        
        y_position -= line_height
        c.setFont("Helvetica-Bold", 10)
        c.drawString(label_x, y_position, "Invoice Date:")
        c.setFont("Helvetica", 10)
        c.drawString(value_x, y_position, invoice_details['invoice_date'])
        
        y_position -= line_height
        c.setFont("Helvetica-Bold", 10)
        c.drawString(label_x, y_position, "Due Date:")
        c.setFont("Helvetica", 10)
        c.drawString(value_x, y_position, invoice_details['due_date'])
        
        y_position -= line_height
        c.setFont("Helvetica-Bold", 10)
        c.drawString(label_x, y_position, "Status:")
        # Color-code status
        status_color = colors.green if invoice_details['payment_status'] == "Paid" else colors.red
        c.setFillColor(status_color)
        c.drawString(value_x, y_position, invoice_details['payment_status'])
        c.setFillColor(colors.black)
        
        # Company and customer info with better formatting
        from_section = Paragraph("<b>FROM:</b><br/>" + 
                               f"{invoice_details['tenant']['name']}<br/>" +
                               (f"{invoice_details['tenant']['company_name']}<br/>" if invoice_details['tenant']['company_name'] else "") +
                               f"{invoice_details['tenant']['address']}<br/>" +
                               f"{invoice_details['tenant']['email']}<br/>" +
                               (f"Phone: {invoice_details['tenant']['phone']}<br/>" if invoice_details['tenant']['phone'] else ""),
                               styles['Normal'])
        
        to_section = Paragraph("<b>TO:</b><br/>" + 
                             f"{invoice_details['customer']['name']}<br/>" +
                             (f"{invoice_details['customer']['company_name']}<br/>" if invoice_details['customer']['company_name'] else "") +
                             f"{invoice_details['customer']['email']}",
                             styles['Normal'])
        
        from_section.wrapOn(c, width/2-60, height)
        from_section.drawOn(c, 50, height-280)
        
        to_section.wrapOn(c, width/2-60, height)
        to_section.drawOn(c, width/2, height-280)
        
        # Invoice items table with improved styling
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height-320, "ITEMIZED CHARGES")
        
        # Table data with more professional formatting
        data = [
            ["DESCRIPTION", "QTY", "UNIT PRICE", "AMOUNT"]
        ]
        for item in invoice_details['items']:
            data.append([
                item['description'],
                str(item['quantity']),
                f"R {item['unit_price']:,.2f}",
                f"R {item['total_price']:,.2f}"
            ])
        
        # Create table with professional styling
        table = Table(data, colWidths=[280, 50, 90, 90], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        # Draw table
        table.wrapOn(c, width-100, height)
        table.drawOn(c, 50, height-420)
        
        # Totals section with better formatting
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(width-140, height-470, "SUBTOTAL:")
        if 'tax_amount' in invoice_details and invoice_details['tax_amount'] > 0:
            c.drawRightString(width-140, height-490, "TAX:")
        c.drawRightString(width-140, height-510, "TOTAL:")
        
        c.setFont("Helvetica", 10)
        c.drawRightString(width-50, height-470, f"R {invoice_details['subtotal']:,.2f}")
        if 'tax_amount' in invoice_details and invoice_details['tax_amount'] > 0:
            c.drawRightString(width-50, height-490, f"R {invoice_details['tax_amount']:,.2f}")
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width-50, height-510, f"R {invoice_details['total_invoiced']:,.2f}")

        # Payment terms and footer
        c.setFont("Helvetica", 8)
        c.drawString(50, 100, "Payment Terms:")
        c.setFont("Helvetica", 8)
        c.drawString(50, 85, "Payment due within 30 days of invoice date. Late payments subject to interest.")
        
        # Footer with company info
        footer_text = (f"{invoice_details['tenant']['name']} | {invoice_details['tenant']['address']} | "
                      f"Phone: {invoice_details['tenant']['phone'] or 'N/A'} | "
                      f"Email: {invoice_details['tenant']['email']}")
        c.setFont("Helvetica", 7)
        c.drawCentredString(width/2, 30, footer_text)
        
        # Page number
        c.setFont("Helvetica", 7)
        c.drawRightString(width-50, 30, "Page 1 of 1")
        
        # Save the PDF to buffer
        c.save()
        
        # Get the PDF bytes from buffer
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        buffer.close()
        raise Exception(f"PDF generation failed: {str(e)}")

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