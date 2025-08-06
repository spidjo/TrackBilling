from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from db.database import get_db_connection
import io
import datetime
import os

def generate_superadmin_pdf_report(start_date, end_date):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Date conversion
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_obj = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date_obj = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
    prev_start = (start_date_obj - (end_date_obj - start_date_obj)).date()
    prev_end = (start_date_obj - datetime.timedelta(days=1)).date()

    # Tenant summary
    cursor.execute("""
        SELECT t.id, t.name,
            COUNT(DISTINCT i.id) AS total_invoices,
            COALESCE(SUM(i.total_amount), 0) AS total_billed,
            COALESCE(SUM(CASE WHEN i.is_paid = 1 THEN i.total_amount ELSE 0 END), 0) AS total_paid
        FROM tenants t
        LEFT JOIN users u ON u.tenant_id = t.id
        LEFT JOIN invoices i ON i.user_id = u.id
        WHERE i.invoice_date BETWEEN ? AND ?
        GROUP BY t.id, t.name
    """, (start_date_str, end_date_str))
    tenants = cursor.fetchall()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("📊 SuperAdmin SaaS Billing Summary", styles["Title"]))
    elements.append(Paragraph(f"<font size=10>Period: {start_date_str} to {end_date_str}</font>", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # Totals for summary row
    total_active = total_arpu = total_invoices = total_billed = total_paid = total_churned = 0
    total_metrics = {}

    for idx, (tenant_id, tenant_name, invoice_count, billed, paid) in enumerate(tenants):
        elements.append(Paragraph(f"🏢 Tenant: <b>{tenant_name}</b>", styles["Heading3"]))

        # Optional logo
        logo_path = f"assets/logos/{tenant_id}.png"
        if os.path.exists(logo_path):
            try:
                elements.append(Image(logo_path, width=100, height=40))
                elements.append(Spacer(1, 10))
            except Exception:
                pass

        # Active users
        cursor.execute("""
            SELECT COUNT(DISTINCT ur.user_id)
            FROM usage_records ur
            JOIN users u ON ur.user_id = u.id
            WHERE u.tenant_id = ? AND ur.usage_date BETWEEN ? AND ?
        """, (tenant_id, start_date_str, end_date_str))
        active_users = cursor.fetchone()[0] or 0

        # Churned users
        cursor.execute("""
            SELECT COUNT(DISTINCT prev.user_id)
            FROM (
                SELECT ur.user_id
                FROM usage_records ur
                JOIN users u ON ur.user_id = u.id
                WHERE u.tenant_id = ? AND ur.usage_date BETWEEN ? AND ?
            ) AS prev
            LEFT JOIN (
                SELECT ur.user_id
                FROM usage_records ur
                JOIN users u ON ur.user_id = u.id
                WHERE u.tenant_id = ? AND ur.usage_date BETWEEN ? AND ?
            ) AS curr ON prev.user_id = curr.user_id
            WHERE curr.user_id IS NULL
        """, (tenant_id, prev_start, prev_end, tenant_id, start_date_str, end_date_str))
        churned_users = cursor.fetchone()[0] or 0

        # ARPU
        arpu = billed / active_users if active_users > 0 else 0.0

        # Usage summary by metric
        cursor.execute("""
            SELECT m.metric_name, SUM(ur.usage_amount)
            FROM usage_records ur
            JOIN usage_metrics m ON ur.metric_id = m.id
            JOIN users u ON ur.user_id = u.id
            WHERE u.tenant_id = ? AND ur.usage_date BETWEEN ? AND ?
            GROUP BY m.metric_name
        """, (tenant_id, start_date_str, end_date_str))
        usage_summary = cursor.fetchall()
        usage_dict = {metric: amount for metric, amount in usage_summary}

        usage_text = ", ".join(f"{k}: {v}" for k, v in usage_dict.items()) if usage_dict else "N/A"

        # Table for this tenant
        table_data = [
            ["Metric", "Value"],
            ["Total Invoices", str(invoice_count)],
            ["Total Billed", f"R{billed:.2f}"],
            ["Total Paid", f"R{paid:.2f}"],
            ["Unpaid Invoices", str(invoice_count - int(paid > 0))],
            ["Active Users", str(active_users)],
            ["ARPU", f"R{arpu:.2f}"],
            ["Churned Users", str(churned_users)],
            ["Usage Summary", usage_text],
        ]

        table = Table(table_data, colWidths=[160, 280])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        # Add page break every 3 tenants
        if (idx + 1) % 3 == 0 and idx < len(tenants) - 1:
            elements.append(PageBreak())

        # Totals
        total_active += active_users
        total_arpu += arpu
        total_invoices += invoice_count
        total_billed += billed
        total_paid += paid
        total_churned += churned_users
        for metric, value in usage_dict.items():
            total_metrics[metric] = total_metrics.get(metric, 0) + value

    # --- Totals Table ---
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("📌 Overall Totals", styles["Heading2"]))
    usage_total_text = ", ".join(f"{k}: {v}" for k, v in total_metrics.items()) if total_metrics else "N/A"
    total_table_data = [
        ["Metric", "Total"],
        ["Total Invoices", str(total_invoices)],
        ["Total Billed", f"R{total_billed:.2f}"],
        ["Total Paid", f"R{total_paid:.2f}"],
        ["Unpaid Invoices", str(total_invoices - int(total_paid > 0))],
        ["Active Users", str(total_active)],
        ["ARPU (Avg)", f"R{(total_arpu / len(tenants)):.2f}" if tenants else "R0.00"],
        ["Churned Users", str(total_churned)],
        ["Total Usage Summary", usage_total_text],
    ]
    total_table = Table(total_table_data, colWidths=[160, 280])
    total_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d0d0d0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
    ]))
    elements.append(total_table)

    conn.close()
    doc.build(elements)
    pdf_value = buffer.getvalue()
    buffer.close()
    return pdf_value


def generate_tenant_billing_report_pdf(tenant_id, start_date, end_date):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure date format
    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")

    # Previous period range
    start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    prev_start = (start_date_obj - (end_date_obj - start_date_obj)).date()
    prev_end = (start_date_obj - datetime.timedelta(days=1)).date()

    # Fetch tenant name
    cursor.execute("SELECT name FROM tenants WHERE id = ?", (tenant_id,))
    tenant_name = cursor.fetchone()[0]

    # Fetch invoice stats
    cursor.execute("""
        SELECT COUNT(DISTINCT i.id),
               COALESCE(SUM(i.total_amount), 0),
               COALESCE(SUM(CASE WHEN i.is_paid = 1 THEN i.total_amount ELSE 0 END), 0)
        FROM invoices i
        JOIN users u ON u.id = i.user_id
        WHERE u.tenant_id = ? AND i.invoice_date BETWEEN ? AND ?
    """, (tenant_id, start_date, end_date))
    total_invoices, total_billed, total_paid = cursor.fetchone()

    # Active users this period
    cursor.execute("""
        SELECT COUNT(DISTINCT ur.user_id)
        FROM usage_records ur
        JOIN users u ON ur.user_id = u.id
        WHERE u.tenant_id = ? AND ur.usage_date BETWEEN ? AND ?
    """, (tenant_id, start_date, end_date))
    active_users = cursor.fetchone()[0] or 0

    arpu = (total_billed / active_users) if active_users > 0 else 0.0

    # Churned users
    cursor.execute("""
        SELECT COUNT(DISTINCT prev.user_id)
        FROM (
            SELECT ur.user_id
            FROM usage_records ur
            JOIN users u ON ur.user_id = u.id
            WHERE u.tenant_id = ? AND ur.usage_date BETWEEN ? AND ?
        ) AS prev
        LEFT JOIN (
            SELECT ur.user_id
            FROM usage_records ur
            JOIN users u ON ur.user_id = u.id
            WHERE u.tenant_id = ? AND ur.usage_date BETWEEN ? AND ?
        ) AS curr ON prev.user_id = curr.user_id
        WHERE curr.user_id IS NULL
    """, (tenant_id, prev_start, prev_end, tenant_id, start_date, end_date))
    churned = cursor.fetchone()[0] or 0

    # Generate PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"🏢 Billing Report for <b>{tenant_name}</b>", styles["Title"]))
    elements.append(Paragraph(f"<font size=10>Period: {start_date} to {end_date}</font>", styles["Normal"]))
    elements.append(Spacer(1, 20))

    data = [
        ["Metric", "Value"],
        ["Total Invoices", str(total_invoices)],
        ["Total Billed", f"R{total_billed:.2f}"],
        ["Total Paid", f"R{total_paid:.2f}"],
        ["Active Users", str(active_users)],
        ["ARPU", f"R{arpu:.2f}"],
        ["Churned Users", str(churned)],
    ]

    table = Table(data, colWidths=[150, 250])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))

    elements.append(table)
    conn.close()
    doc.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
