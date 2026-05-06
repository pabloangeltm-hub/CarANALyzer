import os
import sqlite3
from datetime import datetime

DB_PATH = ".tmp/agartha.db"


def get_connection() -> sqlite3.Connection:
    os.makedirs(".tmp", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS listings (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                portal           TEXT,
                ad_id            TEXT,
                brand            TEXT,
                model            TEXT,
                year             INTEGER,
                mileage          INTEGER,
                price            REAL,
                market_price     REAL,
                roi_bruto        REAL,
                roi_neto         REAL,
                repair_cost      REAL,
                forensic_status  TEXT,
                forensic_summary TEXT,
                url              TEXT,
                scraped_at       TEXT,
                UNIQUE(portal, ad_id)
            );
            CREATE TABLE IF NOT EXISTS market_prices (
                slug                 TEXT PRIMARY KEY,
                market_average_price REAL,
                sample_size          INTEGER,
                last_updated         TEXT
            );
        """)


def upsert_listing(car: dict) -> None:
    """Insert or update a listing by (portal, ad_id), tracking price changes."""
    report = car.get("forensic_report")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO listings
                (portal, ad_id, brand, model, year, mileage, price,
                 market_price, roi_bruto, roi_neto, repair_cost,
                 forensic_status, forensic_summary, url, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(portal, ad_id) DO UPDATE SET
                price            = excluded.price,
                market_price     = excluded.market_price,
                roi_bruto        = excluded.roi_bruto,
                roi_neto         = excluded.roi_neto,
                repair_cost      = excluded.repair_cost,
                forensic_status  = excluded.forensic_status,
                forensic_summary = excluded.forensic_summary,
                scraped_at       = excluded.scraped_at
            """,
            (
                car.get("portal", ""),
                car.get("ad_id", ""),
                car.get("brand", ""),
                car.get("model", ""),
                car.get("year"),
                car.get("mileage"),
                car.get("price"),
                car.get("market_price"),
                car.get("roi_bruto"),
                car.get("roi_neto"),
                car.get("repair_cost_eur", 0),
                report.status if report else None,
                report.summary if report else None,
                car.get("url", ""),
                car.get("scraped_at") or datetime.now().isoformat(timespec="seconds"),
            ),
        )


def upsert_market_price(slug: str, avg_price: float, sample_size: int) -> None:
    """Insert or update a market price entry."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO market_prices (slug, market_average_price, sample_size, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                market_average_price = excluded.market_average_price,
                sample_size          = excluded.sample_size,
                last_updated         = excluded.last_updated
            """,
            (slug, avg_price, sample_size, datetime.now().isoformat(timespec="seconds")),
        )
