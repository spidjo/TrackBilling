# views/admin/stripe_connect.py
def onboard_tenant(tenant_id):
    account = stripe.Account.create(
        type="express",  # For fastest onboarding
        capabilities={"card_payments": {"requested": True},
                     "transfers": {"requested": True}},
        business_type="company",
        metadata={"tenant_id": tenant_id}
    )
    
    # Generate onboarding link
    link = stripe.AccountLink.create(
        account=account.id,
        refresh_url=f"{DOMAIN}/stripe/reauth?tenant={tenant_id}",
        return_url=f"{DOMAIN}/stripe/success?tenant={tenant_id}",
        type="account_onboarding"
    )
    
    store_stripe_account_id(tenant_id, account.id)
    return link.url