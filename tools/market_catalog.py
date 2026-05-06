"""
Local market price catalog for the car arbitrage pipeline.

Maintains a persistent JSON file at .tmp/market_catalog.json that accumulates
market price observations over time. Each entry represents a unique model/year
combination (slug) and stores a running average, sample size, and last-updated
timestamp — eliminating the need for expensive real-time API calls on every run.

Usage:
    from tools.market_catalog import MarketCatalog, calculate_max_bid, is_profitable

    catalog = MarketCatalog()

    # Record a new price observation
    catalog.update("toyota_yaris_2019", 12_500)

    # Query the stored average
    entry = catalog.get("toyota_yaris_2019")
    print(entry)  # {"market_average_price": 12500.0, "sample_size": 1, "last_updated": "..."}

    # Bid decision
    max_bid = calculate_max_bid(entry["market_average_price"])
    print(is_profitable(car_price=10_800, max_bid=max_bid))  # True

Run directly for a smoke test:
    python tools/market_catalog.py
"""

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CATALOG_PATH = Path(".tmp/market_catalog.json")


# ---------------------------------------------------------------------------
# Slug helper
# ---------------------------------------------------------------------------

def make_slug(brand: str, model: str, year: int | str) -> str:
    """Normalise brand + model + year into a filesystem-safe ASCII slug.

    make_slug("Toyota", "Yaris Cross", 2019) → "toyota_yaris_cross_2019"
    """
    raw = f"{brand} {model} {year}"
    # Decompose accented chars and drop combining marks
    nfd = unicodedata.normalize("NFD", raw)
    ascii_only = nfd.encode("ascii", "ignore").decode("ascii")
    lower = ascii_only.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", lower).strip("_")
    return slug


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class MarketCatalog:
    """Persistent market price registry backed by a local JSON file.

    Each entry is keyed by a slug and stores:
        market_average_price  Running price mean across all observed samples (EUR)
        sample_size           Number of cars that contributed to the average
        last_updated          ISO-8601 UTC timestamp of the most recent update

    The running average is updated incrementally — no raw prices are stored,
    so the file stays compact even with thousands of observations.
    """

    def __init__(self, path: Path = _CATALOG_PATH) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, slug: str, new_price: float) -> dict:
        """Record a new price observation and update the running average.

        If the slug doesn't exist yet, it is created with sample_size=1.
        Returns the updated entry.
        """
        if new_price <= 0:
            raise ValueError(f"new_price must be positive, got {new_price}")

        entry = self._data.get(slug)
        if entry is None:
            self._data[slug] = {
                "market_average_price": round(float(new_price), 2),
                "sample_size": 1,
                "last_updated": _utc_now(),
            }
        else:
            n = entry["sample_size"]
            new_avg = (entry["market_average_price"] * n + new_price) / (n + 1)
            self._data[slug] = {
                "market_average_price": round(new_avg, 2),
                "sample_size": n + 1,
                "last_updated": _utc_now(),
            }

        self._save()
        return self._data[slug]

    def update_batch(self, slug: str, prices: list[float]) -> dict:
        """Record multiple price observations in one call.

        Equivalent to calling update() sequentially but more efficient for
        ingesting a full scrape batch.
        """
        for price in prices:
            self.update(slug, price)
        return self._data[slug]

    def get(self, slug: str) -> Optional[dict]:
        """Return the catalog entry for *slug*, or None if not found."""
        return self._data.get(slug)

    def all(self) -> dict:
        """Return the full catalog as a dict keyed by slug."""
        return dict(self._data)

    def remove(self, slug: str) -> bool:
        """Delete an entry. Returns True if it existed, False otherwise."""
        existed = slug in self._data
        if existed:
            del self._data[slug]
            self._save()
        return existed

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if self._path.exists():
            with self._path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        return {}

    def _save(self) -> None:
        with self._path.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Bid decision functions
# ---------------------------------------------------------------------------

def calculate_max_bid(
    market_average: float,
    mileage: Optional[int] = None,
    year: Optional[int] = None,
    desired_margin: float = 0.0,
    fixed_costs: float = 300.0,
) -> float:
    """Return the maximum purchase price that guarantees profitability.

    When mileage and year are supplied, market_average is corrected before
    computing the bid ceiling:
      - Standard usage: 15 000 km/year of age
      - Each 10 000 km above standard: -1.5% on market_average
      - Each 10 000 km below standard: +1.0% on market_average
      - Hard cap: correction never exceeds +/-30% (factor clamped to [0.70, 1.30])

    Returns:
        Maximum price to pay. Callers should treat any value <= 0 as a hard skip.
    """
    if mileage is not None and year is not None:
        age = max(1, datetime.now().year - year)
        standard_km = age * 15_000
        delta_km = mileage - standard_km
        steps = delta_km / 10_000
        raw_correction = -steps * 0.015 if steps > 0 else abs(steps) * 0.010
        factor = max(0.70, min(1.30, 1.0 + raw_correction))
        market_average = round(market_average * factor, 2)

    return round(market_average - desired_margin - fixed_costs, 2)


def is_profitable(car_price: float, max_bid: float) -> bool:
    """Return True when buying at *car_price* meets the profitability threshold.

    A car is profitable when its asking price is at or below the max bid
    calculated by calculate_max_bid().
    """
    return car_price <= max_bid


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import shutil

    TEST_PATH = Path(".tmp/market_catalog_test.json")

    # Clean slate
    if TEST_PATH.exists():
        TEST_PATH.unlink()

    catalog = MarketCatalog(path=TEST_PATH)
    slug = make_slug("Toyota", "Yaris", 2019)
    print(f"\n{'-'*55}")
    print(f"  Slug generado: {slug}")
    print(f"{'-'*55}")

    # --- Test 1: primera observación ---
    prices_day1 = [12_500, 13_000, 11_800]
    for p in prices_day1:
        catalog.update(slug, p)

    entry = catalog.get(slug)
    expected_avg = round(sum(prices_day1) / len(prices_day1), 2)
    assert entry["sample_size"] == 3, f"sample_size esperado 3, obtenido {entry['sample_size']}"
    assert entry["market_average_price"] == expected_avg, (
        f"Promedio esperado {expected_avg}, obtenido {entry['market_average_price']}"
    )
    print(f"\n[TEST 1] Tres observaciones acumuladas correctamente")
    print(f"  sample_size:          {entry['sample_size']}")
    print(f"  market_average_price: {entry['market_average_price']:,.2f} EUR")
    print(f"  last_updated:         {entry['last_updated']}")

    # --- Test 2: segunda tanda con update_batch ---
    prices_day2 = [12_200, 13_400]
    catalog.update_batch(slug, prices_day2)
    entry = catalog.get(slug)
    print(f"\n[TEST 2] Dos observaciones más vía update_batch")
    print(f"  sample_size:          {entry['sample_size']}")
    print(f"  market_average_price: {entry['market_average_price']:,.2f} EUR")

    # --- Test 3: lógica de negocio ---
    market_avg = entry["market_average_price"]
    max_bid = calculate_max_bid(market_avg, desired_margin=1_000, fixed_costs=300)
    print(f"\n[TEST 3] Decisión de compra")
    print(f"  Precio mercado:   {market_avg:,.2f} EUR")
    print(f"  Margen deseado:   1.000 EUR")
    print(f"  Costes fijos:       300 EUR")
    print(f"  Max bid:          {max_bid:,.2f} EUR")

    test_cases = [
        (10_900, True),
        (11_000, True),
        (max_bid, True),
        (max_bid + 1, False),
        (13_000, False),
    ]
    all_ok = True
    for price, expected in test_cases:
        result = is_profitable(price, max_bid)
        status = "OK" if result == expected else "FAIL"
        if status == "FAIL":
            all_ok = False
        print(f"    is_profitable({price:,.0f} EUR) -> {result}  [{status}]")

    # --- Test 4: persistencia en disco ---
    catalog2 = MarketCatalog(path=TEST_PATH)
    entry2 = catalog2.get(slug)
    assert entry2 is not None, "El catálogo no se persistió correctamente"
    assert entry2["sample_size"] == entry["sample_size"], "Discrepancia en sample_size tras recarga"
    print(f"\n[TEST 4] Persistencia en disco verificada — JSON recargado correctamente")

    # Limpieza
    TEST_PATH.unlink()
    print(f"\n{'-'*55}")
    print(f"  Archivo de test eliminado. Todos los tests {'PASARON' if all_ok else 'FALLARON'}.")
    print(f"{'-'*55}\n")
