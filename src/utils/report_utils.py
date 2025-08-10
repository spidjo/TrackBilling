from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, 
    Table, TableStyle, PageBreak, Image
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from db.database import get_db_connection
from datetime import datetime
import io
import os
import time
from functools import lru_cache

# Cache tenant data for better performance
@lru_cache(maxsize=32)
def get_tenant_info(tenant_id):
    """Get cached tenant information"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, billing_contact FROM tenants WHERE id = %s", (tenant_id,))
        return cursor.fetchone()
    finally:
        conn.close()

def generate_superadmin_pdf_report(start_date, end_date, tenant_filter=None):
    """Generate comprehensive cross-tenant report with optimizations"""
    start_time = time.time()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Convert dates
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Base query with optional tenant filter
        tenant_condition = ""
        params = [start_str, end_str]
        if tenant_filter:
            tenant_ids = [int(t.split("ID: ")[1].rstrip(")")) for t in tenant_filter]
            tenant_condition = "AND t.id IN %s"
            params.append(tuple(tenant_ids))
        
        # Optimized tenant summary query
        cursor.execute(f"""
            SELECT t.id, t.name,
                COUNT(DISTINCT i.id) AS invoice_count,
                COALESCE(SUM(i.total_amount), 0) AS total_billed,
                COALESCE(SUM(CASE WHEN i.is_paid THEN i.total_amount ELSE 0 END), 0) AS paid_amount,
                COUNT(DISTINCT u.id) AS user_count
            FROM tenants t
            LEFT JOIN users u ON u.tenant_id = t.id
            LEFT JOIN invoices i ON i.user_id = u.id AND i.invoice_date BETWEEN %s AND %s
            WHERE 1=1 {tenant_condition}
            GROUP BY t.id, t.name
            ORDER BY total_billed DESC
        """, params)
        
        tenants = cursor.fetchall()
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=inch/2, leftMargin=inch/2,
                              topMargin=inch/2, bottomMargin=inch/2)
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Add custom styles
        styles.add(ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=16,
            spaceAfter=12,
            alignment=1
        ))
        
        # Header
        elements.append(Paragraph("SAAS BILLING ANALYTICS DASHBOARD", styles["ReportTitle"]))
        elements.append(Paragraph(
            f"Period: {start_str} to {end_str} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 20))
        
        # Summary Stats
        summary_data = [
            ["Total Tenants", len(tenants)],
            ["Total Invoices", sum(t[2] for t in tenants)],
            ["Total Billed", f"R{sum(t[3] for t in tenants):,.2f}"],
            ["Total Paid", f"R{sum(t[4] for t in tenants):,.2f}"],
            ["Avg. Revenue per Tenant", f"R{sum(t[3] for t in tenants)/len(tenants):,.2f}" if tenants else "R0.00"]
        ]
        
        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3a7bd5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 30))
        
        # Tenant Details
        for idx, tenant in enumerate(tenants):
            tenant_id, name, invoices, billed, paid, users = tenant
            
            # Tenant header with optional logo
            elements.append(Paragraph(name, styles["Heading2"]))
            
            # Key metrics table
            metrics = [
                ["Metric", "Value", "Percentage"],
                ["Invoices", invoices, f"{(invoices/sum(t[2] for t in tenants))*100:.1f}%" if sum(t[2] for t in tenants) else "0%"],
                ["Amount Billed", f"R{billed:,.2f}", f"{(billed/sum(t[3] for t in tenants))*100:.1f}%" if sum(t[3] for t in tenants) else "0%"],
                ["Amount Paid", f"R{paid:,.2f}", f"{(paid/billed)*100:.1f}%" if billed else "0%"],
                ["Active Users", users, ""]
            ]
            
            tenant_table = Table(metrics, colWidths=[150, 100, 100])
            tenant_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]))
            
            elements.append(tenant_table)
            elements.append(Spacer(1, 15))
            
            # Add page break every 3 tenants
            if (idx + 1) % 3 == 0 and idx < len(tenants) - 1:
                elements.append(PageBreak())
        
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        
        print(f"Report generated in {time.time() - start_time:.2f} seconds")
        return pdf_bytes
        
    finally:
        conn.close()
        buffer.close()

def generate_tenant_billing_report_pdf(tenant_id, start_date, end_date):
    """Generate optimized tenant-specific billing report"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get tenant info (uses cache)
        tenant_name, contact = get_tenant_info(tenant_id)
        
        # Convert dates
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Get invoice summary
        cursor.execute("""
            SELECT 
                COUNT(id),
                COALESCE(SUM(total_amount), 0),
                COALESCE(SUM(CASE WHEN is_paid THEN total_amount ELSE 0 END), 0),
                AVG(total_amount)
            FROM invoices
            WHERE user_id IN (SELECT id FROM users WHERE tenant_id = %s)
            AND invoice_date BETWEEN %s AND %s
        """, (tenant_id, start_str, end_str))
        invoice_count, total_billed, total_paid, avg_invoice = cursor.fetchone()
        
        # Get user metrics
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM usage_records
            WHERE user_id IN (SELECT id FROM users WHERE tenant_id = %s)
            AND usage_date BETWEEN %s AND %s
        """, (tenant_id, start_str, end_str))
        active_users = cursor.fetchone()[0] or 0
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        
        # Header
        elements.append(Paragraph(f"{tenant_name} Billing Report", styles["Title"]))
        elements.append(Paragraph(f"Period: {start_str} to {end_str}", styles["Normal"]))
        elements.append(Spacer(1, 20))
        
        # Key metrics
        metrics = [
            ["Metric", "Value"],
            ["Total Invoices", invoice_count],
            ["Total Billed", f"R{total_billed:,.2f}"],
            ["Total Paid", f"R{total_paid:,.2f}"],
            ["Outstanding", f"R{total_billed - total_paid:,.2f}"],
            ["Avg. Invoice", f"R{avg_invoice:,.2f}" if avg_invoice else "N/A"],
            ["Active Users", active_users],
            ["ARPU", f"R{total_billed/active_users:,.2f}" if active_users else "N/A"]
        ]
        
        table = Table(metrics, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3a7bd5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        
        elements.append(table)
        doc.build(elements)
        return buffer.getvalue()
        
    finally:
        conn.close()
        buffer.close()