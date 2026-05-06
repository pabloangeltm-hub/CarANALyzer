"""
CarANALyzer — 24/7 Radar orchestrator.

Execution flow (see workflows/car_arbitrage_analysis.md for the full SOP):
    1. Scrape Milanuncios listings  (Playwright + stealth, ≤ BURST_MAX_PAGES per burst)
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
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv

from tools.scrape_cars import MilanunciosScraper
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
    print("\n[1/5] Scraping Milanuncios...")
    scraper = MilanunciosScraper()
    try:
        listings = await scraper.scrape(
            MilanunciosScraper.BASE_URL,
            max_pages=max_pages,
            seen_ids=seen_ids,
            start_page=start_page,
            disable_brake=disable_brake,
        )
    except Exception as exc:
        print(f"[ERROR] Scraping failed: {exc}")
        notifier.send_text(f"CarANALyzer — scraping failed:\n<code>{html.escape(str(exc))}</code>")
        return set()

    if not listings:
        print("[INFO] No new listings this burst.")
        return set()

    burst_ids = {car["ad_id"] for car in listings if car.get("ad_id")}
    print(f"      {len(listings)} new listing(s) | {len(burst_ids)} unique ID(s).")

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
        db.init_db()
        analysed_by_id = {r["car"].get("ad_id"): r for r in analysed}
        for car in listings:
            record = analysed_by_id.get(car.get("ad_id"))
            flat = {**car}
            if record:
                flat["market_price"] = record["market_price"]
                flat["roi_bruto"]    = record["roi"]
                flat["roi_neto"]     = record["roi_neto"]
            db.upsert_listing(flat)
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
