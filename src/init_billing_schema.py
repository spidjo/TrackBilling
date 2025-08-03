import sqlite3

def init_billing_schema(db_path="data/billing.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
         
         -- DROP ALL TABLES IF EXISTS
     
        
        -- Tenants Table
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company_name TEXT,
            address TEXT,
            email TEXT,
            region TEXT,
            phone TEXT,
            industry TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Users Table
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            company_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT CHECK(role IN ('superadmin', 'admin', 'client')) DEFAULT 'client',
            registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            verification_token TEXT,
            is_verified INTEGER DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        );
        -- Plans Table
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            monthly_fee REAL NOT NULL,
            included_units INTEGER DEFAULT 0,
            overage_rate REAL DEFAULT 0.0,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        );

        -- Subscriptions Table
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            start_date TEXT DEFAULT CURRENT_DATE,
            end_date TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        );

        -- Usage Metrics Table
        CREATE TABLE IF NOT EXISTS usage_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            usage_date TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            -- user_id is TEXT to support custom usernames like 'user_alpha1'
        );

        -- Invoices Table
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            invoice_date TEXT DEFAULT CURRENT_DATE,
            total_amount REAL NOT NULL,
            is_paid INTEGER DEFAULT 0,
            due_date TEXT DEFAULT (DATE('now', '+30 days')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Invoice Items Table
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );
        -- Payments Table
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            payment_date TEXT DEFAULT CURRENT_DATE,
            amount_paid REAL NOT NULL,
            payment_method TEXT,
            notes TEXT,
            reference TEXT,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );


    """)

    conn.commit()
    conn.close()
    print("✅ Billing schema initialized successfully.")


if __name__ == "__main__":
    init_billing_schema()
