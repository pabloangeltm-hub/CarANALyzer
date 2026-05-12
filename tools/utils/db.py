import asyncio
import json
import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Awaitable, Callable, TypeVar

import aiosqlite

DB_PATH = os.getenv("AGARTHA_DB_PATH", ".tmp/agartha.db")
POOL_SIZE = int(os.getenv("AGARTHA_DB_POOL_SIZE", "5"))
BUSY_TIMEOUT_MS = int(os.getenv("AGARTHA_DB_BUSY_TIMEOUT_MS", "5000"))
MAX_RETRIES = int(os.getenv("AGARTHA_DB_MAX_RETRIES", "5"))
RETRY_BASE_DELAY = float(os.getenv("AGARTHA_DB_RETRY_BASE_DELAY", "0.05"))
PRICE_DEDUP_TOLERANCE = 0.05
MILEAGE_DEDUP_TOLERANCE = 0.10

_pool: asyncio.Queue[aiosqlite.Connection] | None = None
_pool_lock = asyncio.Lock()
_backup_done = False

T = TypeVar("T")

_LISTINGS_MIGRATION_COLUMNS: dict[str, str] = {
    "condition_score": "REAL",
    "images_count": "INTEGER",
    "seller_type": "TEXT",
    "location": "TEXT",
    "price_history_json": "TEXT",
}

_LISTINGS_FTS_COLUMNS = (
    "brand",
    "model",
    "location",
    "forensic_summary",
    "url",
)


def _db_path() -> Path:
    return Path(DB_PATH)


def _is_busy_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    busy_markers = ("database is locked", "database table is locked", "busy")
    return (
        isinstance(exc, aiosqlite.OperationalError)
        and any(marker in message for marker in busy_markers)
    )


def _is_fts_unavailable(exc: BaseException) -> bool:
    message = str(exc).lower()
    return isinstance(exc, aiosqlite.OperationalError) and (
        "no such module: fts5" in message
        or "no such table: listings_fts" in message
    )


def _ensure_db_backup() -> None:
    """Create a one-time backup before the first write-oriented init in this process."""
    global _backup_done
    if _backup_done:
        return

    db_file = _db_path()
    if db_file.exists() and db_file.stat().st_size > 0:
        backup_dir = db_file.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{db_file.stem}_{timestamp}{db_file.suffix}"
        shutil.copy2(db_file, backup_path)

    _backup_done = True


async def _open_connection() -> aiosqlite.Connection:
    db_file = _db_path()
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(db_file, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA synchronous=NORMAL;")
    await conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS};")
    await conn.commit()
    return conn


async def _get_pool() -> asyncio.Queue[aiosqlite.Connection]:
    global _pool
    if _pool is not None:
        return _pool

    async with _pool_lock:
        if _pool is None:
            pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue(maxsize=POOL_SIZE)
            for _ in range(POOL_SIZE):
                await pool.put(await _open_connection())
            _pool = pool
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    pool = await _get_pool()
    conn = await pool.get()
    try:
        yield conn
    finally:
        pool.put_nowait(conn)


async def close_pool() -> None:
    global _pool
    if _pool is None:
        return

    while not _pool.empty():
        conn = await _pool.get()
        await conn.close()
    _pool = None


async def _with_retry(operation: Callable[[aiosqlite.Connection], Awaitable[T]]) -> T:
    last_exc: BaseException | None = None

    for attempt in range(MAX_RETRIES + 1):
        async with get_connection() as conn:
            try:
                result = await operation(conn)
                await conn.commit()
                return result
            except Exception as exc:
                await conn.rollback()
                last_exc = exc
                if not _is_busy_error(exc) or attempt >= MAX_RETRIES:
                    raise
                await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))

    raise RuntimeError("SQLite operation failed without an exception") from last_exc


async def _ensure_columns(
    conn: aiosqlite.Connection,
    table_name: str,
    columns: dict[str, str],
) -> None:
    cursor = await conn.execute(f"PRAGMA table_info({table_name})")
    existing = {row["name"] for row in await cursor.fetchall()}
    for column_name, column_type in columns.items():
        if column_name not in existing:
            await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


async def _ensure_listings_fts(conn: aiosqlite.Connection) -> None:
    try:
        await conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS listings_fts USING fts5(
                brand,
                model,
                location,
                forensic_summary,
                url,
                tokenize='unicode61 remove_diacritics 2'
            )
            """
        )
        await conn.execute("DELETE FROM listings_fts")
        await conn.execute(
            """
            INSERT INTO listings_fts(rowid, brand, model, location, forensic_summary, url)
            SELECT id, brand, model, location, forensic_summary, url
            FROM listings
            """
        )
    except aiosqlite.OperationalError as exc:
        if _is_fts_unavailable(exc):
            return
        raise


async def _sync_listing_fts(conn: aiosqlite.Connection, listing_id: int) -> None:
    try:
        cursor = await conn.execute(
            """
            SELECT brand, model, location, forensic_summary, url
            FROM listings
            WHERE id = ?
            """,
            (listing_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            await conn.execute("DELETE FROM listings_fts WHERE rowid = ?", (listing_id,))
            return
        await conn.execute("DELETE FROM listings_fts WHERE rowid = ?", (listing_id,))
        await conn.execute(
            """
            INSERT INTO listings_fts(rowid, brand, model, location, forensic_summary, url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (listing_id, *(row[column] for column in _LISTINGS_FTS_COLUMNS)),
        )
    except aiosqlite.OperationalError as exc:
        if _is_fts_unavailable(exc):
            return
        raise


def _json_text_or_none(value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load_price_history(value: object) -> list[dict[str, object]]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []

    history: list[dict[str, object]] = []
    seen: set[tuple[float, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        try:
            price = float(item["price"])
        except (KeyError, TypeError, ValueError):
            continue
        scraped_at = str(item.get("scraped_at") or "").strip()
        if not scraped_at:
            continue
        key = (price, scraped_at)
        if key in seen:
            continue
        seen.add(key)
        history.append({"price": price, "scraped_at": scraped_at})
    return history


def _price_history_json(
    existing_value: object,
    incoming_value: object,
    price: object,
    scraped_at: str,
) -> str | None:
    history = _load_price_history(existing_value)
    incoming = _load_price_history(incoming_value)
    known = {(entry["price"], entry["scraped_at"]) for entry in history}

    for entry in incoming:
        key = (entry["price"], entry["scraped_at"])
        if key not in known:
            history.append(entry)
            known.add(key)

    try:
        current_price = float(price)
    except (TypeError, ValueError):
        current_price = None

    if current_price is not None and scraped_at:
        if not history or history[-1]["price"] != current_price:
            history.append({"price": current_price, "scraped_at": scraped_at})

    return _json_text_or_none(history)


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").casefold().strip().split())


def _dedup_pair(
    portal_a: str,
    ad_id_a: str,
    portal_b: str,
    ad_id_b: str,
) -> tuple[str, str, str, str]:
    first = (portal_a, ad_id_a)
    second = (portal_b, ad_id_b)
    if second < first:
        first, second = second, first
    return first[0], first[1], second[0], second[1]


def _match_score(
    price: float,
    candidate_price: float,
    mileage: float,
    candidate_mileage: float,
) -> float:
    price_delta = abs(candidate_price - price) / price if price else PRICE_DEDUP_TOLERANCE
    mileage_delta = (
        abs(candidate_mileage - mileage) / mileage
        if mileage
        else MILEAGE_DEDUP_TOLERANCE
    )
    price_score = max(0.0, 1.0 - (price_delta / PRICE_DEDUP_TOLERANCE))
    mileage_score = max(0.0, 1.0 - (mileage_delta / MILEAGE_DEDUP_TOLERANCE))
    return round((price_score + mileage_score) / 2, 4)


async def _record_cross_portal_duplicates(
    conn: aiosqlite.Connection,
    car: dict,
    detected_at: str,
) -> None:
    portal = str(car.get("portal") or "").strip()
    ad_id = str(car.get("ad_id") or "").strip()
    brand = _clean_text(car.get("brand"))
    model = _clean_text(car.get("model"))
    year = car.get("year")
    price = car.get("price")
    mileage = car.get("mileage")

    if not all((portal, ad_id, brand, model, year, price, mileage)):
        return

    price = float(price)
    mileage = float(mileage)
    if price <= 0 or mileage <= 0:
        return

    await conn.execute(
        """
        DELETE FROM listing_duplicates
        WHERE (portal = ? AND ad_id = ?)
           OR (duplicate_portal = ? AND duplicate_ad_id = ?)
        """,
        (portal, ad_id, portal, ad_id),
    )

    price_low = price * (1 - PRICE_DEDUP_TOLERANCE)
    price_high = price * (1 + PRICE_DEDUP_TOLERANCE)
    mileage_low = mileage * (1 - MILEAGE_DEDUP_TOLERANCE)
    mileage_high = mileage * (1 + MILEAGE_DEDUP_TOLERANCE)

    cursor = await conn.execute(
        """
        SELECT portal, ad_id, price, mileage
        FROM listings
        WHERE portal != ?
          AND lower(trim(brand)) = ?
          AND lower(trim(model)) = ?
          AND year = ?
          AND price BETWEEN ? AND ?
          AND mileage BETWEEN ? AND ?
        """,
        (portal, brand, model, year, price_low, price_high, mileage_low, mileage_high),
    )
    candidates = await cursor.fetchall()

    for candidate in candidates:
        candidate_portal = str(candidate["portal"] or "")
        candidate_ad_id = str(candidate["ad_id"] or "")
        if not candidate_portal or not candidate_ad_id:
            continue

        pair = _dedup_pair(portal, ad_id, candidate_portal, candidate_ad_id)
        score = _match_score(price, float(candidate["price"]), mileage, float(candidate["mileage"]))
        await conn.execute(
            """
            INSERT INTO listing_duplicates
                (portal, ad_id, duplicate_portal, duplicate_ad_id,
                 match_score, match_reason, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(portal, ad_id, duplicate_portal, duplicate_ad_id) DO UPDATE SET
                match_score  = excluded.match_score,
                match_reason = excluded.match_reason,
                detected_at  = excluded.detected_at
            """,
            (
                *pair,
                score,
                "brand_model_year_price_5pct_mileage_10pct",
                detected_at,
            ),
        )


async def init_db() -> None:
    _ensure_db_backup()

    async def _init(conn: aiosqlite.Connection) -> None:
        await conn.executescript("""
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
                condition_score  REAL,
                images_count     INTEGER,
                seller_type      TEXT,
                location         TEXT,
                price_history_json TEXT,
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
            CREATE TABLE IF NOT EXISTS listing_duplicates (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                portal              TEXT NOT NULL,
                ad_id               TEXT NOT NULL,
                duplicate_portal    TEXT NOT NULL,
                duplicate_ad_id     TEXT NOT NULL,
                match_score         REAL,
                match_reason        TEXT,
                detected_at         TEXT,
                UNIQUE(portal, ad_id, duplicate_portal, duplicate_ad_id)
            );
        """)
        await _ensure_columns(conn, "listings", _LISTINGS_MIGRATION_COLUMNS)
        await _ensure_listings_fts(conn)

    await _with_retry(_init)


async def upsert_listing(car: dict) -> None:
    """Insert or update a listing by (portal, ad_id), tracking price changes."""
    report = car.get("forensic_report")
    scraped_at = car.get("scraped_at") or datetime.now().isoformat(timespec="seconds")

    async def _upsert(conn: aiosqlite.Connection) -> None:
        cursor = await conn.execute(
            """
            SELECT price_history_json
            FROM listings
            WHERE portal = ? AND ad_id = ?
            """,
            (car.get("portal", ""), car.get("ad_id", "")),
        )
        existing = await cursor.fetchone()
        price_history_json = _price_history_json(
            existing["price_history_json"] if existing else None,
            car.get("price_history_json"),
            car.get("price"),
            scraped_at,
        )

        await conn.execute(
            """
            INSERT INTO listings
                (portal, ad_id, brand, model, year, mileage, price,
                 market_price, roi_bruto, roi_neto, repair_cost,
                 condition_score, images_count, seller_type, location,
                 price_history_json,
                 forensic_status, forensic_summary, url, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(portal, ad_id) DO UPDATE SET
                price            = excluded.price,
                market_price     = excluded.market_price,
                roi_bruto        = excluded.roi_bruto,
                roi_neto         = excluded.roi_neto,
                repair_cost      = excluded.repair_cost,
                condition_score  = excluded.condition_score,
                images_count     = excluded.images_count,
                seller_type      = excluded.seller_type,
                location         = excluded.location,
                price_history_json = excluded.price_history_json,
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
                car.get("condition_score"),
                car.get("images_count"),
                car.get("seller_type"),
                car.get("location"),
                price_history_json,
                report.status if report else None,
                report.summary if report else None,
                car.get("url", ""),
                scraped_at,
            ),
        )
        cursor = await conn.execute(
            "SELECT id FROM listings WHERE portal = ? AND ad_id = ?",
            (car.get("portal", ""), car.get("ad_id", "")),
        )
        row = await cursor.fetchone()
        if row is not None:
            await _sync_listing_fts(conn, int(row["id"]))
        await _record_cross_portal_duplicates(conn, car, scraped_at)

    await _with_retry(_upsert)


async def upsert_market_price(slug: str, avg_price: float, sample_size: int) -> None:
    """Insert or update a market price entry."""

    async def _upsert(conn: aiosqlite.Connection) -> None:
        await conn.execute(
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

    await _with_retry(_upsert)
