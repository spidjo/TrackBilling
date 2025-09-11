# utils/payment_processor.py
def charge_customer(tenant_id, amount_cents):
    tenant_account = get_stripe_account_id(tenant_id)
    
    try:
        payment = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            application_fee_amount=calculate_platform_fee(amount_cents),
            transfer_data={"destination": tenant_account},
            metadata={"tenant_id": tenant_id}
        )
        return payment.client_secret
    except stripe.error.StripeError as e:
        log_error(e)
        raise PaymentProcessingError(str(e))