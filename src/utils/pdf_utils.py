# src/utils/pdf_utils.py
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Table, TableStyle, SimpleDocTemplate, 
    Paragraph, Spacer, Image, PageBreak,
    Frame, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from io import BytesIO
import os
from datetime import datetime
import logging
from typing import Dict, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFGenerationError(Exception):
    """Custom exception for PDF generation failures"""
    pass

def _safe_get(dictionary: Dict, key: str, default: str = "") -> str:
    """Safely get a value from dictionary with null checking"""
    value = dictionary.get(key, default)
    return str(value) if value is not None else default

def _create_custom_styles() -> Dict[str, ParagraphStyle]:
    """Create custom styles for the PDF document"""
    styles = getSampleStyleSheet()
    
    # Add custom styles
    styles.add(ParagraphStyle(
        name='InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.HexColor("#2c3e50")
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        leading=14,
        spaceAfter=6,
        textColor=colors.HexColor("#3498db")
    ))
    
    styles.add(ParagraphStyle(
        name='FooterText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor("#7f8c8d")
    ))
    
    styles.add(ParagraphStyle(
        name='TotalAmount',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor("#27ae60"),
        alignment=TA_RIGHT
    ))
    
    return styles

def _validate_input_data(invoice: Dict, items: List[Dict]) -> None:
    """Validate input data before PDF generation"""
    if not isinstance(invoice, dict):
        raise ValueError("Invoice data must be a dictionary")
    if not isinstance(items, list):
        raise ValueError("Items must be a list of dictionaries")
    
    required_invoice_fields = ['id', 'invoice_date', 'total_invoiced']
    for field in required_invoice_fields:
        if field not in invoice:
            raise ValueError(f"Missing required invoice field: {field}")
    
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx} must be a dictionary")
        if 'description' not in item:
            raise ValueError(f"Item {idx} is missing description")
        if 'quantity' not in item:
            raise ValueError(f"Item {idx} is missing quantity")
        if 'unit_price' not in item:
            raise ValueError(f"Item {idx} is missing unit_price")

def _create_header(styles: Dict, tenant_info: Dict, logo_path: Optional[str] = None) -> Table:
    """Create the invoice header with optional logo"""
    header_data = []
    
    # Left column - Logo or empty space
    left_col = ""
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=50*mm, height=20*mm)
            left_col = logo
        except Exception as e:
            logger.warning(f"Failed to load logo: {e}")
    
    # Right column - Tenant info with null checks
    tenant_name = _safe_get(tenant_info, 'name', 'Tenant Name')
    tenant_address = _safe_get(tenant_info, 'address', 'Address not provided')
    
    contact_parts = []
    if 'email' in tenant_info and tenant_info['email']:
        contact_parts.append(_safe_get(tenant_info, 'email'))
    if 'phone' in tenant_info and tenant_info['phone']:
        contact_parts.append(_safe_get(tenant_info, 'phone'))
    
    right_col = Paragraph(
        f"<b>{tenant_name}</b><br/>"
        f"{tenant_address}<br/>"
        f"{'<br/>'.join(contact_parts) if contact_parts else ''}",
        styles['Normal']
    )
    
    header_data.append([left_col, right_col])
    
    return Table(
        header_data, 
        colWidths=[60*mm, 110*mm],
        style=[
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12)
        ]
    )

def _create_client_info(styles: Dict, client_info: Dict) -> Paragraph:
    """Create client information section with null checks"""
    client_name = _safe_get(client_info, 'name', 'Client Name')
    client_address = _safe_get(client_info, 'address', 'Address not provided')
    client_email = _safe_get(client_info, 'email')
    
    return Paragraph(
        f"<b>Bill To:</b><br/>"
        f"{client_name}<br/>"
        f"{client_address}<br/>"
        f"{client_email if client_email else ''}",
        styles['Normal']
    )

def _create_invoice_metadata(styles: Dict, invoice: Dict) -> Paragraph:
    """Create invoice metadata section with null checks"""
    invoice_id = _safe_get(invoice, 'id', 'N/A')
    invoice_date = _safe_get(invoice, 'invoice_date', datetime.now().strftime('%Y-%m-%d'))
    period_start = _safe_get(invoice, 'period_start', invoice_date)
    period_end = _safe_get(invoice, 'period_end', invoice_date)
    
    return Paragraph(
        f"<b>Invoice #:</b> {invoice_id}<br/>"
        f"<b>Date:</b> {invoice_date}<br/>"
        f"<b>Period:</b> {period_start} to {period_end}",
        styles['Normal']
    )

def _create_items_table(styles: Dict, items: List[Dict]) -> Table:
    """Create the invoice items table with null checks"""
    table_data = [["Description", "Qty", "Unit Price", "Amount"]]
    
    for item in items:
        description = _safe_get(item, 'description', 'Item')
        quantity = item.get('quantity', 0)
        unit_price = float(item.get('unit_price', 0.00))
        amount = quantity * unit_price
        
        table_data.append([
            description,
            str(quantity),
            f"R{unit_price:.2f}",
            f"R{amount:.2f}"
        ])
    
    return Table(
        table_data, 
        colWidths=[200, 50, 70, 70],
        style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor("#3498db")),
        ]
    )

def generate_invoice_pdf(
    invoice: Dict,
    items: List[Dict],
    tenant_info: Optional[Dict] = None,
    client_info: Optional[Dict] = None,
    logo_path: Optional[str] = None
) -> BytesIO:
    """
    Generate a professional PDF invoice document with comprehensive error handling.
    
    Args:
        invoice: Dictionary containing invoice metadata
        items: List of dictionaries containing line items
        tenant_info: Dictionary containing tenant information
        client_info: Dictionary containing client information
        logo_path: Path to logo image file
        
    Returns:
        BytesIO buffer containing the PDF data
        
    Raises:
        PDFGenerationError: If PDF generation fails
        ValueError: If input data is invalid
    """
    try:
        # Initialize with safe defaults
        tenant_info = tenant_info or {}
        client_info = client_info or {}
        
        # Validate input data
        _validate_input_data(invoice, items)
        
        # Create buffer and document template
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=15*mm,
            rightMargin=15*mm,
            topMargin=20*mm,
            bottomMargin=15*mm,
            title=f"Invoice_{invoice.get('id', '')}"
        )
        
        # Create custom styles
        styles = _create_custom_styles()
        elements = []
        
        # Add title
        elements.append(Paragraph("INVOICE", styles['InvoiceTitle']))
        
        # Add header with logo and tenant info
        elements.append(_create_header(styles, tenant_info, logo_path))
        elements.append(Spacer(1, 12))
        
        # Create two-column layout for client info and invoice metadata
        col1 = _create_client_info(styles, client_info)
        col2 = _create_invoice_metadata(styles, invoice)
        
        two_col_table = Table(
            [[col1, col2]],
            colWidths=[100*mm, 80*mm],
            style=[
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 16)
            ]
        )
        elements.append(two_col_table)
        
        # Add items table
        elements.append(Paragraph("Invoice Items", styles['SectionHeader']))
        elements.append(_create_items_table(styles, items))
        elements.append(Spacer(1, 8))
        
        # Add total amount with null check
        total_amount = float(invoice.get('total_invoiced', 0.00))
        elements.append(Paragraph(
            f"<b>TOTAL: R{total_amount:.2f}</b>",
            styles['TotalAmount']
        ))
        elements.append(Spacer(1, 24))
        
        # Add footer
        elements.append(Paragraph(
            "<i>Thank you for your business. Please make payment to the account listed on your profile. "
            "For any questions, contact our support team.</i>",
            styles['FooterText']
        ))
        
        # Build the document
        doc.build(elements)
        buffer.seek(0)
        
        return buffer
        
    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")
        raise PDFGenerationError(f"Invalid input data: {ve}")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise PDFGenerationError(f"Failed to generate PDF: {str(e)}")