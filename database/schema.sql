CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    first_name TEXT,
    last_name TEXT,
    company_name TEXT,
    email TEXT UNIQUE,
    role TEXT DEFAULT 'client',
    tenant_id TEXT,
    registration_date TEXT,
    is_verified INTEGER DEFAULT 0,
    verification_token TEXT,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

--tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,              -- UUID
    name TEXT NOT NULL UNIQUE,        -- Used in dropdown
    industry TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 1. PLANS TABLE (Product/Service plans per tenant)
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    monthly_fee REAL DEFAULT 0.0,
    included_units INTEGER DEFAULT 0, -- e.g. included minutes, API calls
    overage_rate REAL DEFAULT 0.0,    -- per extra unit
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- 2. SUBSCRIPTIONS (Assigns plan to a user/tenant)
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tenant_id TEXT NOT NULL,
    plan_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (plan_id) REFERENCES plans(id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- 3. USAGE METRICS (Tracks usage per tenant or user)
CREATE TABLE IF NOT EXISTS usage_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    user_id INTEGER,
    metric_type TEXT NOT NULL,         -- e.g. "api_calls", "minutes", "storage"
    quantity INTEGER DEFAULT 0,
    usage_date TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 4. INVOICES (Generated per tenant/month)
    CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id INTEGER,
            invoice_date TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            total_amount REAL NOT NULL,
            is_paid INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

-- 5. INVOICE ITEMS (Line items on each invoice)
CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price REAL DEFAULT 0.0,
    total REAL GENERATED ALWAYS AS (quantity * unit_price) STORED,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- 6. PAYMENTS (Records payments made against invoices)
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
    method TEXT,                      -- e.g. "credit_card", "bank_transfer"
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);  

-- 7. Billing EVENTS (Logs for billing actions)
CREATE TABLE IF NOT EXISTS billing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    user_id INTEGER,
    event_type TEXT NOT NULL,          -- e.g. "subscription_created", "invoice_generated"
    description TEXT,
    event_date TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS usage_aggregates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    user_id INTEGER,
    metric_type TEXT NOT NULL,
    metric_subtype TEXT,
    period TEXT NOT NULL,  -- e.g., "2025-07-31", "2025-07"
    total_quantity INTEGER DEFAULT 0,
    UNIQUE (tenant_id, user_id, metric_type, metric_subtype, period),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);



