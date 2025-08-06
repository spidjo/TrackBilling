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
            last_verification_sent TEXT,
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

        CREATE TABLE IF NOT EXISTS plan_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER,
            metric_name TEXT,          -- e.g., 'API Calls', 'Seats', 'Storage (GB)'
            included_units INTEGER,
            overage_rate REAL,
            unit_label TEXT,           -- e.g., 'calls', 'users', 'GB'
            FOREIGN KEY (plan_id) REFERENCES plans(id)
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
            usage_date TEXT NOT NULL DEFAULT CURRENT_DATE,
            name TEXT NOT NULL,
            metric_type TEXT,
            metric_name TEXT NOT NULL DEFAULT 'default_metric',  -- e.g., 'API Calls', 'Storage'
            unit TEXT NOT NULL DEFAULT 'units',  -- e.g., 'calls', 'users', 'GB'
            usage_amount INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            -- user_id is TEXT to support custom usernames like 'user_alpha1'
        );

        --DROP TABLE IF EXISTS plan_metric_limits;
        -- Plan Metric Limits Table
        CREATE TABLE IF NOT EXISTS plan_metric_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            metric_id INTEGER NOT NULL,
            metric_limit INTEGER NOT NULL DEFAULT 0,
            included_units INTEGER NOT NULL DEFAULT 0,
            overage_rate REAL NOT NULL DEFAULT 0.0,
            UNIQUE(plan_id, metric_id),
            FOREIGN KEY (plan_id) REFERENCES plans(id),
            FOREIGN KEY (metric_id) REFERENCES usage_metrics(id)
        ); 
       
        -- Usage Records Table
        CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            metric_id INTEGER NOT NULL,
            usage_amount INTEGER NOT NULL,
            metric_name TEXT NOT NULL DEFAULT 'default_metric',  -- e.g., 'API Calls', 'Storage'
            usage_date DATE NOT NULL,
            recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (metric_id) REFERENCES plan_metrics(id)
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
        --DROP TABLE IF EXISTS payments;
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            invoice_id INTEGER,
            amount REAL,
            payment_date TEXT,
            payment_method TEXT,
            receipt_path TEXT,
            notes TEXT,
            is_verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );
        


        CREATE TABLE IF NOT EXISTS subscription_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            action TEXT NOT NULL,            -- 'subscribed', 'cancelled', 'switched'
            old_plan_id INTEGER,             -- nullable
            new_plan_id INTEGER,             -- nullable
            timestamp TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(old_plan_id) REFERENCES plans(id),
            FOREIGN KEY(new_plan_id) REFERENCES plans(id)
        );

        CREATE TABLE IF NOT EXISTS verification_resend_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            ip_address TEXT,
            status TEXT,          -- 'success', 'blocked', 'error'
            reason TEXT,         -- nullable, e.g., 'rate limit', 'already verified'
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    conn.commit()


    conn.close()
    
    print("✅ Billing schema initialized successfully.")


if __name__ == "__main__":
    init_billing_schema()
