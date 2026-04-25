"""
CarANALyzer — arbitrage pipeline orchestrator.

Execution flow (see workflows/car_arbitrage_analysis.md for the full SOP):
    1. Scrape Milanuncios listings  (Playwright + stealth)
    2. Group by brand/model/year → compute market valuation per car (ValuationEngine)
    3. Write every analysed car to Google Sheets  (CRM)
    4. Fire Telegram alert for every car with ROI >= ROI_ALERT_THRESHOLD %

Usage:
    python main.py
    python main.py --pages 5
"""

import argparse
import asyncio
import os
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv

from tools.scrape_cars import MilanunciosScraper
from tools.utils.valuation_engine import ValuationEngine, InsufficientDataError
from tools.utils.google_sheets_manager import GoogleSheetsManager
from tools.utils.telegram_notifier import TelegramNotifier

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration — override via .env or CLI flags
# ---------------------------------------------------------------------------

ROI_ALERT_THRESHOLD: float = 15.0          # % minimum ROI to trigger Telegram alert
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "").strip()
SHEETS_TAB: str = "Oportunidades"          # Must exist as a tab inside the spreadsheet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _group_by_model(listings: list[dict]) -> dict[tuple, list[dict]]:
    """Bucket raw listings into (brand, model, year) groups for valuation.

    Cars missing brand or price are silently discarded — the engine would
    reject them anyway and they add noise to the sample.
    """
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


def _sheets_row(car: dict, market_price: float, roi: float, sample_size: int) -> list:
    """Build a flat ordered row. Column order must match the Sheets header row:
    Portal | Marca | Modelo | Año | KM | Precio Lista | Precio Mercado | ROI % | Muestra | URL | Fecha
    """
    return [
        car.get("portal", ""),
        car.get("brand", ""),
        car.get("model", ""),
        car.get("year", ""),
        car.get("mileage", ""),
        car.get("price", ""),
        round(market_price, 0),
        round(roi, 2),
        sample_size,
        car.get("url", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    ]


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

async def main(pages: int = 3) -> None:
    engine   = ValuationEngine()
    notifier = TelegramNotifier()

    # ── Step 1: Scrape ──────────────────────────────────────────────────────
    print("\n[1/4] Scraping Milanuncios…")
    scraper = MilanunciosScraper()
    try:
        listings = await scraper.scrape(MilanunciosScraper.BASE_URL, max_pages=pages)
    except Exception as exc:
        print(f"[ERROR] Scraping failed: {exc}")
        notifier.send_text(f"❌ CarANALyzer — scraping failed:\n<code>{exc}</code>")
        return

    if not listings:
        print("[WARN] No listings returned — aborting.")
        return

    print(f"      {len(listings)} raw listing(s) collected.")

    # ── Step 2: Valuation ───────────────────────────────────────────────────
    print("\n[2/4] Computing market valuations…")
    groups = _group_by_model(listings)

    # Each record: {car, market_price, roi, sample_size}
    analysed: list[dict] = []
    skipped_data  = 0
    skipped_error = 0

    for (brand, model, year), comps in groups.items():
        label = f"{brand} {model} {year or '?'}"
        try:
            for car in comps:
                result = engine.compute(comps, target_mileage=car.get("mileage"))
                market_price = result.precio_ajustado or result.precio_mercado_base
                roi = engine.roi(car["price"], market_price)
                analysed.append({
                    "car":         car,
                    "market_price": market_price,
                    "roi":         roi,
                    "sample_size": result.sample_size_trimmed,
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
            "⚠️ CarANALyzer pipeline completado sin resultados valuados.\n"
            "Revisar scraper o tamaño de muestra."
        )
        return

    opportunities = [r for r in analysed if r["roi"] >= ROI_ALERT_THRESHOLD]
    print(f"      {len(opportunities)} opportunity/ies with ROI ≥ {ROI_ALERT_THRESHOLD} %")

    # ── Step 3: Google Sheets CRM ───────────────────────────────────────────
    print(f"\n[3/4] Writing {len(analysed)} row(s) to Google Sheets…")
    if not SPREADSHEET_ID:
        print("  [SKIP] SPREADSHEET_ID not set in .env — Sheets step skipped.")
    else:
        try:
            sheets = GoogleSheetsManager()
            sheets.connect(spreadsheet_id=SPREADSHEET_ID)
            for record in analysed:
                row = _sheets_row(
                    record["car"],
                    record["market_price"],
                    record["roi"],
                    record["sample_size"],
                )
                sheets.append_row(row, worksheet_name=SHEETS_TAB)
            print(f"  [OK] {len(analysed)} row(s) appended to '{SHEETS_TAB}'")
        except Exception as exc:
            print(f"  [ERROR] Google Sheets write failed: {exc}")

    # ── Step 4: Telegram alerts ─────────────────────────────────────────────
    print(f"\n[4/4] Sending Telegram alerts (ROI ≥ {ROI_ALERT_THRESHOLD} %)…")
    if not opportunities:
        print("  No opportunities above threshold — no alerts sent.")
    else:
        sent = 0
        for record in opportunities:
            car = record["car"]
            ok = notifier.send_opportunity(
                brand=f"{car.get('brand', '')} {car.get('model', '')}".strip(),
                list_price=car["price"],
                market_price=record["market_price"],
                roi=record["roi"],
                url=car.get("url", ""),
                year=car.get("year"),
                mileage=car.get("mileage"),
            )
            if ok:
                sent += 1
        print(f"  [OK] {sent}/{len(opportunities)} alert(s) sent.")

    print("\n[DONE] Pipeline complete.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CarANALyzer arbitrage pipeline")
    parser.add_argument(
        "--pages",
        type=int,
        default=3,
        help="Number of Milanuncios pages to scrape (default: 3)",
    )
    args = parser.parse_args()
    asyncio.run(main(pages=args.pages))
