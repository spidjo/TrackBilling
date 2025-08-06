# utils/pdf_generator.py

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def generate_pdf_invoice(invoice_id, user_name, invoice_items, total_amount, save_path="invoices"):
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, f"invoice_{invoice_id}.pdf")
    c = canvas.Canvas(file_path, pagesize=letter)
    c.setFont("Helvetica", 12)

    c.drawString(50, 750, f"Invoice #{invoice_id}")
    c.drawString(50, 735, f"User: {user_name}")
    c.drawString(50, 720, f"Date: {invoice_items[0]['date'] if invoice_items else 'N/A'}")

    y = 690
    for item in invoice_items:
        c.drawString(50, y, f"{item['description']} | {item['quantity']} x {item['unit_price']} = {item['total_price']}")
        y -= 20

    c.drawString(50, y-20, f"Total: ${total_amount:.2f}")
    c.save()
    return file_path
