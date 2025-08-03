from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
import os

def generate_invoice_pdf(invoice, items, tenant_info=None, client_info=None, logo_path=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=30*mm, bottomMargin=20*mm)
    elements = []
    styles = getSampleStyleSheet()

    # === SAFE DEFAULTS ===
    tenant_info = tenant_info or {}
    client_info = client_info or {}

    # --- Header with Logo and Tenant Info ---
    header_table_data = []

    # Logo (if exists)
    if logo_path and os.path.exists(logo_path):
        img = Image(logo_path, width=50*mm, height=20*mm)
        header_table_data.append([img, Paragraph(f"""
            <b>{tenant_info.get('name', 'Tenant Name')}</b><br/>
            {tenant_info.get('address', 'Tenant Address')}<br/>
            {tenant_info.get('email', '')}<br/>
            {tenant_info.get('phone', '')}
        """, styles["Normal"])])
    else:
        header_table_data.append(["", Paragraph(f"""
            <b>{tenant_info.get('name', 'Tenant Name')}</b><br/>
            {tenant_info.get('address', 'Tenant Address')}<br/>
            {tenant_info.get('email', '')}<br/>
            {tenant_info.get('phone', '')}
        """, styles["Normal"])])

    header_table = Table(header_table_data, colWidths=[80*mm, 90*mm])
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # --- Client Billing Info ---
    elements.append(Paragraph(f"""
        <b>Bill To:</b><br/>
        {client_info.get('name', 'Client Name')}<br/>
        {client_info.get('address', 'Client Address')}<br/>
        {client_info.get('email', '')}
    """, styles["Normal"]))
    elements.append(Spacer(1, 12))

    # --- Invoice Info ---
    elements.append(Paragraph(f"""
        <b>Invoice #: </b> {invoice['id']}<br/>
        <b>Date: </b> {invoice.get('invoice_date', '')}<br/>
        <b>Period:</b> {invoice['period_start']} to {invoice['period_end']}
    """, styles["Normal"]))
    elements.append(Spacer(1, 12))

    # --- Invoice Items Table ---
    table_data = [["Description", "Quantity", "Unit Price", "Amount"]]
    for item in items:
        table_data.append([
            item["description"],
            str(item["quantity"]),
            f"R{item['unit_price']:.2f}",
            f"R{item['quantity'] * item['unit_price']:.2f}"
        ])

    table = Table(table_data, colWidths=[180, 70, 70, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#eaeaea")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 18))

    # --- Total Section ---
    total_paragraph = Paragraph(
        f"<b>Total: R{invoice['total_amount']:.2f}</b>", styles["Heading3"]
    )
    elements.append(total_paragraph)

    # --- Footer / Notes ---
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "Please make payment to the account listed on your profile or contact support for assistance.",
        styles["Italic"]
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
