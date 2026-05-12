import json
import sqlite3
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "tools" / "api" / "migrations"
EXPECTED_COLUMNS = {"id", "dealer_id", "name", "filter_json", "created_at"}


def _run_migration(conn: sqlite3.Connection, filename: str) -> None:
    conn.executescript((MIGRATIONS_DIR / filename).read_text(encoding="utf-8"))


def test_saved_searches_schema_stores_filter_json_per_dealer(tmp_path):
    conn = sqlite3.connect(tmp_path / "saved_searches.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _run_migration(conn, "002_dealers.sql")
    _run_migration(conn, "004_saved_searches.sql")
    _run_migration(conn, "004_saved_searches.sql")
    conn.execute(
        """
        INSERT INTO dealers (name, email, password_hash, plan, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Saved Dealer", "saved@example.com", "hash", "trial", "2026-05-09T00:00:00"),
    )
    dealer_id = conn.execute("SELECT id FROM dealers").fetchone()["id"]
    filters = {"brand": "Toyota", "min_roi": 20, "seller_type": "particular"}

    conn.execute(
        """
        INSERT INTO saved_searches (dealer_id, name, filter_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (dealer_id, "Toyota ROI", json.dumps(filters), "2026-05-09T00:00:01"),
    )
    conn.commit()

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(saved_searches)").fetchall()}
    indexes = {row["name"] for row in conn.execute("PRAGMA index_list(saved_searches)").fetchall()}
    foreign_keys = conn.execute("PRAGMA foreign_key_list(saved_searches)").fetchall()
    row = conn.execute("SELECT * FROM saved_searches").fetchone()
    conn.close()

    assert EXPECTED_COLUMNS.issubset(columns)
    assert "idx_saved_searches_dealer_created_at" in indexes
    assert foreign_keys[0]["table"] == "dealers"
    assert row["dealer_id"] == dealer_id
    assert row["name"] == "Toyota ROI"
    assert json.loads(row["filter_json"]) == filters


def test_saved_searches_schema_enforces_unique_name_per_dealer(tmp_path):
    conn = sqlite3.connect(tmp_path / "saved_searches_unique.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _run_migration(conn, "002_dealers.sql")
    _run_migration(conn, "004_saved_searches.sql")
    conn.execute(
        """
        INSERT INTO dealers (name, email, password_hash, plan, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Saved Dealer", "unique@example.com", "hash", "trial", "2026-05-09T00:00:00"),
    )
    dealer_id = conn.execute("SELECT id FROM dealers").fetchone()["id"]
    params = (dealer_id, "Daily leads", "{}", "2026-05-09T00:00:01")
    conn.execute(
        "INSERT INTO saved_searches (dealer_id, name, filter_json, created_at) VALUES (?, ?, ?, ?)",
        params,
    )

    try:
        conn.execute(
            "INSERT INTO saved_searches (dealer_id, name, filter_json, created_at) VALUES (?, ?, ?, ?)",
            params,
        )
    except sqlite3.IntegrityError as exc:
        message = str(exc).lower()
    else:
        message = ""
    finally:
        conn.close()

    assert "unique" in message


def test_saved_searches_schema_cascades_when_dealer_is_deleted(tmp_path):
    conn = sqlite3.connect(tmp_path / "saved_searches_cascade.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _run_migration(conn, "002_dealers.sql")
    _run_migration(conn, "004_saved_searches.sql")
    conn.execute(
        """
        INSERT INTO dealers (name, email, password_hash, plan, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Saved Dealer", "cascade-saved@example.com", "hash", "trial", "2026-05-09T00:00:00"),
    )
    dealer_id = conn.execute("SELECT id FROM dealers").fetchone()["id"]
    conn.execute(
        "INSERT INTO saved_searches (dealer_id, name, filter_json, created_at) VALUES (?, ?, ?, ?)",
        (dealer_id, "Will disappear", "{}", "2026-05-09T00:00:01"),
    )
    conn.execute("DELETE FROM dealers WHERE id = ?", (dealer_id,))
    conn.commit()

    remaining = conn.execute("SELECT COUNT(*) AS count FROM saved_searches").fetchone()["count"]
    conn.close()

    assert remaining == 0
