-- ============================================================================
-- BomaSec — PostgreSQL Schema Initialization
-- ============================================================================
-- This script runs once when the PostgreSQL container is first created.
-- It configures:
--   1. Extensions (uuid-ossp for UUID generation, pgcrypto for hashing)
--   2. Custom types (user_role enum)
--   3. Core tables (tenants, users)
--   4. Row-Level Security (RLS) policies for tenant data isolation
--   5. An application-level database role subject to RLS
--   6. Seed data for development / demo purposes
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- 0. Extensions
-- ────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ────────────────────────────────────────────────────────────────────────────
-- 1. Custom Types
-- ────────────────────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'viewer');
    END IF;
END
$$;

-- ────────────────────────────────────────────────────────────────────────────
-- 2. Tables
-- ────────────────────────────────────────────────────────────────────────────

-- Tenants — each client organization
CREATE TABLE IF NOT EXISTS tenants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_key         VARCHAR(64)  NOT NULL UNIQUE,
    company_name    VARCHAR(255) NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Index for fast API key lookups during ingestion
CREATE INDEX IF NOT EXISTS idx_tenants_api_key ON tenants (api_key);

-- Users — operators within a tenant
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           VARCHAR(320) NOT NULL UNIQUE,
    password_hash   TEXT         NOT NULL,
    role            user_role    NOT NULL DEFAULT 'viewer',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users (tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email     ON users (email);

-- ────────────────────────────────────────────────────────────────────────────
-- 3. Updated-at trigger (auto-update timestamps)
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ────────────────────────────────────────────────────────────────────────────
-- 4. Application Database Role
-- ────────────────────────────────────────────────────────────────────────────
-- The FastAPI application connects as 'bomasec_app'. This role is subject
-- to RLS policies, unlike the superuser 'bomasec' which bypasses them.
-- This ensures defense-in-depth: even if app code has bugs, the DB engine
-- itself prevents cross-tenant data leakage.
-- ────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bomasec_app') THEN
        CREATE ROLE bomasec_app WITH LOGIN PASSWORD 'bomasec_app_secret';
    END IF;
END
$$;

-- Grant necessary permissions to the app role
GRANT CONNECT ON DATABASE bomasec_db TO bomasec_app;
GRANT USAGE ON SCHEMA public TO bomasec_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bomasec_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO bomasec_app;

-- Ensure future tables also grant permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bomasec_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO bomasec_app;

-- ────────────────────────────────────────────────────────────────────────────
-- 5. Row-Level Security (RLS) Policies
-- ────────────────────────────────────────────────────────────────────────────
-- Strategy:
--   The application sets a session variable `app.current_tenant` at the
--   beginning of each transaction via: SET LOCAL app.current_tenant = '<uuid>';
--
--   RLS policies compare each row's tenant_id (or id, for tenants table)
--   against this session variable. If they don't match, the row is invisible.
--
--   The superuser 'bomasec' bypasses RLS (BYPASSRLS is default for superusers).
--   The app role 'bomasec_app' is subject to it — this is defense-in-depth.
-- ────────────────────────────────────────────────────────────────────────────

-- Enable RLS on tenants table
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants FORCE ROW LEVEL SECURITY;

-- Tenants: a tenant can only see its own row
CREATE POLICY tenant_isolation_self ON tenants
    FOR ALL
    USING (
        id = current_setting('app.current_tenant', true)::uuid
    )
    WITH CHECK (
        id = current_setting('app.current_tenant', true)::uuid
    );

-- Enable RLS on users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

-- Users: users can only see rows belonging to their tenant
CREATE POLICY tenant_isolation_users ON users
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant', true)::uuid
    )
    WITH CHECK (
        tenant_id = current_setting('app.current_tenant', true)::uuid
    );

-- ────────────────────────────────────────────────────────────────────────────
-- 6. Seed Data (Development Only)
-- ────────────────────────────────────────────────────────────────────────────
-- Two demo tenants representing typical Kenyan mid-sized institutions.
-- API keys are pre-generated for Wazuh agent configuration.
-- User passwords are bcrypt-hashed. Plaintext for dev reference:
--   admin@hakikisha.co.ke  → HakikishaAdmin2026!
--   admin@swiftcargo.co.ke → SwiftCargoAdmin2026!
-- ────────────────────────────────────────────────────────────────────────────

-- Tenant 1: Hakikisha Sacco
INSERT INTO tenants (id, api_key, company_name) VALUES (
    'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d',
    'hak_live_sk_7f3a9b2c1d4e5f6078a9b0c1d2e3f4a5',
    'Hakikisha Sacco Ltd'
) ON CONFLICT (id) DO NOTHING;

-- Tenant 2: SwiftCargo Logistics
INSERT INTO tenants (id, api_key, company_name) VALUES (
    'b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e',
    'swc_live_sk_8a4b0c2d3e5f6a7189b0c1d2e3f4a5b6',
    'SwiftCargo Logistics'
) ON CONFLICT (id) DO NOTHING;

-- Admin user for Hakikisha Sacco
-- Password: HakikishaAdmin2026!
INSERT INTO users (id, tenant_id, email, password_hash, role) VALUES (
    'c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f',
    'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d',
    'admin@hakikisha.co.ke',
    crypt('HakikishaAdmin2026!', gen_salt('bf', 12)),
    'admin'
) ON CONFLICT (id) DO NOTHING;

-- Analyst user for Hakikisha Sacco
-- Password: HakikishaAnalyst2026!
INSERT INTO users (id, tenant_id, email, password_hash, role) VALUES (
    'd4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f80',
    'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d',
    'analyst@hakikisha.co.ke',
    crypt('HakikishaAnalyst2026!', gen_salt('bf', 12)),
    'analyst'
) ON CONFLICT (id) DO NOTHING;

-- Admin user for SwiftCargo Logistics
-- Password: SwiftCargoAdmin2026!
INSERT INTO users (id, tenant_id, email, password_hash, role) VALUES (
    'e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8091',
    'b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e',
    'admin@swiftcargo.co.ke',
    crypt('SwiftCargoAdmin2026!', gen_salt('bf', 12)),
    'admin'
) ON CONFLICT (id) DO NOTHING;

-- ────────────────────────────────────────────────────────────────────────────
-- 7. Verification queries (run manually to confirm)
-- ────────────────────────────────────────────────────────────────────────────
-- To verify RLS from the app role:
--
--   SET ROLE bomasec_app;
--   SET LOCAL app.current_tenant = 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d';
--   SELECT * FROM users;   -- Should only show Hakikisha users
--   SELECT * FROM tenants; -- Should only show Hakikisha tenant
--   RESET ROLE;
-- ============================================================================
