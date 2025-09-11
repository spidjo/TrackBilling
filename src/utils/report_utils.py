import logging
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, 
    Table, TableStyle, PageBreak, Image,
    ListFlowable, ListItem
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from db.database import get_db_connection
from datetime import datetime, timedelta
import io
import os
import time
from functools import lru_cache
from typing import Optional, Tuple, List, Dict, Any
import hashlib

# Constants
COMPANY_LOGO_PATH = "assets/logo.png"
PRIMARY_COLOR = colors.HexColor("#3a7bd5")
SECONDARY_COLOR = colors.HexColor("#00d2ff")
ACCENT_COLOR = colors.HexColor("#f5a623")
LIGHT_GRAY = colors.HexColor("#f5f5f5")
DARK_GRAY = colors.HexColor("#333333")
FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
PAGE_MARGINS = inch/2
TABLE_GRID_COLOR = colors.HexColor("#dddddd")
MAX_RETRIES = 3
RETRY_DELAY = 1

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = logging.FileHandler('billing_reports.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Register fonts
try:
    pdfmetrics.registerFont(TTFont('Helvetica', 'Helvetica.ttf'))
    pdfmetrics.registerFont(TTFont('Helvetica-Bold', 'Helvetica-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('Helvetica-Oblique', 'Helvetica-Oblique.ttf'))
except:
    logger.warning("Custom fonts not found, using default fonts")

class ReportGenerationError(Exception):
    """Custom exception for report generation failures"""
    pass

class DatabaseConnectionError(Exception):
    """Custom exception for database connection issues"""
    pass

def retry_on_failure(func):
    """Decorator for retrying failed operations"""
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}")
                time.sleep(RETRY_DELAY * (attempt + 1))
        raise last_exception if last_exception else Exception("Unknown error in retry decorator")
    return wrapper

@lru_cache(maxsize=128)
@retry_on_failure
def get_tenant_info(tenant_id: int) -> Optional[Tuple[str, str]]:
    """Get cached tenant information with retry logic
    
    Args:
        tenant_id: ID of the tenant to fetch information for
        
    Returns:
        Tuple of (tenant_name, billing_contact) or None if not found
        
    Raises:
        DatabaseConnectionError: If database connection fails after retries
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, billing_contact, address FROM tenants WHERE id = %s", 
            (tenant_id,)
        )
        result = cursor.fetchone()
        if not result:
            logger.warning(f"No tenant found with ID {tenant_id}")
            return None
        return result
    except Exception as e:
        logger.error(f"Error fetching tenant info: {e}")
        raise DatabaseConnectionError(f"Failed to fetch tenant info: {e}")
    finally:
        if conn:
            conn.close()

def create_pdf_styles() -> Dict[str, ParagraphStyle]:
    """Create and return a dictionary of custom PDF styles"""
    styles = getSampleStyleSheet()
    
    # Add custom styles
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=PRIMARY_COLOR,
        fontName=FONT_BOLD
    ))
    
    styles.add(ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=20,
        spaceAfter=10,
        textColor=DARK_GRAY,
        fontName=FONT_BOLD,
        underlineWidth=1,
        underlineColor=SECONDARY_COLOR,
        underlineOffset=-6
    ))
    
    styles.add(ParagraphStyle(
        name="Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER,
        spaceBefore=10
    ))
    
    styles.add(ParagraphStyle(
        name="Highlight",
        parent=styles["Normal"],
        fontSize=10,
        textColor=ACCENT_COLOR,
        backColor=LIGHT_GRAY,
        borderPadding=(5, 5, 5, 5),
        fontName=FONT_BOLD
    ))
    
    styles.add(ParagraphStyle(
        name="Disclaimer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceBefore=15
    ))
    
    return styles

def add_report_header(elements: List[Any], styles: Dict[str, ParagraphStyle], 
                    title: str, subtitle: str = None, logo_path: str = None) -> None:
    """Add a professional header to the report"""
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=2*inch, height=0.5*inch)
            elements.append(logo)
            elements.append(Spacer(1, 10))
        except Exception as e:
            logger.warning(f"Could not add logo: {e}")
    
    elements.append(Paragraph(title, styles["ReportTitle"]))
    
    if subtitle:
        elements.append(Paragraph(subtitle, styles["Normal"]))
    
    elements.append(Spacer(1, 15))
    elements.append(Spacer(1, 1))

def add_report_footer(elements: List[Any], styles: Dict[str, ParagraphStyle]) -> None:
    """Add a standardized footer to the report"""
    footer_text = f"Confidential - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} - Page <page>"
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(footer_text, styles["Footer"]))

def create_metrics_table(data: List[List[Any]], col_widths: List[float] = None, 
                        header_color: colors.Color = PRIMARY_COLOR) -> Table:
    """Create a styled metrics table with consistent formatting"""
    if not col_widths:
        col_widths = [200] * len(data[0]) if data else []
    
    table = Table(data, colWidths=col_widths, hAlign='LEFT')
    
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, TABLE_GRID_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, colors.white]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ])
    
    table.setStyle(style)
    return table

def validate_dates(start_date: datetime, end_date: datetime) -> None:
    """Validate that dates are in correct order and reasonable"""
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        raise ValueError("Both start_date and end_date must be datetime objects")
    
    if start_date > end_date:
        raise ValueError("Start date cannot be after end date")

    if start_date.year < 2000 or (end_date - timedelta(days=1) > datetime.now()):
        print(f"Start date: {start_date.year}, End date: {end_date}, Now: {datetime.now()}")
        raise ValueError("Dates must be between 2000 and current date")

def generate_tenant_billing_report_pdf(tenant_id: int, start_date: datetime, 
                                     end_date: datetime) -> Optional[bytes]:
    """
    Generate an optimized tenant-specific billing report with professional formatting
    
    Args:
        tenant_id: ID of the tenant to generate report for
        start_date: Start date of the reporting period
        end_date: End date of the reporting period
        
    Returns:
        PDF bytes if successful, None otherwise
        
    Raises:
        ReportGenerationError: If report generation fails
    """
    logger.info(f"Generating billing report for tenant {tenant_id} from {start_date} to {end_date}")
    
    try:
        validate_dates(start_date, end_date)
        
        # Get tenant info (uses cache and retry)
        tenant_info = get_tenant_info(tenant_id)
        if not tenant_info:
            logger.error(f"No tenant found with ID {tenant_id}")
            raise ReportGenerationError(f"Tenant not found: {tenant_id}")
            
        tenant_name, contact, address = tenant_info
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Get data from database
        data = fetch_tenant_billing_data(tenant_id, start_str, end_str)
        if not data:
            logger.warning(f"No invoice data found for tenant {tenant_id}")
            raise ReportGenerationError("No data available for the selected period")
            
        invoice_count, total_billed, total_paid, avg_invoice = data
        
        # Get additional metrics
        active_users = fetch_active_users_count(tenant_id, start_str, end_str)
        outstanding = total_billed - total_paid
        arpu = total_billed / active_users if active_users else 0
        
        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=PAGE_MARGINS,
            leftMargin=PAGE_MARGINS,
            topMargin=PAGE_MARGINS,
            bottomMargin=PAGE_MARGINS
        )
        
        styles = create_pdf_styles()
        elements = []
        
        # Add header
        add_report_header(
            elements,
            styles,
            title=f"{tenant_name} - Billing Report",
            subtitle=f"Period: {start_str} to {end_str}",
            logo_path=COMPANY_LOGO_PATH
        )
        
        # Add tenant info section
        elements.append(Paragraph("Tenant Information", styles["SectionHeader"]))
        tenant_info_data = [
            ["Tenant Name:", tenant_name],
            ["Billing Contact:", contact],
            ["Billing Address:", address],
            ["Report Period:", f"{start_str} to {end_str}"]
        ]
        elements.append(create_metrics_table(tenant_info_data, [150, 300]))
        elements.append(Spacer(1, 20))
        
        # Key metrics section
        elements.append(Paragraph("Billing Summary", styles["SectionHeader"]))
        
        metrics = [
            ["Metric", "Value", "Notes"],
            ["Total Invoices", invoice_count, "All issued invoices"],
            ["Total Billed", f"R{total_billed:,.2f}", "Gross amount"],
            ["Total Paid", f"R{total_paid:,.2f}", "Received payments"],
            ["Outstanding", f"R{outstanding:,.2f}", "Pending collection"],
            ["Avg. Invoice", f"R{avg_invoice:,.2f}" if avg_invoice else "N/A", "Mean invoice value"],
            ["Active Users", active_users, "Users with activity"],
            ["ARPU", f"R{arpu:,.2f}" if active_users else "N/A", "Revenue per user"]
        ]
        
        elements.append(create_metrics_table(metrics, [150, 100, 150]))
        elements.append(Spacer(1, 20))
        
        # Add payment status visualization
        payment_status_data = [
            ["Status", "Amount", "Percentage"],
            ["Paid", f"R{total_paid:,.2f}", f"{(total_paid/total_billed)*100:.1f}%" if total_billed else "0%"],
            ["Outstanding", f"R{outstanding:,.2f}", f"{(outstanding/total_billed)*100:.1f}%" if total_billed else "0%"]
        ]
        
        elements.append(Paragraph("Payment Status", styles["SectionHeader"]))
        payment_table = create_metrics_table(payment_status_data, [200, 100, 100])
        
        # Add conditional coloring for outstanding amounts
        outstanding_style = TableStyle([
            ("TEXTCOLOR", (1, 2), (1, 2), ACCENT_COLOR if outstanding > 0 else colors.green),
            ("FONTNAME", (1, 2), (1, 2), FONT_BOLD if outstanding > 0 else FONT_NAME)
        ])
        payment_table.setStyle(outstanding_style)
        elements.append(payment_table)
        
        # Add disclaimer
        disclaimer_text = ("*Note: This report is generated automatically. "
                         "Please contact support with any discrepancies.")
        elements.append(Paragraph(disclaimer_text, styles["Disclaimer"]))
        
        # Add footer
        add_report_footer(elements, styles)
        
        # Build document
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        
        if not pdf_bytes:
            logger.error("Generated PDF is empty")
            raise ReportGenerationError("PDF generation failed - empty output")
            
        logger.info(f"Successfully generated PDF report for tenant {tenant_id}")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error generating PDF report: {str(e)}", exc_info=True)
        raise ReportGenerationError(f"Failed to generate report: {str(e)}")
    finally:
        if 'buffer' in locals() and buffer:
            buffer.close()

@retry_on_failure
def fetch_tenant_billing_data(tenant_id: int, start_date: str, end_date: str) -> Optional[Tuple[int, float, float, float]]:
    """Fetch billing data for a tenant with retry logic"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(id) AS invoice_count,
                COALESCE(SUM(total_invoiced), 0) AS total_billed,
                COALESCE(SUM(CASE WHEN is_paid THEN total_invoiced ELSE 0 END), 0) AS total_paid,
                AVG(total_invoiced) AS avg_invoice
            FROM invoices
            WHERE user_id IN (SELECT id FROM users WHERE tenant_id = %s)
            AND invoice_date BETWEEN %s AND %s
        """, (tenant_id, start_date, end_date))
        
        result = cursor.fetchone()
        return result if result else None
    except Exception as e:
        logger.error(f"Error fetching billing data: {e}")
        raise DatabaseConnectionError(f"Failed to fetch billing data: {e}")
    finally:
        if conn:
            conn.close()

@retry_on_failure
def fetch_active_users_count(tenant_id: int, start_date: str, end_date: str) -> int:
    """Fetch active users count with retry logic"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM usage_records
            WHERE user_id IN (SELECT id FROM users WHERE tenant_id = %s)
            AND usage_date BETWEEN %s AND %s
        """, (tenant_id, start_date, end_date))
        
        return cursor.fetchone()[0] or 0
    except Exception as e:
        logger.error(f"Error fetching active users: {e}")
        raise DatabaseConnectionError(f"Failed to fetch active users: {e}")
    finally:
        if conn:
            conn.close()

def generate_superadmin_pdf_report(start_date: datetime, end_date: datetime, 
                                 tenant_filter: Optional[List[str]] = None) -> Optional[bytes]:
    """
    Generate comprehensive cross-tenant report with professional formatting
    
    Args:
        start_date: Start date of reporting period
        end_date: End date of reporting period
        tenant_filter: Optional list of tenant IDs to filter by
        
    Returns:
        PDF bytes if successful, None otherwise
        
    Raises:
        ReportGenerationError: If report generation fails
    """
    start_time = time.time()
    logger.info(f"Generating superadmin report from {start_date} to {end_date}")
    
    try:
        validate_dates(start_date, end_date)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Fetch tenant data
        tenants_data = fetch_tenants_billing_data(start_str, end_str, tenant_filter)
        if not tenants_data:
            logger.warning("No tenant data found for the given period")
            raise ReportGenerationError("No data available for the selected period")
            
        # Calculate summary stats
        total_invoices = sum(t[2] for t in tenants_data)
        total_billed = sum(t[3] for t in tenants_data)
        total_paid = sum(t[4] for t in tenants_data)
        avg_revenue = total_billed / len(tenants_data) if tenants_data else 0
        
        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=PAGE_MARGINS,
            leftMargin=PAGE_MARGINS,
            topMargin=PAGE_MARGINS,
            bottomMargin=PAGE_MARGINS,
            title="SAAS Billing Analytics Report"
        )
        
        styles = create_pdf_styles()
        elements = []
        
        # Add header
        add_report_header(
            elements,
            styles,
            title="SAAS BILLING ANALYTICS DASHBOARD",
            subtitle=f"Period: {start_str} to {end_str} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            logo_path=COMPANY_LOGO_PATH
        )
        
        # Executive Summary
        elements.append(Paragraph("Executive Summary", styles["SectionHeader"]))
        
        summary_data = [
            ["Total Tenants", len(tenants_data)],
            ["Total Invoices", total_invoices],
            ["Total Billed", f"R{total_billed:,.2f}"],
            ["Total Paid", f"R{total_paid:,.2f}"],
            ["Collection Rate", f"{(total_paid/total_billed)*100:.1f}%" if total_billed else "0%"],
            ["Avg. Revenue per Tenant", f"R{avg_revenue:,.2f}"]
        ]
        
        elements.append(create_metrics_table(summary_data, [200, 150]))
        elements.append(Spacer(1, 30))
        
        # Tenant Performance Breakdown
        elements.append(Paragraph("Tenant Performance", styles["SectionHeader"]))
        
        # Add visualization of top performers
        top_performers = sorted(tenants_data, key=lambda x: x[3], reverse=True)[:5]
        if top_performers:
            elements.append(Paragraph("Top 5 Tenants by Revenue", styles["Heading3"]))
            
            performers_data = [["Tenant", "Revenue", "% of Total"]]
            for tenant in top_performers:
                performers_data.append([
                    tenant[1],
                    f"R{tenant[3]:,.2f}",
                    f"{(tenant[3]/total_billed)*100:.1f}%" if total_billed else "0%"
                ])
            
            elements.append(create_metrics_table(performers_data, [250, 100, 100]))
            elements.append(Spacer(1, 20))
        
        # Detailed Tenant Reports
        for idx, tenant in enumerate(tenants_data):
            tenant_id, name, invoices, billed, paid, users = tenant
            
            # Tenant header with page break if not first tenant
            if idx > 0:
                elements.append(PageBreak())
                
            elements.append(Paragraph(name, styles["SectionHeader"]))
            
            # Key metrics
            metrics = [
                ["Metric", "Value", "Percentage"],
                ["Invoices", invoices, f"{(invoices/total_invoices)*100:.1f}%" if total_invoices else "0%"],
                ["Amount Billed", f"R{billed:,.2f}", f"{(billed/total_billed)*100:.1f}%" if total_billed else "0%"],
                ["Amount Paid", f"R{paid:,.2f}", f"{(paid/billed)*100:.1f}%" if billed else "0%"],
                ["Collection Rate", f"{(paid/billed)*100:.1f}%" if billed else "N/A", ""],
                ["Active Users", users, f"{(users/sum(t[5] for t in tenants_data))*100:.1f}%" if sum(t[5] for t in tenants_data) else "0%"]
            ]
            
            table = create_metrics_table(metrics, [150, 100, 100])
            
            # Add conditional formatting for collection rate
            collection_rate = (paid/billed) if billed else 0
            rate_style = TableStyle([
                ("TEXTCOLOR", (1, 3), (1, 3), 
                colors.green if collection_rate >= 0.9 
                else ACCENT_COLOR if collection_rate >= 0.7 
                else colors.red),
                ("FONTNAME", (1, 3), (1, 3), FONT_BOLD)
            ])
            table.setStyle(rate_style)
            
            elements.append(table)
            
            # Add notes section
            elements.append(Spacer(1, 15))
            notes = [
                f"Tenant represents {(billed/total_billed)*100:.1f}% of total revenue" if total_billed else "New tenant with no revenue",
                f"Collection rate is {'above' if collection_rate >= 0.9 else 'below'} average" if billed else "No billing data"
            ]
            
            bullet_points = ListFlowable(
                [ListItem(Paragraph(note, styles["Normal"])) for note in notes],
                bulletType='bullet',
                leftIndent=20
            )
            elements.append(bullet_points)
        
        # Add footer
        add_report_footer(elements, styles)
        
        # Build document
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        
        if not pdf_bytes:
            logger.error("Generated PDF is empty")
            raise ReportGenerationError("PDF generation failed - empty output")
            
        logger.info(f"Report generated in {time.time() - start_time:.2f} seconds")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error generating superadmin report: {str(e)}", exc_info=True)
        raise ReportGenerationError(f"Failed to generate report: {str(e)}")
    finally:
        if 'buffer' in locals() and buffer:
            buffer.close()

@retry_on_failure
def fetch_tenants_billing_data(start_date: str, end_date: str, 
                              tenant_filter: Optional[List[str]] = None) -> List[Tuple]:
    """Fetch billing data for all tenants with retry logic"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Base query with optional tenant filter
        query = """
            SELECT t.id, t.name,
                COUNT(DISTINCT i.id) AS invoice_count,
                COALESCE(SUM(i.total_invoiced), 0) AS total_billed,
                COALESCE(SUM(CASE WHEN i.is_paid THEN i.total_invoiced ELSE 0 END), 0) AS paid_amount,
                COUNT(DISTINCT u.id) AS user_count
            FROM tenants t
            LEFT JOIN users u ON u.tenant_id = t.id
            LEFT JOIN invoices i ON i.user_id = u.id AND i.invoice_date BETWEEN %s AND %s
        """
        
        params = [start_date, end_date]
        
        if tenant_filter:
            try:
                tenant_ids = [int(t.split("ID: ")[1].rstrip(")")) for t in tenant_filter]
                query += " WHERE t.id IN %s"
                params.append(tuple(tenant_ids))
                logger.debug(f"Filtering for tenant IDs: {tenant_ids}")
            except Exception as e:
                logger.error(f"Error parsing tenant filter: {e}")
                raise ValueError("Invalid tenant filter format")
        
        query += " GROUP BY t.id, t.name ORDER BY total_billed DESC"
        
        cursor.execute(query, params)
        return cursor.fetchall()
        
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise DatabaseConnectionError(f"Failed to fetch tenants data: {e}")
    finally:
        if conn:
            conn.close()