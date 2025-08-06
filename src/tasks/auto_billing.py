# tasks/auto_billing.py

from billing_engine import auto_generate_invoices

if __name__ == "__main__":
    auto_generate_invoices()
    print("✅ Auto-billing completed.")
