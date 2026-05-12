import asyncio
from types import SimpleNamespace

import pytest

from tools.utils import forensic_agent as fa


def test_extract_json_strips_think_blocks():
    raw = '<think>{"noise": true}</think> prefix {"tiene_averia": true, "motivo": "motor"}'

    assert fa._extract_json(raw) == {"tiene_averia": True, "motivo": "motor"}


def test_normalize_report_clamps_confidence_and_adds_keyword_hits():
    report = fa._normalize_report(
        {
            "tiene_averia": "true",
            "status": "damaged",
            "confidence_score": 2,
            "damage_keywords": ["turbo"],
            "damage_types": ["motor", "unknown"],
            "motivo": "Turbo roto.",
        },
        "Se vende con turbo roto y no arranca.",
    )

    assert report.schema_version == "v2"
    assert report.tiene_averia is True
    assert report.status == "damaged"
    assert report.confidence_score == 1.0
    assert "turbo" in report.damage_keywords
    assert "no arranca" in report.damage_keywords
    assert report.damage_types == ["motor"]
    assert report.summary == "Turbo roto."


def test_normalize_report_uses_keyword_default_and_damage_fallback():
    report = fa._normalize_report({"motivo": ""}, "Necesita grua, para reparar.")

    assert report.status == "damaged"
    assert report.tiene_averia is True
    assert report.confidence_score == 0.8
    assert report.damage_types == ["averia_generica"]
    assert report.motivo == "Posibles danos detectados."


def test_fallback_report_marks_damaged_as_generic_breakdown():
    report = fa._fallback_report("error", status="damaged", confidence_score=0.35)

    assert report.status == "damaged"
    assert report.tiene_averia is True
    assert report.damage_types == ["averia_generica"]


def test_repair_cost_engine_prices_by_brand_damage_and_keywords():
    report = fa.ForensicReport(
        tiene_averia=True,
        motivo="airbag y siniestro",
        status="damaged",
        summary="airbag y siniestro",
        confidence_score=1.0,
        damage_keywords=["airbag", "siniestro"],
        damage_types=[],
    )

    seat_range = fa.RepairCostEngine.estimate_range(report, brand="Seat")
    porsche_range = fa.RepairCostEngine.estimate_range(report, brand="Porsche")

    assert seat_range[0] > 0
    assert porsche_range[0] > seat_range[0]
    assert fa.RepairCostEngine.estimate(report, brand="Seat") == fa.RepairCostEngine._round_to_50(
        sum(seat_range) / 2
    )


def test_repair_cost_engine_returns_zero_for_clean_report():
    report = fa.ForensicReport(
        tiene_averia=False,
        motivo="sin danos",
        status="clean",
        summary="sin danos",
    )

    assert fa.RepairCostEngine.estimate_range(report, brand="BMW") == (0.0, 0.0)
    assert fa.RepairCostEngine.estimate(report, brand="BMW") == 0.0


def test_forensic_agent_analyze_success_with_mock_ollama():
    async def run():
        agent = fa.ForensicAgent()

        class Client:
            async def chat(self, **kwargs):
                assert kwargs["format"] == "json"
                return SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"tiene_averia": false, "status": "clean", '
                            '"confidence_score": 0.7, "motivo": "Sin danos."}'
                        )
                    )
                )

        agent._client = Client()
        return await agent.analyze("Vehiculo revisado, sin danos.", brand="Seat")

    report = asyncio.run(run())

    assert report.status == "clean"
    assert report.tiene_averia is False
    assert report.confidence_score == 0.7


def test_forensic_agent_analyze_malformed_response_fails_safe():
    async def run():
        agent = fa.ForensicAgent()

        class Client:
            async def chat(self, **kwargs):
                return SimpleNamespace(message=SimpleNamespace(content="not json"))

        agent._client = Client()
        return await agent.analyze("Descripcion cualquiera.", brand="Seat")

    report = asyncio.run(run())

    assert report.status == "damaged"
    assert report.tiene_averia is True
    assert report.confidence_score == 0.35
    assert report.damage_types == ["averia_generica"]


def test_analyze_batch_enriches_reports_and_repair_costs():
    class Agent:
        async def analyze(self, text, brand=""):
            return fa.ForensicReport(
                tiene_averia=True,
                motivo="fallo motor",
                status="damaged",
                summary="fallo motor",
                confidence_score=0.9,
                damage_keywords=["fallo motor"],
                damage_types=["motor"],
            )

    async def run():
        return await fa.analyze_batch(
            [
                {"ad_id": "1", "brand": "BMW", "description": "fallo motor"},
                {"ad_id": "2", "brand": "Seat", "description": ""},
            ],
            agent=Agent(),
            concurrency=5,
        )

    enriched = asyncio.run(run())

    damaged, empty = enriched
    assert damaged["forensic_report"].status == "damaged"
    assert damaged["repair_cost_eur"] > 0
    assert damaged["repair_cost_range_eur"][1] >= damaged["repair_cost_range_eur"][0]
    assert empty["forensic_report"].status == "dudoso"
    assert empty["repair_cost_eur"] == 0.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [("si", True), ("no", False), ("unexpected", True)],
)
def test_as_bool_handles_spanish_strings_and_default(value, expected):
    assert fa._as_bool(value, default=True) is expected
