from datetime import datetime

import pytest

from tools.market_catalog import calculate_max_bid, is_profitable, make_slug
from tools.scrape_cars import CarScraper


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("14.500 EUR", 14_500.0),
        ("16.500 EUR / 189 EUR/mes", 16_500.0),
        ("rebajado 13.900 antes 15.000", 13_900.0),
        ("500 EUR", 500.0),
        ("Consultar", None),
        ("", None),
    ],
)
def test_parse_price_handles_european_formats_and_financing(raw, expected):
    assert CarScraper.parse_price(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("145.000 km", 145_000),
        ("64 700 kilometros", 64_700),
        ("12km", 12),
        ("sin kilometros", None),
        ("", None),
    ],
)
def test_parse_mileage_extracts_digits(raw, expected):
    assert CarScraper.parse_mileage(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Seat Leon 2019 gasolina", 2019),
        ("matriculado en 2001", 2001),
        ("ano 2099", 2099),
        ("1899 clasico", None),
        ("sin ano", None),
    ],
)
def test_parse_year_accepts_1900_to_2099(raw, expected):
    assert CarScraper.parse_year(raw) == expected


def test_make_slug_normalizes_accents_symbols_and_spacing():
    assert make_slug("Citroen", "C4 Cactus", 2020) == "citroen_c4_cactus_2020"
    assert make_slug("Mercedes-Benz", "Clase A 180 d", "2018") == "mercedes_benz_clase_a_180_d_2018"
    assert make_slug("  BMW  ", "Serie   3 Touring", 2021) == "bmw_serie_3_touring_2021"


def test_calculate_max_bid_without_adjustment():
    assert calculate_max_bid(20_000, desired_margin=1_500, fixed_costs=500) == 18_000


@pytest.mark.parametrize(
    ("mileage_delta_steps", "expected_rate"),
    [
        (2, -0.03),
        (-2, 0.02),
    ],
)
def test_calculate_max_bid_adjusts_for_mileage(mileage_delta_steps, expected_rate):
    year = datetime.now().year - 4
    standard_km = 4 * 15_000
    mileage = standard_km + mileage_delta_steps * 10_000
    adjusted_market = round(20_000 * (1 + expected_rate), 2)

    assert calculate_max_bid(20_000, mileage=mileage, year=year, fixed_costs=300) == round(
        adjusted_market - 300,
        2,
    )


def test_calculate_max_bid_clamps_extreme_mileage_adjustment():
    year = datetime.now().year - 1

    assert calculate_max_bid(20_000, mileage=500_000, year=year, fixed_costs=0) == 14_000
    assert calculate_max_bid(20_000, mileage=0, year=year, fixed_costs=0) == 20_300


def test_is_profitable_compares_price_to_max_bid():
    assert is_profitable(10_000, 10_000) is True
    assert is_profitable(10_001, 10_000) is False
