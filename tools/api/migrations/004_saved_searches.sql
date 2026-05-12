-- F4-T03: saved listing filters per dealer.
CREATE TABLE IF NOT EXISTS saved_searches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dealer_id   INTEGER NOT NULL,
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0),
    filter_json TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (dealer_id) REFERENCES dealers(id) ON DELETE CASCADE,
    UNIQUE (dealer_id, name)
);

CREATE INDEX IF NOT EXISTS idx_saved_searches_dealer_created_at
    ON saved_searches(dealer_id, created_at DESC);
