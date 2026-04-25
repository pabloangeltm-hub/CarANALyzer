"""
Deterministic market valuation engine for the car arbitrage pipeline.

Takes a sample of comparable cars (price + mileage) and produces a cleaned,
trimmed market price plus an optional mileage-adjusted estimate for a specific
target vehicle.

Usage:
    from tools.utils.valuation_engine import ValuationEngine, InsufficientDataError

    comps = [
        {"price": 15_000, "mileage": 110_000},
        {"price": 16_500, "mileage": 95_000},
        # … at least 8 entries required
    ]

    engine = ValuationEngine()
    result = engine.compute(comps, target_mileage=130_000)

    print(result.precio_mercado_base)   # median after outlier trim
    print(result.precio_ajustado)       # base ± mileage correction
    print(result.summary())             # human-readable breakdown

All arithmetic uses only the Python stdlib (math + statistics).
No network calls, no side effects, fully deterministic.
"""

import math
import statistics
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class InsufficientDataError(ValueError):
    """Raised when the comparable sample is too small to be statistically valid."""

    def __init__(self, found: int, required: int):
        self.found = found
        self.required = required
        super().__init__(
            f"Sample too small: {found} car(s) found, {required} required. "
            "Expand the search radius or relax the filter criteria."
        )


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ValuationResult:
    """Full audit trail of a single valuation computation.

    Every field is populated so callers can log, store, or display exactly
    how the final price was derived.
    """

    # Core output
    precio_mercado_base: float          # Trimmed-sample median (EUR)
    precio_ajustado: Optional[float]    # Base ± mileage correction (None if no target)

    # Sample metadata
    sample_size_raw: int                # Cars provided before trimming
    sample_size_trimmed: int            # Cars used for the median
    trim_removed: int                   # Outliers discarded (top + bottom combined)
    price_min_trimmed: float            # Lowest price in clean sample
    price_max_trimmed: float            # Highest price in clean sample

    # Mileage adjustment (all None when target_mileage not supplied)
    mean_mileage: Optional[float]       # Group mean odometer (km)
    target_mileage: Optional[int]       # Odometer of the car being evaluated
    mileage_delta_km: Optional[float]   # target − mean  (positive → higher km → penalty)
    mileage_factor: Optional[float]     # Multiplier applied (e.g. 0.97 = −3 %)

    def summary(self) -> str:
        """Return a compact, human-readable breakdown of the valuation."""
        lines = [
            "── Valuation Engine Result ─────────────────────────",
            f"  Raw sample:         {self.sample_size_raw} comparables",
            f"  Outliers removed:   {self.trim_removed} ({self.trim_removed / self.sample_size_raw * 100:.0f} %)",
            f"  Clean sample:       {self.sample_size_trimmed} cars  "
            f"[{self.price_min_trimmed:,.0f} € — {self.price_max_trimmed:,.0f} €]",
            f"  Precio mercado base:{self.precio_mercado_base:>10,.0f} €  (mediana)",
        ]
        if self.precio_ajustado is not None:
            sign = "+" if self.mileage_delta_km <= 0 else "-"
            pct = abs(1 - self.mileage_factor) * 100
            lines += [
                f"  Km objetivo:        {self.target_mileage:>10,} km",
                f"  Km media grupo:     {self.mean_mileage:>10,.0f} km",
                f"  Δ kilometraje:      {self.mileage_delta_km:>+10,.0f} km",
                f"  Factor corrección:  {sign}{pct:.1f} %  (×{self.mileage_factor:.4f})",
                f"  Precio ajustado:    {self.precio_ajustado:>10,.0f} €",
            ]
        lines.append("─────────────────────────────────────────────────────")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ValuationEngine:
    """Stateless market price calculator.

    Business rules (all configurable as class attributes):

    MIN_SAMPLE      Minimum comparable cars required before any calculation.
                    Fewer than this raises InsufficientDataError.

    TRIM_PERCENT    Fraction removed from each tail of the sorted price list.
                    0.10 → removes the cheapest 10 % and the most expensive 10 %.
                    Uses math.floor so small samples lose at most 1 car per tail.

    MILEAGE_STEP_KM Reference odometer step for the penalty/bonus grid.
    PENALTY_PER_STEP Price correction per step (0.005 = 0.5 % per 10 000 km).
    MAX_FACTOR_DELTA Hard cap on total mileage correction (0.15 = ±15 %).
    """

    MIN_SAMPLE: int = 8
    TRIM_PERCENT: float = 0.10
    MILEAGE_STEP_KM: float = 10_000.0
    PENALTY_PER_STEP: float = 0.005   # 0.5 % per 10 000 km above/below mean
    MAX_FACTOR_DELTA: float = 0.15    # hard cap: correction never exceeds ±15 %

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute(
        self,
        cars: list[dict],
        target_mileage: Optional[int] = None,
        price_key: str = "price",
        mileage_key: str = "mileage",
    ) -> ValuationResult:
        """Compute the market valuation for a group of comparable cars.

        Args:
            cars:           List of dicts, each with at least a price field.
            target_mileage: Odometer of the specific car being evaluated.
                            When provided, the result includes a mileage-adjusted
                            price on top of the base median.
            price_key:      Dict key for the price field (default "price").
            mileage_key:    Dict key for the mileage field (default "mileage").

        Returns:
            ValuationResult with full audit trail.

        Raises:
            InsufficientDataError: If len(cars) < MIN_SAMPLE.
            KeyError:              If price_key is missing from any entry.
            ValueError:            If any price is non-numeric or negative.
        """
        prices = self._extract_prices(cars, price_key)
        self._validate_sample(prices)

        sorted_prices = sorted(prices)
        trimmed = self._trim(sorted_prices)

        base_median = statistics.median(trimmed)
        trim_removed = len(sorted_prices) - len(trimmed)

        # Mileage adjustment
        mean_mileage = mileage_factor = mileage_delta = adjusted = None
        mileages = self._extract_mileages(cars, mileage_key)

        if target_mileage is not None and mileages:
            mean_mileage = statistics.mean(mileages)
            mileage_delta = target_mileage - mean_mileage
            mileage_factor = self._compute_mileage_factor(mileage_delta)
            adjusted = round(base_median * mileage_factor, 2)

        return ValuationResult(
            precio_mercado_base=round(base_median, 2),
            precio_ajustado=adjusted,
            sample_size_raw=len(prices),
            sample_size_trimmed=len(trimmed),
            trim_removed=trim_removed,
            price_min_trimmed=trimmed[0],
            price_max_trimmed=trimmed[-1],
            mean_mileage=round(mean_mileage, 0) if mean_mileage is not None else None,
            target_mileage=target_mileage,
            mileage_delta_km=round(mileage_delta, 0) if mileage_delta is not None else None,
            mileage_factor=round(mileage_factor, 6) if mileage_factor is not None else None,
        )

    def roi(self, list_price: float, market_price: float) -> float:
        """Return the return-on-investment percentage.

        roi(15_000, 22_000) → 46.67
        Positive = profit opportunity; negative = overpriced listing.
        """
        if market_price <= 0:
            raise ValueError("market_price must be positive.")
        return round((market_price - list_price) / market_price * 100, 2)

    # ------------------------------------------------------------------
    # Internal — validation
    # ------------------------------------------------------------------

    def _validate_sample(self, prices: list[float]) -> None:
        if len(prices) < self.MIN_SAMPLE:
            raise InsufficientDataError(found=len(prices), required=self.MIN_SAMPLE)

    # ------------------------------------------------------------------
    # Internal — extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_prices(cars: list[dict], key: str) -> list[float]:
        result = []
        for i, car in enumerate(cars):
            raw = car[key]  # intentional KeyError if missing
            value = float(raw)
            if value < 0:
                raise ValueError(f"Car at index {i} has negative price: {value}")
            result.append(value)
        return result

    @staticmethod
    def _extract_mileages(cars: list[dict], key: str) -> list[float]:
        """Return mileage values, silently skipping entries where the key is absent."""
        result = []
        for car in cars:
            raw = car.get(key)
            if raw is not None:
                result.append(float(raw))
        return result

    # ------------------------------------------------------------------
    # Internal — trimming
    # ------------------------------------------------------------------

    def _trim(self, sorted_prices: list[float]) -> list[float]:
        """Remove the bottom and top TRIM_PERCENT of the sorted price list.

        Uses math.floor so a 10-car sample loses exactly 1 car per tail (not 2).
        The trimmed list always has at least 1 element when MIN_SAMPLE ≥ 2.
        """
        n = len(sorted_prices)
        cut = math.floor(n * self.TRIM_PERCENT)
        return sorted_prices[cut: n - cut] if cut > 0 else sorted_prices[:]

    # ------------------------------------------------------------------
    # Internal — mileage factor
    # ------------------------------------------------------------------

    def _compute_mileage_factor(self, delta_km: float) -> float:
        """Translate an odometer delta into a price multiplier.

        delta_km > 0 → car has MORE km than average → penalty (factor < 1).
        delta_km < 0 → car has FEWER km than average → bonus (factor > 1).

        The factor is capped at [1 − MAX_FACTOR_DELTA, 1 + MAX_FACTOR_DELTA]
        to prevent extreme outlier mileages from producing nonsensical prices.
        """
        steps = delta_km / self.MILEAGE_STEP_KM
        raw_factor = 1.0 - steps * self.PENALTY_PER_STEP
        lower = 1.0 - self.MAX_FACTOR_DELTA
        upper = 1.0 + self.MAX_FACTOR_DELTA
        return max(lower, min(upper, raw_factor))


# ---------------------------------------------------------------------------
# Quick smoke-test (run directly: python tools/utils/valuation_engine.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample = [
        {"price": 9_500,  "mileage": 180_000},
        {"price": 12_000, "mileage": 145_000},
        {"price": 13_500, "mileage": 130_000},
        {"price": 14_000, "mileage": 120_000},
        {"price": 14_800, "mileage": 115_000},
        {"price": 15_200, "mileage": 108_000},
        {"price": 16_000, "mileage": 95_000},
        {"price": 16_500, "mileage": 90_000},
        {"price": 17_200, "mileage": 82_000},
        {"price": 24_000, "mileage": 30_000},  # outlier — will be trimmed
    ]

    engine = ValuationEngine()
    result = engine.compute(sample, target_mileage=130_000)
    print(result.summary())

    listing_price = 11_000
    print(f"\n  ROI at {listing_price:,} € list price: {engine.roi(listing_price, result.precio_ajustado):.1f} %")
