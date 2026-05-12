"""
CarANALyzer — 24/7 Radar orchestrator.

Execution flow (see workflows/car_arbitrage_analysis.md for the full SOP):
    1. Scrape Milanuncios + Wallapop listings concurrently  (<= BURST_MAX_PAGES per portal)
    2. Group by brand/model/year → compute market valuation per car (ValuationEngine)
    3. Write every analysed car to Google Sheets  (CRM)
    4. Fire Telegram alert for every car with ROI >= ROI_ALERT_THRESHOLD %
    Repeat every COOLDOWN_SECONDS seconds (radar mode) or exit after one burst (historical mode).

Usage:
    # Continuous radar (normal operation)
    python main.py

    # Historical dump — scrape pages 5-15 without stopping on known IDs
    python main.py --start-page 5 --pages 10 --disable-brake
"""

import argparse
import asyncio
import html
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv

from tools.scrape_cars import MilanunciosScraper, WallapopScraper
from tools.utils.valuation_engine import ValuationEngine, InsufficientDataError
from tools.utils.forensic_agent import ForensicAgent, analyze_batch
from tools.utils.telegram_notifier import TelegramNotifier
from tools.market_catalog import MarketCatalog, make_slug, calculate_max_bid, is_profitable
from tools.utils import db

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration — override via .env
# ---------------------------------------------------------------------------

ROI_ALERT_THRESHOLD: float = 15.0
SPREADSHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "").strip()
SHEETS_TAB: str = "Oportunidades"
BURST_MAX_PAGES: int = 10             # hard cap per burst — Datadome IP limit
COOLDOWN_SECONDS: int = 900           # 15 min between bursts
LAST_SEEN_FILE: str = ".tmp/last_seen_ids.json"


# ---------------------------------------------------------------------------
# Heuristic pre-filter configuration
# ---------------------------------------------------------------------------

_EMPTY_ENV_VALUES = {"", "any", "all", "*", "none", "null"}


@dataclass(frozen=True)
class HeuristicFilterConfig:
    year_min: int | None = None
    year_max: int | None = None
    price_min: float | None = None
    price_max: float | None = None
    seller_types: frozenset[str] = frozenset()

    @property
    def enabled(self) -> bool:
        return any(
            value is not None
            for value in (self.year_min, self.year_max, self.price_min, self.price_max)
        ) or bool(self.seller_types)

    def summary(self) -> str:
        parts: list[str] = []
        if self.year_min is not None or self.year_max is not None:
            parts.append(f"year={self.year_min or '*'}..{self.year_max or '*'}")
        if self.price_min is not None or self.price_max is not None:
            price_min = f"{self.price_min:.0f}" if self.price_min is not None else "*"
            price_max = f"{self.price_max:.0f}" if self.price_max is not None else "*"
            parts.append(f"price={price_min}..{price_max}")
        if self.seller_types:
            parts.append(f"seller_type={','.join(sorted(self.seller_types))}")
        return "; ".join(parts) if parts else "disabled"


def _env_first(*names: str) -> str:
    for name in names:
        raw = os.getenv(name, "").strip()
        if raw.lower() not in _EMPTY_ENV_VALUES:
            return raw
    return ""


def _parse_int(raw: str, label: str, warnings: list[str]) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        warnings.append(f"{label}={raw!r} is not an integer; ignored")
        return None


def _parse_price(raw: str, label: str, warnings: list[str]) -> float | None:
    if not raw:
        return None
    cleaned = raw.replace("EUR", "").replace("eur", "").replace("€", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        warnings.append(f"{label}={raw!r} is not a price; ignored")
        return None


def _parse_price_band(raw: str, warnings: list[str]) -> tuple[float | None, float | None]:
    if not raw:
        return None, None
    parts = [part.strip() for part in re.split(r"[:|,-]", raw, maxsplit=1)]
    if len(parts) != 2:
        warnings.append(
            f"AGARTHA_PREFILTER_PRICE_BAND={raw!r} must look like 'min:max'; ignored"
        )
        return None, None
    return (
        _parse_price(parts[0], "AGARTHA_PREFILTER_PRICE_BAND.min", warnings),
        _parse_price(parts[1], "AGARTHA_PREFILTER_PRICE_BAND.max", warnings),
    )


def _normalize_seller_type(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    if raw in _EMPTY_ENV_VALUES:
        return None
    aliases = {
        "particular": "private",
        "particulares": "private",
        "private": "private",
        "privado": "private",
        "profesional": "professional",
        "professional": "professional",
        "dealer": "professional",
        "business": "professional",
        "empresa": "professional",
    }
    return aliases.get(raw, raw)


def load_heuristic_filter_config() -> tuple[HeuristicFilterConfig, list[str]]:
    """Load optional pre-filter settings from .env-compatible variables."""
    warnings: list[str] = []

    year_min = _parse_int(
        _env_first("AGARTHA_PREFILTER_YEAR_MIN", "YEAR_MIN"),
        "AGARTHA_PREFILTER_YEAR_MIN",
        warnings,
    )
    year_max = _parse_int(
        _env_first("AGARTHA_PREFILTER_YEAR_MAX", "YEAR_MAX"),
        "AGARTHA_PREFILTER_YEAR_MAX",
        warnings,
    )
    price_min, price_max = _parse_price_band(
        _env_first("AGARTHA_PREFILTER_PRICE_BAND", "PRICE_BAND"),
        warnings,
    )
    explicit_price_min = _parse_price(
        _env_first("AGARTHA_PREFILTER_PRICE_MIN", "PRICE_MIN"),
        "AGARTHA_PREFILTER_PRICE_MIN",
        warnings,
    )
    explicit_price_max = _parse_price(
        _env_first("AGARTHA_PREFILTER_PRICE_MAX", "PRICE_MAX"),
        "AGARTHA_PREFILTER_PRICE_MAX",
        warnings,
    )
    price_min = explicit_price_min if explicit_price_min is not None else price_min
    price_max = explicit_price_max if explicit_price_max is not None else price_max

    seller_raw = _env_first("AGARTHA_PREFILTER_SELLER_TYPE", "SELLER_TYPE")
    seller_types = frozenset(
        normalized
        for part in re.split(r"[,;|]", seller_raw)
        if (normalized := _normalize_seller_type(part))
    )

    if year_min is not None and year_max is not None and year_min > year_max:
        warnings.append("AGARTHA_PREFILTER_YEAR_MIN is greater than YEAR_MAX; swapping")
        year_min, year_max = year_max, year_min
    if price_min is not None and price_max is not None and price_min > price_max:
        warnings.append("AGARTHA_PREFILTER_PRICE_MIN is greater than PRICE_MAX; swapping")
        price_min, price_max = price_max, price_min

    return (
        HeuristicFilterConfig(
            year_min=year_min,
            year_max=year_max,
            price_min=price_min,
            price_max=price_max,
            seller_types=seller_types,
        ),
        warnings,
    )


def _heuristic_reject_reason(car: dict, config: HeuristicFilterConfig) -> str | None:
    price = car.get("price")
    year = car.get("year")

    if config.price_min is not None or config.price_max is not None:
        if price is None:
            return "missing_price"
        if config.price_min is not None and price < config.price_min:
            return "price_below_min"
        if config.price_max is not None and price > config.price_max:
            return "price_above_max"

    if config.year_min is not None or config.year_max is not None:
        if year is None:
            return "missing_year"
        if config.year_min is not None and year < config.year_min:
            return "year_below_min"
        if config.year_max is not None and year > config.year_max:
            return "year_above_max"

    if config.seller_types:
        seller_type = _normalize_seller_type(car.get("seller_type"))
        if seller_type is None:
            return "missing_seller_type"
        if seller_type not in config.seller_types:
            return "seller_type_mismatch"

    return None


def apply_heuristic_prefilter(
    listings: list[dict],
    config: HeuristicFilterConfig,
) -> tuple[list[dict], dict[str, int]]:
    if not config.enabled:
        return listings, {}

    kept: list[dict] = []
    rejected: dict[str, int] = defaultdict(int)
    for car in listings:
        reason = _heuristic_reject_reason(car, config)
        if reason is None:
            kept.append(car)
        else:
            rejected[reason] += 1
    return kept, dict(rejected)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load_seen_ids() -> set[str]:
    try:
        with open(LAST_SEEN_FILE, encoding="utf-8") as fh:
            return set(json.load(fh))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def _save_seen_ids(ids: set[str]) -> None:
    os.makedirs(".tmp", exist_ok=True)
    with open(LAST_SEEN_FILE, "w", encoding="utf-8") as fh:
        json.dump(sorted(ids), fh, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _group_by_model(listings: list[dict]) -> dict[tuple, list[dict]]:
    """Bucket raw listings into (brand, model, year) groups for valuation."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for car in listings:
        if not car.get("brand") or car.get("price") is None:
            continue
        key = (
            (car["brand"] or "").upper(),
            (car["model"] or "").upper(),
            car.get("year"),
        )
        groups[key].append(car)
    return dict(groups)


def _sheets_row(
    car: dict,
    market_price=None,
    roi=None,
    roi_neto=None,
    sample_size=None,
) -> list:
    """Column order must match the Sheets header row:
    Portal | Marca | Modelo | Año | KM | Precio Lista | Precio Mercado |
    ROI Bruto % | ROI Neto % | Muestra | Daños | Coste Rep. € | Resumen | URL | Fecha
    """
    report = car.get("forensic_report")
    return [
        car.get("portal", ""),
        car.get("brand", ""),
        car.get("model", ""),
        car.get("year", ""),
        car.get("mileage", ""),
        car.get("price", ""),
        round(market_price, 0) if market_price is not None else "N/A",
        round(roi, 2) if roi is not None else "N/A",
        round(roi_neto, 2) if roi_neto is not None else "N/A",
        sample_size if sample_size is not None else "N/A",
        report.status if report else "",
        car.get("repair_cost_eur", 0),
        report.summary if report else "",
        car.get("url", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    ]


# ---------------------------------------------------------------------------
# Single burst (steps 1-5)
# ---------------------------------------------------------------------------

async def _run_pipeline(
    seen_ids: set[str],
    start_page: int = 1,
    disable_brake: bool = False,
    max_pages: int = BURST_MAX_PAGES,
    min_roi: float = 5.0,
) -> set[str]:
    """
    Execute one full scrape → catalog → filter → forensic → value → publish cycle.
    Returns the set of ad_ids discovered this burst (empty if nothing new).
    """
    engine   = ValuationEngine()
    notifier = TelegramNotifier()

    # ── Step 1: Scrape ──────────────────────────────────────────────────────
    print("\n[1/5] Scraping Milanuncios + Wallapop concurrently...")

    async def _scrape_portal(
        portal: str,
        scraper,
        url: str | None,
    ) -> tuple[str, list[dict], str | None]:
        try:
            results = await scraper.scrape(
                url,
                max_pages=max_pages,
                seen_ids=seen_ids,
                start_page=start_page,
                disable_brake=disable_brake,
            )
            return portal, results, None
        except Exception as exc:
            return portal, [], str(exc)

    scrape_results = await asyncio.gather(
        _scrape_portal("milanuncios", MilanunciosScraper(), MilanunciosScraper.BASE_URL),
        _scrape_portal("wallapop", WallapopScraper(), None),
    )

    listings: list[dict] = []
    failures: list[str] = []
    for portal, portal_listings, error in scrape_results:
        if error:
            failures.append(f"{portal}: {error}")
            print(f"[ERROR] {portal} scraping failed: {error}")
            continue
        listings.extend(portal_listings)
        print(f"      {portal}: {len(portal_listings)} listing(s)")

    if failures:
        message = "CarANALyzer scraping partial failure:\n" + "\n".join(
            f"<code>{html.escape(failure)}</code>" for failure in failures
        )
        if not listings:
            print("[ERROR] All scraping portals failed.")
            notifier.send_text(message)
            return set()
        notifier.send_text(message)

    if not listings:
        print("[INFO] No new listings this burst.")
        return set()

    burst_ids = {car["ad_id"] for car in listings if car.get("ad_id")}
    print(f"      {len(listings)} new listing(s) | {len(burst_ids)} unique ID(s).")

    filter_config, filter_warnings = load_heuristic_filter_config()
    for warning in filter_warnings:
        print(f"[WARN] Heuristic pre-filter config: {warning}")
    if filter_config.enabled:
        listings, rejected_counts = apply_heuristic_prefilter(listings, filter_config)
        rejected_total = sum(rejected_counts.values())
        rejected_summary = ", ".join(
            f"{reason}={count}" for reason, count in sorted(rejected_counts.items())
        ) or "none"
        print(
            f"      Heuristic pre-filter ({filter_config.summary()}): "
            f"{len(listings)} kept / {rejected_total} rejected ({rejected_summary})."
        )
        if not listings:
            print("[INFO] No listings match the heuristic pre-filter this burst.")
            return burst_ids
    else:
        print("      Heuristic pre-filter disabled (.env not set).")

    # ── Step 1.5: Market catalog update + profitable pre-filter ────────────
    print(f"\n[1.5/5] Updating market catalog and filtering by max bid...")
    catalog = MarketCatalog()

    groups_by_slug: dict[str, list] = defaultdict(list)
    for car in listings:
        if car.get("brand") and car.get("price"):
            slug = make_slug(car.get("brand", ""), car.get("model") or "", car.get("year") or "")
            groups_by_slug[slug].append(car)

    for slug, slug_cars in groups_by_slug.items():
        catalog.update_batch(slug, [c["price"] for c in slug_cars])

    for car in listings:
        if car.get("brand") and car.get("price"):
            slug = make_slug(car.get("brand", ""), car.get("model") or "", car.get("year") or "")
            entry = catalog.get(slug)
            if entry:
                car["_max_bid"] = calculate_max_bid(
                    entry["market_average_price"],
                    mileage=car.get("mileage"),
                    year=car.get("year"),
                )
                roi = (car["_max_bid"] - car["price"]) / car["price"] * 100
                car["_profitable"] = roi >= min_roi
            else:
                car["_profitable"] = False
        else:
            car["_profitable"] = False

    profitable_listings = [c for c in listings if c.get("_profitable")]
    print(f"      {len(profitable_listings)} profitable / {len(listings)} total after ROI >= {min_roi}% filter.")

    # ── Step 2: Forensic analysis (profitable listings only) ────────────────
    print(f"\n[2/5] Running forensic analysis on {len(profitable_listings)} listing(s)...")
    if profitable_listings:
        forensic_agent = ForensicAgent()
        enriched = await analyze_batch(profitable_listings, agent=forensic_agent, concurrency=5)
        forensic_by_id = {c["ad_id"]: c for c in enriched if c.get("ad_id")}
        listings = [forensic_by_id.get(c.get("ad_id"), c) for c in listings]
        damaged  = sum(1 for c in enriched if c.get("forensic_report") and c["forensic_report"].status == "damaged")
        avg_cost = sum(c.get("repair_cost_eur", 0) for c in enriched) / len(enriched)
        print(f"      {damaged} damaged | avg estimated repair {avg_cost:.0f} EUR")
    else:
        print("      No profitable listings — forensic skipped.")

    # ── Step 3: Valuation ───────────────────────────────────────────────────
    print("\n[3/5] Computing market valuations...")
    groups        = _group_by_model(listings)
    analysed:     list[dict] = []
    skipped_data  = 0
    skipped_error = 0

    for (brand, model, year), comps in groups.items():
        label = f"{brand} {model} {year or '?'}"
        try:
            for car in comps:
                result       = engine.compute(comps, target_mileage=car.get("mileage"))
                market_price = result.precio_ajustado or result.precio_mercado_base
                roi          = engine.roi(car["price"], market_price)
                repair_cost  = car.get("repair_cost_eur", 0)
                roi_neto     = engine.roi(car["price"] + repair_cost, market_price)
                analysed.append({
                    "car":          car,
                    "market_price": market_price,
                    "roi":          roi,
                    "roi_neto":     roi_neto,
                    "sample_size":  result.sample_size_trimmed,
                })
        except InsufficientDataError as e:
            print(f"  [SKIP] {label} — {e}")
            skipped_data += 1
        except Exception as exc:
            print(f"  [SKIP] {label} — unexpected error: {exc}")
            skipped_error += 1

    print(
        f"      {len(analysed)} car(s) valued | "
        f"{skipped_data} group(s) skipped (sample too small) | "
        f"{skipped_error} group(s) skipped (error)"
    )

    if not analysed:
        print("[WARN] Nothing to report — check scraper output or sample sizes.")
        notifier.send_text(
            "CarANALyzer pipeline completado sin resultados valuados.\n"
            "Revisar scraper o tamano de muestra."
        )
        return burst_ids

    clean_opportunities = [
        r for r in analysed
        if r["car"].get("forensic_report") is not None
        and r["car"]["forensic_report"].status != "damaged"
    ]
    print(f"      {len(clean_opportunities)} clean profitable opportunity/ies ready for alert.")

    # ── Step 4: SQLite CRM ──────────────────────────────────────────────────
    print(f"\n[4/5] Persisting {len(listings)} listing(s) to SQLite...")
    try:
        await db.init_db()
        analysed_by_id = {r["car"].get("ad_id"): r for r in analysed}
        for car in listings:
            record = analysed_by_id.get(car.get("ad_id"))
            flat = {**car}
            if record:
                flat["market_price"] = record["market_price"]
                flat["roi_bruto"]    = record["roi"]
                flat["roi_neto"]     = record["roi_neto"]
            await db.upsert_listing(flat)
        print(f"  [OK] {len(listings)} listing(s) upserted to .tmp/agartha.db")
    except Exception as exc:
        print(f"  [ERROR] SQLite write failed: {exc}")

    # ── Step 4 (disabled): Google Sheets CRM ────────────────────────────────
    # if not SPREADSHEET_ID:
    #     print("  [SKIP] SPREADSHEET_ID not set in .env — Sheets step skipped.")
    # else:
    #     try:
    #         analysed_by_id = {r["car"].get("ad_id"): r for r in analysed}
    #         rows_to_append = []
    #         for car in listings:
    #             record = analysed_by_id.get(car.get("ad_id"))
    #             row = _sheets_row(
    #                 car,
    #                 market_price=record["market_price"] if record else None,
    #                 roi=record["roi"] if record else None,
    #                 roi_neto=record["roi_neto"] if record else None,
    #                 sample_size=record["sample_size"] if record else None,
    #             )
    #             rows_to_append.append(row)
    #         append_rows(sheet_id=SPREADSHEET_ID, range_=SHEETS_TAB, values=rows_to_append)
    #         print(f"  [OK] {len(rows_to_append)} row(s) appended to '{SHEETS_TAB}'")
    #     except Exception as exc:
    #         print(f"  [ERROR] Google Sheets write failed: {exc}")

    # ── Step 5: Telegram alerts (profitable + forensically clean) ───────────
    print(f"\n[5/5] Sending Telegram alerts (profitable + forensically clean)...")
    if not clean_opportunities:
        print("  No clean profitable opportunities — no alerts sent.")
    else:
        async def _send_alert(record: dict) -> bool:
            car    = record["car"]
            repair = car.get("repair_cost_eur", 0)
            extra_parts = [f"ROI bruto: {record['roi']:.1f} %"]
            if repair > 0:
                extra_parts.append(f"Rep. est.: {repair:,.0f} EUR".replace(",", "."))
            return await asyncio.to_thread(
                notifier.send_opportunity,
                brand=f"{car.get('brand', '')} {car.get('model', '')}".strip(),
                list_price=car["price"],
                market_price=record["market_price"],
                roi=record["roi_neto"],
                url=car.get("url", ""),
                year=car.get("year"),
                mileage=car.get("mileage"),
                extra=" | ".join(extra_parts),
            )

        results = await asyncio.gather(
            *[_send_alert(r) for r in clean_opportunities],
            return_exceptions=True,
        )
        sent = sum(1 for r in results if r is True)
        print(f"  [OK] {sent}/{len(clean_opportunities)} alert(s) sent.")

    return burst_ids


# ---------------------------------------------------------------------------
# 24/7 Radar
# ---------------------------------------------------------------------------

async def main(
    start_page: int = 1,
    disable_brake: bool = False,
    max_pages: int = BURST_MAX_PAGES,
    min_roi: float = 5.0,
) -> None:
    """
    Radar mode (default): runs continuously, one burst every COOLDOWN_SECONDS.
    Historical mode (--disable-brake): runs a single burst and exits so the
    caller can inspect results without waiting for the cooldown cycle.
    """
    seen_ids = _load_seen_ids()

    if disable_brake:
        # One-shot historical dump — no loop, no seen_ids filtering
        print("[HISTORICAL] CarANALyzer one-shot dump started.")
        print(f"[HISTORICAL] start_page={start_page}, max_pages={max_pages}, brake=OFF")
        await _run_pipeline(
            seen_ids=set(),  # ignore history entirely
            start_page=start_page,
            disable_brake=True,
            max_pages=max_pages,
            min_roi=min_roi,
        )
        print("[HISTORICAL] Done.")
        return

    # Normal 24/7 radar
    print("[RADAR] CarANALyzer 24/7 started.")
    print(f"[RADAR] {len(seen_ids)} known ID(s) loaded from {LAST_SEEN_FILE}.")

    while True:
        print(f"\n{'=' * 60}")
        print(f"[RADAR] Burst — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}")

        try:
            new_ids = await _run_pipeline(
                seen_ids=seen_ids,
                start_page=start_page,
                disable_brake=False,
                max_pages=max_pages,
                min_roi=min_roi,
            )
            if new_ids:
                seen_ids |= new_ids
                _save_seen_ids(seen_ids)
                print(f"[RADAR] {len(seen_ids)} ID(s) saved to {LAST_SEEN_FILE}.")
        except Exception as exc:
            print(f"[RADAR] Unhandled burst error (continuing): {exc}")

        print(f"\n[RADAR] Cooling down {COOLDOWN_SECONDS}s ({COOLDOWN_SECONDS // 60} min)…")
        await asyncio.sleep(COOLDOWN_SECONDS)
        start_page = 1  # subsequent radar bursts always start from page 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CarANALyzer — Radar de arbitraje de coches"
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        dest="start_page",
        help="Primera página a raspar (default: 1)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=BURST_MAX_PAGES,
        help=f"Número de páginas por burst (default: {BURST_MAX_PAGES})",
    )
    parser.add_argument(
        "--min-roi",
        type=float,
        default=5.0,
        dest="min_roi",
        help="ROI mínimo %% para pasar el filtro financiero y activar alerta Telegram (default: 5.0)",
    )
    parser.add_argument(
        "--disable-brake",
        action="store_true",
        dest="disable_brake",
        help=(
            "Modo histórico: ignora seen_ids, nunca para en overlap. "
            "Ejecuta un único burst y termina."
        ),
    )
    args = parser.parse_args()

    asyncio.run(
        main(
            start_page=args.start_page,
            disable_brake=args.disable_brake,
            max_pages=args.pages,
            min_roi=args.min_roi,
        )
    )
