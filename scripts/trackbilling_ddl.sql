CREATE TABLE IF NOT EXISTS tenants (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            company_name TEXT,
            address TEXT,
            email TEXT,
            region TEXT,
            phone TEXT,
            industry TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Users Table
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id),
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            company_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT CHECK(role IN ('superadmin', 'admin', 'client')) DEFAULT 'client',
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            verification_token TEXT,
            last_verification_sent TIMESTAMP,
            is_verified BOOLEAN DEFAULT FALSE
        );

        -- Plans Table
        CREATE TABLE IF NOT EXISTS plans (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            name TEXT NOT NULL,
            description TEXT,
            monthly_fee NUMERIC NOT NULL,
            included_units INTEGER DEFAULT 0,
            overage_rate NUMERIC DEFAULT 0.0,
            is_active BOOLEAN DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS plan_metrics (
            id SERIAL PRIMARY KEY,
            plan_id INTEGER REFERENCES plans(id),
            metric_name TEXT,
            included_units INTEGER,
            overage_rate NUMERIC,
            unit_label TEXT
        );

        -- Subscriptions Table
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            plan_id INTEGER NOT NULL REFERENCES plans(id),
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            start_date DATE DEFAULT CURRENT_DATE,
            end_date DATE,
            is_active BOOLEAN DEFAULT TRUE
        );

        -- Usage Metrics Table
        CREATE TABLE IF NOT EXISTS usage_metrics (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
            name TEXT NOT NULL,
            metric_type TEXT,
            metric_name TEXT NOT NULL DEFAULT 'default_metric',
            unit TEXT NOT NULL DEFAULT 'units',
            usage_amount INTEGER NOT NULL DEFAULT 0
        );

        -- Plan Metric Limits Table
        CREATE TABLE IF NOT EXISTS plan_metric_limits (
            id SERIAL PRIMARY KEY,
            plan_id INTEGER NOT NULL REFERENCES plans(id),
            metric_id INTEGER NOT NULL REFERENCES usage_metrics(id),
            metric_limit INTEGER NOT NULL DEFAULT 0,
            included_units INTEGER NOT NULL DEFAULT 0,
            overage_rate NUMERIC NOT NULL DEFAULT 0.0,
            UNIQUE(plan_id, metric_id)
        );

        -- Usage Records Table
        CREATE TABLE IF NOT EXISTS usage_records (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            metric_id INTEGER NOT NULL REFERENCES plan_metrics(id),
            usage_amount INTEGER NOT NULL,
            metric_name TEXT NOT NULL DEFAULT 'default_metric',
            usage_date DATE NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Invoices Table
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            invoice_date DATE DEFAULT CURRENT_DATE,
            total_amount NUMERIC NOT NULL,
            is_paid BOOLEAN DEFAULT FALSE,
            due_date DATE DEFAULT (CURRENT_DATE + INTERVAL '30 days'),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Invoice Items Table
        CREATE TABLE IF NOT EXISTS invoice_items (
            id SERIAL PRIMARY KEY,
            invoice_id INTEGER NOT NULL REFERENCES invoices(id),
            description TEXT,
            quantity INTEGER NOT NULL,
            unit_price NUMERIC NOT NULL,
            total_price NUMERIC NOT NULL
        );

        -- Payments Table
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            invoice_id INTEGER REFERENCES invoices(id),
            amount NUMERIC,
            payment_date TIMESTAMP,
            payment_method TEXT,
            receipt_path TEXT,
            notes TEXT,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS subscription_audit (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            action TEXT NOT NULL,
            old_plan_id INTEGER REFERENCES plans(id),
            new_plan_id INTEGER REFERENCES plans(id),
            timestamp TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS verification_resend_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            timestamp TIMESTAMP,
            ip_address TEXT,
            status TEXT,
            reason TEXT
        );

        CREATE TABLE IF NOT EXISTS anomalies (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            user_id INTEGER REFERENCES users(id),
            subscription_id INTEGER REFERENCES subscriptions(id),
            metric_id INTEGER REFERENCES usage_metrics(id),
            invoice_id INTEGER REFERENCES invoices(id),
            anomaly_type TEXT NOT NULL,
            anomaly_description TEXT,
            detected_value NUMERIC,
            expected_value NUMERIC,
            threshold_value NUMERIC,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_acknowledged BOOLEAN DEFAULT FALSE,
            acknowledged_by INTEGER REFERENCES users(id),
            acknowledged_at TIMESTAMP,
            severity TEXT DEFAULT 'low' CHECK (severity IN ('low', 'medium', 'high')),
            status TEXT DEFAULT 'unresolved' CHECK (status IN ('unresolved', 'in_progress', 'resolved')),
            assigned_to INTEGER REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS anomaly_logs (
            id SERIAL PRIMARY KEY,
            anomaly_id INTEGER NOT NULL REFERENCES anomalies(id),
            action TEXT NOT NULL CHECK (action IN ('assigned', 'resolved')),
            performed_by INTEGER NOT NULL REFERENCES users(id),
            assigned_to INTEGER REFERENCES users(id),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );