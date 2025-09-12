-- ================================
-- TrackBilling Database Schema
-- ================================

-- Tenants (companies using the platform)
CREATE TABLE IF NOT EXISTS tenants
(
    id SERIAL PRIMARY KEY,
    name text COLLATE pg_catalog."default" NOT NULL,
    company_name text COLLATE pg_catalog."default",
    address text COLLATE pg_catalog."default",
    email text COLLATE pg_catalog."default",
    region text COLLATE pg_catalog."default",
    phone text COLLATE pg_catalog."default",
    industry text COLLATE pg_catalog."default",
    created_at text COLLATE pg_catalog."default" DEFAULT CURRENT_TIMESTAMP,
    logo_url text COLLATE pg_catalog."default",
    is_active boolean,
    stripe_account_id character varying(30) COLLATE pg_catalog."default",
    billing_contact text COLLATE pg_catalog."default",
    vat_number text COLLATE pg_catalog."default",
    tax_id text COLLATE pg_catalog."default"
);

-- Users (SuperAdmin, Admin, Client)
CREATE TABLE IF NOT EXISTS users
(
    id SERIAL PRIMARY KEY,
    tenant_id integer,
    first_name text COLLATE pg_catalog."default" NOT NULL,
    last_name text COLLATE pg_catalog."default" NOT NULL,
    company_name text COLLATE pg_catalog."default" NOT NULL,
    username text COLLATE pg_catalog."default" NOT NULL,
    password text COLLATE pg_catalog."default" NOT NULL,
    email text COLLATE pg_catalog."default" NOT NULL,
    role text COLLATE pg_catalog."default" DEFAULT 'client'::text,
    is_active integer DEFAULT 1,
    verification_token text COLLATE pg_catalog."default",
    last_verification_sent text COLLATE pg_catalog."default",
    is_verified integer DEFAULT 0,
    registration_date date DEFAULT CURRENT_TIMESTAMP,
    last_login timestamp without time zone,
    token_timestamp timestamp without time zone,
    phone text COLLATE pg_catalog."default",
    billing_address text COLLATE pg_catalog."default",
    CONSTRAINT users_username_key UNIQUE (username),
    CONSTRAINT users_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT users_role_check CHECK (role = ANY (ARRAY['superadmin'::text, 'admin'::text, 'client'::text]))
);

-- Plans (subscription offerings)
CREATE TABLE IF NOT EXISTS plans
(
    id SERIAL PRIMARY KEY,
    tenant_id integer NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    description text COLLATE pg_catalog."default",
    monthly_fee numeric NOT NULL,
    included_units integer DEFAULT 0,
    overage_rate numeric DEFAULT 0.0,
    is_active boolean DEFAULT true,
    billing_cycle text COLLATE pg_catalog."default" NOT NULL DEFAULT 'monthly'::text,
    start_date date NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT plans_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions
(
    id SERIAL PRIMARY KEY,
    user_id integer NOT NULL,
    plan_id integer NOT NULL,
    tenant_id integer NOT NULL,
    start_date date DEFAULT CURRENT_DATE,
    end_date date,
    is_active boolean DEFAULT true,
    CONSTRAINT subscriptions_plan_id_fkey FOREIGN KEY (plan_id)
        REFERENCES plans (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT subscriptions_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


-- Plan Metrics table to define metrics associated with each plan
CREATE TABLE IF NOT EXISTS plan_metrics
(
    id SERIAL PRIMARY KEY,
    plan_id integer,
    metric_name text COLLATE pg_catalog."default",
    included_units integer,
    overage_rate numeric,
    unit_label text COLLATE pg_catalog."default",
    CONSTRAINT plan_metrics_plan_id_fkey FOREIGN KEY (plan_id)
        REFERENCES plans (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


-- plan_metric_limits table to define limits and overage rates for each metric in a plan
CREATE TABLE IF NOT EXISTS plan_metric_limits
(
    id SERIAL PRIMARY KEY,
    plan_id integer NOT NULL,
    metric_id integer NOT NULL,
    metric_limit integer NOT NULL DEFAULT 0,
    included_units integer NOT NULL DEFAULT 0,
    overage_rate numeric NOT NULL DEFAULT 0.0,
    CONSTRAINT plan_metric_limits_plan_id_metric_id_key UNIQUE (plan_id, metric_id),
    CONSTRAINT plan_metric_limits_metric_id_fkey FOREIGN KEY (metric_id)
        REFERENCES usage_metrics (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT plan_metric_limits_plan_id_fkey FOREIGN KEY (plan_id)
        REFERENCES plans (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


CREATE TABLE IF NOT EXISTS usage_metrics
(
    id SERIAL PRIMARY KEY,
    tenant_id integer NOT NULL,
    usage_date date NOT NULL DEFAULT CURRENT_DATE,
    name text COLLATE pg_catalog."default" NOT NULL,
    metric_type text COLLATE pg_catalog."default",
    metric_name text COLLATE pg_catalog."default" NOT NULL DEFAULT 'default_metric'::text,
    unit text COLLATE pg_catalog."default" NOT NULL DEFAULT 'units'::text,
    usage_amount integer NOT NULL DEFAULT 0,
    created_at date DEFAULT CURRENT_DATE,
    description text COLLATE pg_catalog."default",
    CONSTRAINT usage_metrics_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


CREATE TABLE IF NOT EXISTS usage_records
(
    id SERIAL PRIMARY KEY,
    tenant_id integer NOT NULL,
    user_id integer NOT NULL,
    metric_id integer NOT NULL,
    usage_amount integer NOT NULL,
    metric_name text COLLATE pg_catalog."default" NOT NULL DEFAULT 'default_metric'::text,
    usage_date date NOT NULL,
    recorded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT usage_records_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT usage_records_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


CREATE TABLE IF NOT EXISTS subscription_audit
(
    id SERIAL PRIMARY KEY,
    user_id integer NOT NULL,
    tenant_id integer NOT NULL,
    action text COLLATE pg_catalog."default" NOT NULL,
    old_plan_id integer,
    new_plan_id integer,
    "timestamp" timestamp without time zone NOT NULL,
    CONSTRAINT subscription_audit_new_plan_id_fkey FOREIGN KEY (new_plan_id)
        REFERENCES plans (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT subscription_audit_old_plan_id_fkey FOREIGN KEY (old_plan_id)
        REFERENCES plans (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT subscription_audit_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT subscription_audit_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


CREATE TABLE IF NOT EXISTS invoices
(
    id SERIAL PRIMARY KEY,
    tenant_id integer NOT NULL,
    user_id integer NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    invoice_date date DEFAULT CURRENT_DATE,
    is_paid boolean DEFAULT false,
    due_date date DEFAULT (CURRENT_DATE + '30 days'::interval),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    pdf_generated boolean DEFAULT false,
    subtotal numeric NOT NULL DEFAULT 0,
    tax_amount numeric NOT NULL DEFAULT 0,
    notes text COLLATE pg_catalog."default",
    paid_at date,
    payment_status character varying(20) COLLATE pg_catalog."default" DEFAULT 'unpaid'::character varying,
    credit_amount numeric NOT NULL DEFAULT 0,
    amount numeric NOT NULL DEFAULT 0,
    is_overdue boolean DEFAULT false,
    total_invoiced numeric NOT NULL DEFAULT 0,
    total_paid numeric NOT NULL DEFAULT 0,
    balance numeric NOT NULL DEFAULT 0,
    CONSTRAINT invoices_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT invoices_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


CREATE TABLE IF NOT EXISTS invoice_items
(
    id SERIAL PRIMARY KEY,
    invoice_id integer NOT NULL,
    description text COLLATE pg_catalog."default",
    quantity integer NOT NULL,
    unit_price numeric NOT NULL,
    total_price numeric NOT NULL,
    created_at date DEFAULT CURRENT_DATE,
    CONSTRAINT invoice_items_invoice_id_fkey FOREIGN KEY (invoice_id)
        REFERENCES invoices (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


CREATE TABLE IF NOT EXISTS alerts
(
    id SERIAL PRIMARY KEY,
    tenant_id integer NOT NULL,
    user_id integer NOT NULL,
    metric_id integer NOT NULL,
    alert_type character varying(50) COLLATE pg_catalog."default" NOT NULL,
    message text COLLATE pg_catalog."default",
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS anomalies
(
    id SERIAL PRIMARY KEY,
    tenant_id integer NOT NULL,
    user_id integer,
    subscription_id integer,
    metric_id integer,
    invoice_id integer,
    anomaly_type text COLLATE pg_catalog."default" NOT NULL,
    anomaly_description text COLLATE pg_catalog."default",
    detected_value numeric,
    expected_value numeric,
    threshold_value numeric,
    detected_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_acknowledged boolean DEFAULT false,
    acknowledged_by integer,
    acknowledged_at timestamp without time zone,
    severity text COLLATE pg_catalog."default" DEFAULT 'low'::text,
    status text COLLATE pg_catalog."default" DEFAULT 'unresolved'::text,
    assigned_to integer,
    CONSTRAINT anomalies_acknowledged_by_fkey FOREIGN KEY (acknowledged_by)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomalies_assigned_to_fkey FOREIGN KEY (assigned_to)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomalies_invoice_id_fkey FOREIGN KEY (invoice_id)
        REFERENCES invoices (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomalies_metric_id_fkey FOREIGN KEY (metric_id)
        REFERENCES usage_metrics (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomalies_subscription_id_fkey FOREIGN KEY (subscription_id)
        REFERENCES subscriptions (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomalies_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomalies_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomalies_severity_check CHECK (severity = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text])),
    CONSTRAINT anomalies_status_check CHECK (status = ANY (ARRAY['unresolved'::text, 'in_progress'::text, 'resolved'::text]))
);


CREATE TABLE IF NOT EXISTS anomaly_logs
(
    id SERIAL PRIMARY KEY,
    anomaly_id integer NOT NULL,
    action text COLLATE pg_catalog."default" NOT NULL,
    performed_by integer NOT NULL,
    assigned_to integer,
    comment text COLLATE pg_catalog."default",
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT anomaly_logs_anomaly_id_fkey FOREIGN KEY (anomaly_id)
        REFERENCES anomalies (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomaly_logs_assigned_to_fkey FOREIGN KEY (assigned_to)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomaly_logs_performed_by_fkey FOREIGN KEY (performed_by)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT anomaly_logs_action_check CHECK (action = ANY (ARRAY['assigned'::text, 'resolved'::text]))
);


CREATE TABLE IF NOT EXISTS audit_log
(
    id SERIAL PRIMARY KEY,
    event_time timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id integer,
    tenant_id integer,
    action_type character varying(50) COLLATE pg_catalog."default" NOT NULL,
    action character varying(100) COLLATE pg_catalog."default" NOT NULL,
    entity_type character varying(50) COLLATE pg_catalog."default",
    entity_id character varying(100) COLLATE pg_catalog."default",
    ip_address character varying(45) COLLATE pg_catalog."default",
    user_agent text COLLATE pg_catalog."default",
    metadata jsonb,
    status character varying(20) COLLATE pg_catalog."default",
    CONSTRAINT fk_audit_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


CREATE TABLE IF NOT EXISTS feature_usage
(
    id SERIAL PRIMARY KEY,
    user_id integer NOT NULL,
    tenant_id integer NOT NULL,
    feature_name character varying(100) COLLATE pg_catalog."default" NOT NULL,
    usage_date timestamp without time zone NOT NULL,
    usage_count integer DEFAULT 1,
    duration_seconds integer,
    additional_metadata jsonb,
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_user FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE INDEX IF NOT EXISTS idx_feature_usage_user_date ON feature_usage (user_id, usage_date);

CREATE TABLE IF NOT EXISTS invoice_generation_log
(
    generated_at timestamp without time zone NOT NULL,
    invoice_count integer NOT NULL,
    status character varying(20) COLLATE pg_catalog."default" NOT NULL,
    period text COLLATE pg_catalog."default",
    CONSTRAINT unique_period UNIQUE (period)
);

CREATE TABLE IF NOT EXISTS password_resets
(
    id SERIAL PRIMARY KEY,
    user_id integer,
    email text COLLATE pg_catalog."default",
    token text COLLATE pg_catalog."default",
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_used boolean DEFAULT false,
    expires_at timestamp with time zone,
    CONSTRAINT password_resets_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);


CREATE TABLE IF NOT EXISTS payments
(
    id SERIAL PRIMARY KEY,
    user_id integer,
    invoice_id integer,
    amount numeric,
    payment_date timestamp without time zone,
    payment_method text COLLATE pg_catalog."default",
    receipt_path text COLLATE pg_catalog."default",
    notes text COLLATE pg_catalog."default",
    is_verified boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    verified_at date,
    CONSTRAINT payments_invoice_id_fkey FOREIGN KEY (invoice_id)
        REFERENCES invoices (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT payments_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS usage_metrics
(
    id SERIAL PRIMARY KEY,
    tenant_id integer NOT NULL,
    usage_date date NOT NULL DEFAULT CURRENT_DATE,
    name text COLLATE pg_catalog."default" NOT NULL,
    metric_type text COLLATE pg_catalog."default",
    metric_name text COLLATE pg_catalog."default" NOT NULL DEFAULT 'default_metric'::text,
    unit text COLLATE pg_catalog."default" NOT NULL DEFAULT 'units'::text,
    usage_amount integer NOT NULL DEFAULT 0,
    created_at date DEFAULT CURRENT_DATE,
    description text COLLATE pg_catalog."default",
    CONSTRAINT usage_metrics_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS usage_records
(
    id SERIAL PRIMARY KEY,
    tenant_id integer NOT NULL,
    user_id integer NOT NULL,
    metric_id integer NOT NULL,
    usage_amount integer NOT NULL,
    metric_name text COLLATE pg_catalog."default" NOT NULL DEFAULT 'default_metric'::text,
    usage_date date NOT NULL,
    recorded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT usage_records_tenant_id_fkey FOREIGN KEY (tenant_id)
        REFERENCES tenants (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT usage_records_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS plan_metric_limits
(
    id SERIAL PRIMARY KEY,
    plan_id integer NOT NULL,
    metric_id integer NOT NULL,
    metric_limit integer NOT NULL DEFAULT 0,
    included_units integer NOT NULL DEFAULT 0,
    overage_rate numeric NOT NULL DEFAULT 0.0,
    CONSTRAINT plan_metric_limits_plan_id_metric_id_key UNIQUE (plan_id, metric_id),
    CONSTRAINT plan_metric_limits_metric_id_fkey FOREIGN KEY (metric_id)
        REFERENCES usage_metrics (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT plan_metric_limits_plan_id_fkey FOREIGN KEY (plan_id)
        REFERENCES plans (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS plan_metrics
(
    id SERIAL PRIMARY KEY,
    plan_id integer,
    metric_name text COLLATE pg_catalog."default",
    included_units integer,
    overage_rate numeric,
    unit_label text COLLATE pg_catalog."default",
    CONSTRAINT plan_metrics_plan_id_fkey FOREIGN KEY (plan_id)
        REFERENCES plans (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS platform_fees
(
    transaction_id character varying(50) COLLATE pg_catalog."default" NOT NULL,
    tenant_id integer NOT NULL,
    amount_cents integer NOT NULL,
    processed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT platform_fees_pkey PRIMARY KEY (transaction_id)
);

CREATE TABLE IF NOT EXISTS verification_resend_log
(
    id SERIAL PRIMARY KEY,
    user_id integer,
    "timestamp" timestamp without time zone,
    ip_address text COLLATE pg_catalog."default",
    status text COLLATE pg_catalog."default",
    reason text COLLATE pg_catalog."default",
    attempt_count numeric,
    CONSTRAINT verification_resend_log_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);