import pytest

from tools.utils.valuation_engine import InsufficientDataError, ValuationEngine


SAMPLE = [
    {"price": 9_500, "mileage": 180_000},
    {"price": 12_000, "mileage": 145_000},
    {"price": 13_500, "mileage": 130_000},
    {"price": 14_000, "mileage": 120_000},
    {"price": 14_800, "mileage": 115_000},
    {"price": 15_200, "mileage": 108_000},
    {"price": 16_000, "mileage": 95_000},
    {"price": 16_500, "mileage": 90_000},
    {"price": 17_200, "mileage": 82_000},
    {"price": 24_000, "mileage": 30_000},
]


def test_compute_trims_outliers_and_adjusts_for_mileage():
    result = ValuationEngine().compute(SAMPLE, target_mileage=130_000)

    assert result.precio_mercado_base == 15_000
    assert result.precio_ajustado == 14_846.25
    assert result.sample_size_raw == 10
    assert result.sample_size_trimmed == 8
    assert result.trim_removed == 2
    assert result.price_min_trimmed == 12_000
    assert result.price_max_trimmed == 17_200
    assert result.mean_mileage == 109_500
    assert result.mileage_delta_km == 20_500
    assert result.mileage_factor == 0.98975


def test_compute_without_target_mileage_returns_base_only():
    result = ValuationEngine().compute(SAMPLE)

    assert result.precio_mercado_base == 15_000
    assert result.precio_ajustado is None
    assert result.mean_mileage is None
    assert result.target_mileage is None
    assert "Precio mercado base" in result.summary()


def test_compute_uses_custom_price_and_mileage_keys():
    cars = [
        {"ask": 10_000, "km": 100_000},
        {"ask": 12_000, "km": 80_000},
        {"ask": 14_000, "km": 60_000},
    ]

    result = ValuationEngine().compute(
        cars,
        target_mileage=70_000,
        price_key="ask",
        mileage_key="km",
    )

    assert result.precio_mercado_base == 12_000
    assert result.precio_ajustado == 12_060
    assert result.mean_mileage == 80_000


def test_compute_skips_missing_mileages():
    cars = [{"price": 10_000}, {"price": 12_000}, {"price": 14_000}]

    result = ValuationEngine().compute(cars, target_mileage=80_000)

    assert result.precio_mercado_base == 12_000
    assert result.precio_ajustado is None
    assert result.mileage_factor is None


def test_insufficient_data_error_exposes_counts():
    with pytest.raises(InsufficientDataError) as exc:
        ValuationEngine().compute([{"price": 10_000}])

    assert exc.value.found == 1
    assert exc.value.required == 2
    assert "Sample too small" in str(exc.value)


def test_missing_price_raises_key_error():
    with pytest.raises(KeyError):
        ValuationEngine().compute([{"price": 10_000}, {"mileage": 1}])


@pytest.mark.parametrize("bad_price", [-1, "not-a-number"])
def test_invalid_price_raises_value_error(bad_price):
    with pytest.raises(ValueError):
        ValuationEngine().compute([{"price": 10_000}, {"price": bad_price}])


def test_mileage_factor_is_capped_for_extreme_values():
    engine = ValuationEngine()

    assert engine._compute_mileage_factor(1_000_000) == 0.85
    assert engine._compute_mileage_factor(-1_000_000) == 1.15


def test_trim_handles_small_samples_without_cutting():
    engine = ValuationEngine()

    assert engine._trim([10_000, 12_000]) == [10_000, 12_000]


def test_roi_uses_market_price_denominator():
    engine = ValuationEngine()

    assert engine.roi(15_000, 22_000) == 31.82
    with pytest.raises(ValueError, match="market_price must be positive"):
        engine.roi(10_000, 0)


def test_summary_includes_mileage_breakdown_when_adjusted():
    summary = ValuationEngine().compute(SAMPLE, target_mileage=80_000).summary()

    assert "Km objetivo" in summary
    assert "Precio ajustado" in summary
