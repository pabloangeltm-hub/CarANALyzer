-- F4-T02: daily API usage counters per dealer and endpoint.
CREATE TABLE IF NOT EXISTS api_usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dealer_id   INTEGER NOT NULL,
    date        TEXT NOT NULL,
    endpoint    TEXT NOT NULL,
    calls_count INTEGER NOT NULL DEFAULT 0 CHECK (calls_count >= 0),
    FOREIGN KEY (dealer_id) REFERENCES dealers(id) ON DELETE CASCADE,
    UNIQUE (dealer_id, date, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_api_usage_dealer_date
    ON api_usage(dealer_id, date);

CREATE INDEX IF NOT EXISTS idx_api_usage_date_endpoint
    ON api_usage(date, endpoint);
