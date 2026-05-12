-- F4-T01: dealers schema for auth, API keys and subscription state.
CREATE TABLE IF NOT EXISTS dealers (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    email              TEXT NOT NULL,
    password_hash      TEXT NOT NULL,
    plan               TEXT NOT NULL DEFAULT 'free'
                           CHECK (plan IN (
                               'free',
                               'starter',
                               'pro',
                               'elite',
                               'admin',
                               'trial',
                               'basic',
                               'premium'
                           )),
    api_key_hash       TEXT,
    api_key_prefix     TEXT,
    stripe_customer_id TEXT,
    created_at         TEXT NOT NULL,
    active             INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    calls_today        INTEGER NOT NULL DEFAULT 0 CHECK (calls_today >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dealers_email_unique
    ON dealers(email);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dealers_api_key_hash_unique
    ON dealers(api_key_hash)
    WHERE api_key_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dealers_plan_active
    ON dealers(plan, active);

CREATE INDEX IF NOT EXISTS idx_dealers_stripe_customer_id
    ON dealers(stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;
