import sqlite3
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "tools" / "api" / "migrations"
EXPECTED_COLUMNS = {"id", "dealer_id", "date", "endpoint", "calls_count"}


def _run_migration(conn: sqlite3.Connection, filename: str) -> None:
    conn.executescript((MIGRATIONS_DIR / filename).read_text(encoding="utf-8"))


def test_api_usage_schema_supports_daily_endpoint_counters(tmp_path):
    conn = sqlite3.connect(tmp_path / "api_usage.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    _run_migration(conn, "002_dealers.sql")
    _run_migration(conn, "003_api_usage.sql")
    _run_migration(conn, "003_api_usage.sql")
    conn.execute(
        """
        INSERT INTO dealers (name, email, password_hash, plan, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Usage Dealer", "usage@example.com", "hash", "trial", "2026-05-09T00:00:00"),
    )
    dealer_id = conn.execute("SELECT id FROM dealers").fetchone()["id"]

    for _ in range(2):
        conn.execute(
            """
            INSERT INTO api_usage (dealer_id, date, endpoint, calls_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(dealer_id, date, endpoint) DO UPDATE SET
                calls_count = api_usage.calls_count + excluded.calls_count
            """,
            (dealer_id, "2026-05-09", "/listings"),
        )
    conn.commit()

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(api_usage)").fetchall()}
    indexes = {row["name"] for row in conn.execute("PRAGMA index_list(api_usage)").fetchall()}
    foreign_keys = conn.execute("PRAGMA foreign_key_list(api_usage)").fetchall()
    usage = conn.execute("SELECT * FROM api_usage").fetchone()

    conn.close()

    assert EXPECTED_COLUMNS.issubset(columns)
    assert "idx_api_usage_dealer_date" in indexes
    assert "idx_api_usage_date_endpoint" in indexes
    assert foreign_keys[0]["table"] == "dealers"
    assert usage["dealer_id"] == dealer_id
    assert usage["date"] == "2026-05-09"
    assert usage["endpoint"] == "/listings"
    assert usage["calls_count"] == 2


def test_api_usage_schema_cascades_when_dealer_is_deleted(tmp_path):
    conn = sqlite3.connect(tmp_path / "api_usage_cascade.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _run_migration(conn, "002_dealers.sql")
    _run_migration(conn, "003_api_usage.sql")

    conn.execute(
        """
        INSERT INTO dealers (name, email, password_hash, plan, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Usage Dealer", "cascade@example.com", "hash", "trial", "2026-05-09T00:00:00"),
    )
    dealer_id = conn.execute("SELECT id FROM dealers").fetchone()["id"]
    conn.execute(
        "INSERT INTO api_usage (dealer_id, date, endpoint, calls_count) VALUES (?, ?, ?, ?)",
        (dealer_id, "2026-05-09", "/market/stats", 4),
    )
    conn.execute("DELETE FROM dealers WHERE id = ?", (dealer_id,))
    conn.commit()

    remaining = conn.execute("SELECT COUNT(*) AS count FROM api_usage").fetchone()["count"]
    conn.close()

    assert remaining == 0
