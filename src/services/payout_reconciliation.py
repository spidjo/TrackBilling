# services/payout_reconciliation.py
def handle_webhook(event):
    if event.type == "payout.paid":
        tenant_id = event.data.object.metadata.get("tenant_id")
        mark_payout_completed(tenant_id, event.data.object)