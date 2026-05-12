"""
ForensicAgent - local AI damage triage via Ollama (deepseek-r1:8b).

Zero cloud cost. Runs fully offline against localhost:11434.
Semaphore(1) ensures the local GPU processes one request at a time, avoiding
OOM on small local GPUs.

Output contract (backward-compatible with main.py):
    report.status           -> "damaged" | "clean" | "dudoso"
    report.summary          -> human-readable explanation
    report.tiene_averia     -> bool
    report.confidence_score -> float 0.0-1.0
    report.damage_keywords  -> evidence keywords found in the listing text

RepairCostEngine estimates repair costs from brand and damage type ranges.
"""

import asyncio
import json
import re
from typing import Any

import ollama
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

class ForensicReport(BaseModel):
    schema_version: str = "v2"
    tiene_averia: bool
    motivo: str
    status: str   # "damaged" | "clean" | "dudoso"
    summary: str  # mirrors motivo; kept for pipeline compatibility
    confidence_score: float = 0.0
    damage_keywords: list[str] = Field(default_factory=list)
    damage_types: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Repair cost estimation
# ---------------------------------------------------------------------------

class RepairCostEngine:
    """Estimate repair cost ranges by brand segment and forensic damage type."""

    _BASE_RANGES_EUR: dict[str, tuple[int, int]] = {
        "motor": (1800, 4500),
        "transmision": (900, 2500),
        "carroceria": (600, 2200),
        "chasis": (2500, 6500),
        "airbag": (900, 2600),
        "documentacion_itv": (150, 700),
        "frenos": (250, 800),
        "suspension": (350, 1200),
        "direccion": (500, 1500),
        "electrico": (250, 1600),
        "siniestro": (2000, 8000),
        "inundacion": (1500, 6000),
        "incendio": (2500, 9000),
        "averia_generica": (500, 2000),
    }

    _BRAND_MULTIPLIERS: dict[str, float] = {
        # Premium/luxury parts and labor tend to price materially higher.
        "audi": 1.25,
        "bmw": 1.30,
        "mercedes": 1.35,
        "mercedes-benz": 1.35,
        "mini": 1.20,
        "volvo": 1.20,
        "lexus": 1.25,
        "tesla": 1.45,
        "porsche": 1.70,
        "land rover": 1.55,
        "range rover": 1.60,
        "jaguar": 1.45,
        # Mainstream EU/Asian brands.
        "volkswagen": 1.10,
        "vw": 1.10,
        "seat": 1.00,
        "cupra": 1.10,
        "skoda": 1.00,
        "renault": 0.95,
        "peugeot": 0.95,
        "citroen": 0.95,
        "opel": 0.95,
        "ford": 1.00,
        "fiat": 0.90,
        "toyota": 1.00,
        "honda": 1.05,
        "nissan": 1.00,
        "mazda": 1.05,
        "hyundai": 0.95,
        "kia": 0.95,
        "dacia": 0.85,
        # Low-volume or specialty brands.
        "alfa romeo": 1.20,
        "jeep": 1.20,
        "subaru": 1.15,
        "mitsubishi": 1.10,
        "smart": 1.10,
    }

    _KEYWORD_TYPE_HINTS: tuple[tuple[str, str], ...] = (
        ("no arranca", "motor"),
        ("fallo motor", "motor"),
        ("motor roto", "motor"),
        ("motor gripado", "motor"),
        ("culata", "motor"),
        ("junta culata", "motor"),
        ("turbo", "motor"),
        ("inyectores", "motor"),
        ("caja de cambios", "transmision"),
        ("embrague", "transmision"),
        ("airbag", "airbag"),
        ("chasis", "chasis"),
        ("bastidor", "chasis"),
        ("estructura", "chasis"),
        ("itv desfavorable", "documentacion_itv"),
        ("itv negativa", "documentacion_itv"),
        ("sin itv", "documentacion_itv"),
        ("frenos", "frenos"),
        ("abs", "frenos"),
        ("suspension", "suspension"),
        ("direccion", "direccion"),
        ("electrico", "electrico"),
        ("centralita", "electrico"),
        ("siniestro", "siniestro"),
        ("accidentado", "siniestro"),
        ("choque", "siniestro"),
        ("colision", "siniestro"),
        ("inundado", "inundacion"),
        ("incendio", "incendio"),
    )

    @classmethod
    def estimate_range(cls, report: ForensicReport, brand: str = "") -> tuple[float, float]:
        """Return an estimated (min, max) repair cost range in EUR."""
        if not cls._should_price(report):
            return (0.0, 0.0)

        damage_types = cls._damage_types(report)
        multiplier = cls._brand_multiplier(brand)
        confidence = max(0.35, min(1.0, report.confidence_score or 0.65))

        ranges = [cls._scaled_range(damage_type, multiplier) for damage_type in damage_types]
        ranges.sort(key=lambda item: item[1], reverse=True)

        min_cost, max_cost = ranges[0]
        for extra_min, extra_max in ranges[1:]:
            min_cost += extra_min * 0.45
            max_cost += extra_max * 0.35

        if report.status == "dudoso":
            min_cost *= 0.50
            max_cost *= 0.60

        min_cost *= confidence
        max_cost *= max(confidence, 0.70)

        return (cls._round_to_50(min_cost), cls._round_to_50(max(max_cost, min_cost)))

    @staticmethod
    def estimate(report: ForensicReport, brand: str = "") -> float:
        """Return the midpoint of the repair cost range for existing ROI code."""
        low, high = RepairCostEngine.estimate_range(report, brand=brand)
        return RepairCostEngine._round_to_50((low + high) / 2)

    @classmethod
    def _should_price(cls, report: ForensicReport) -> bool:
        return report.status in {"damaged", "dudoso"} and (
            report.tiene_averia or bool(report.damage_types) or bool(report.damage_keywords)
        )

    @classmethod
    def _damage_types(cls, report: ForensicReport) -> list[str]:
        damage_types = [
            item for item in report.damage_types
            if item in cls._BASE_RANGES_EUR
        ]

        for keyword in report.damage_keywords:
            folded = keyword.casefold()
            for needle, damage_type in cls._KEYWORD_TYPE_HINTS:
                if needle in folded and damage_type not in damage_types:
                    damage_types.append(damage_type)

        return damage_types or ["averia_generica"]

    @classmethod
    def _brand_multiplier(cls, brand: str) -> float:
        normalized = re.sub(r"\s+", " ", brand.casefold().replace("_", " ")).strip()
        if not normalized:
            return 1.0
        if normalized in cls._BRAND_MULTIPLIERS:
            return cls._BRAND_MULTIPLIERS[normalized]
        for known_brand, multiplier in cls._BRAND_MULTIPLIERS.items():
            if known_brand in normalized:
                return multiplier
        return 1.0

    @classmethod
    def _scaled_range(cls, damage_type: str, multiplier: float) -> tuple[float, float]:
        low, high = cls._BASE_RANGES_EUR.get(damage_type, cls._BASE_RANGES_EUR["averia_generica"])
        return (low * multiplier, high * multiplier)

    @staticmethod
    def _round_to_50(amount: float) -> float:
        return float(round(amount / 50) * 50)


# ---------------------------------------------------------------------------
# Ollama configuration
# ---------------------------------------------------------------------------

_OLLAMA_HOST = "http://localhost:11434"
_MODEL = "deepseek-r1:8b"
_SEMAPHORE_SIZE = 1

_VALID_STATUSES = {"damaged", "clean", "dudoso"}

_DAMAGE_KEYWORDS = (
    "averia", "averiado", "no arranca", "no funciona", "fallo motor",
    "motor roto", "motor gripado", "culata", "junta culata", "turbo",
    "embrague", "caja de cambios", "inyectores", "bomba", "alternador",
    "correa distribucion", "cadena distribucion", "testigo motor",
    "luz motor", "airbag", "siniestro", "accidentado", "golpe", "choque",
    "colision", "chasis", "bastidor", "estructura", "grua", "para reparar",
    "reparar", "itv desfavorable", "itv negativa", "sin itv", "fuga",
    "perdida de aceite", "sobrecalienta", "calentamiento", "radiador",
    "suspension", "direccion", "frenos", "abs", "electrico", "centralita",
    "inundado", "incendio", "granizo", "piezas rotas", "rotura",
)

_DAMAGE_TYPES = (
    "motor", "transmision", "carroceria", "chasis", "airbag",
    "documentacion_itv", "frenos", "suspension", "direccion", "electrico",
    "siniestro", "inundacion", "incendio", "averia_generica",
)

_PROMPT_PREFIX = (
    "/no_think\n"  # disable deepseek-r1 chain-of-thought
    "Eres un analista forense de anuncios de coches usados en Espana. "
    "Detecta danos, averias mecanicas, siniestros, problemas de ITV o "
    "documentacion, y senales de compra peligrosa.\n"
    "Pistas de riesgo: "
    + ", ".join(_DAMAGE_KEYWORDS)
    + ".\n"
    "Tipos permitidos: "
    + ", ".join(_DAMAGE_TYPES)
    + ".\n"
    "Reglas: usa damaged solo con evidencia explicita; clean si el texto "
    "niega danos o solo menciona mantenimiento normal; dudoso si falta "
    "informacion o hay ambiguedad.\n"
    "Responde UNICAMENTE con JSON valido schema v2:\n"
    '{"schema_version":"v2","tiene_averia":true/false,'
    '"status":"damaged|clean|dudoso","confidence_score":0.0,'
    '"damage_keywords":["keyword"],"damage_types":["motor"],'
    '"motivo":"explicacion breve"}'
    "\n\nDescripcion: "
)


# ---------------------------------------------------------------------------
# JSON extraction - robust against deepseek-r1 <think> blocks
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> dict[str, Any]:
    """Strip <think>...</think> blocks and extract the first JSON object."""
    clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {clean[:200]!r}")
    return json.loads(match.group())


def _clamp_confidence(value: Any, default: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return max(0.0, min(1.0, score))


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "si", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return default


def _as_clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    clean: list[str] = []
    for item in items:
        text = str(item).strip().lower()
        if text and text not in clean:
            clean.append(text[:60])
    return clean


def _keyword_hits(text: str) -> list[str]:
    haystack = text.casefold()
    return [keyword for keyword in _DAMAGE_KEYWORDS if keyword.casefold() in haystack]


def _normalize_report(data: dict[str, Any], source_text: str) -> ForensicReport:
    keyword_hits = _keyword_hits(source_text)
    raw_status = str(data.get("status", "")).strip().lower()
    tiene_averia = _as_bool(data.get("tiene_averia"), default=bool(keyword_hits))

    if raw_status in _VALID_STATUSES:
        status = raw_status
    elif tiene_averia:
        status = "damaged"
    else:
        status = "clean"

    if status == "damaged":
        tiene_averia = True
    elif status == "clean":
        tiene_averia = False

    default_confidence = 0.55 if status == "dudoso" else 0.80
    confidence_score = _clamp_confidence(data.get("confidence_score"), default_confidence)

    damage_keywords = _as_clean_list(data.get("damage_keywords"))
    for keyword in keyword_hits:
        if keyword not in damage_keywords:
            damage_keywords.append(keyword)

    damage_types = [
        item for item in _as_clean_list(data.get("damage_types"))
        if item in _DAMAGE_TYPES
    ]
    if status == "damaged" and not damage_types:
        damage_types = ["averia_generica"]

    motivo = str(data.get("motivo", "")).strip()
    if not motivo:
        motivo = "Sin descripcion de danos." if status == "clean" else "Posibles danos detectados."

    return ForensicReport(
        schema_version="v2",
        tiene_averia=tiene_averia,
        motivo=motivo,
        status=status,
        summary=motivo,
        confidence_score=confidence_score,
        damage_keywords=damage_keywords,
        damage_types=damage_types,
    )


def _fallback_report(message: str, *, status: str, confidence_score: float) -> ForensicReport:
    tiene_averia = status == "damaged"
    return ForensicReport(
        schema_version="v2",
        tiene_averia=tiene_averia,
        motivo=message,
        status=status,
        summary=message,
        confidence_score=confidence_score,
        damage_keywords=[],
        damage_types=["averia_generica"] if tiene_averia else [],
    )


# ---------------------------------------------------------------------------
# ForensicAgent
# ---------------------------------------------------------------------------

class ForensicAgent:
    def __init__(self) -> None:
        self._client = ollama.AsyncClient(host=_OLLAMA_HOST)
        self._semaphore = asyncio.Semaphore(_SEMAPHORE_SIZE)

    async def analyze(self, text: str, brand: str = "") -> ForensicReport:
        """
        Analyze one listing description.
        Semaphore caps parallel GPU requests to _SEMAPHORE_SIZE.
        Any parse failure returns status="damaged" so the pipeline remains safe.
        """
        async with self._semaphore:
            prompt = _PROMPT_PREFIX + text[:1_500]
            try:
                response = await self._client.chat(
                    model=_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    format="json",
                    think=False,
                    options={"temperature": 0},
                )
                data = _extract_json(response.message.content)
                return _normalize_report(data, text)
            except Exception as exc:
                markers = ("out of memory", "oom", "connection", "refused", "unavailable")
                oom = any(kw in str(exc).lower() for kw in markers)
                tag = "OOM/conexion" if oom else "respuesta malformada"
                print(f"  [FORENSIC WARN] {tag}: {exc!r} - marcado como averia por precaucion")
                return _fallback_report(
                    f"Error de procesamiento IA ({tag}).",
                    status="damaged",
                    confidence_score=0.35,
                )


# ---------------------------------------------------------------------------
# Batch orchestration
# ---------------------------------------------------------------------------

async def analyze_batch(
    listings: list[dict],
    agent: ForensicAgent,
    concurrency: int = _SEMAPHORE_SIZE,  # kept for API compatibility; agent controls the real limit
) -> list[dict]:
    """
    Enrich each listing dict with 'forensic_report', 'repair_cost_eur',
    and 'repair_cost_range_eur'.
    Concurrency is enforced by the agent's internal semaphore, not here.
    """
    async def _analyze_one(car: dict) -> dict:
        text = (car.get("description") or car.get("title") or "").strip()
        brand = car.get("brand", "")

        if not text:
            report = _fallback_report(
                "Sin texto disponible.",
                status="dudoso",
                confidence_score=0.0,
            )
        else:
            report = await agent.analyze(text=text, brand=brand)

        cost_range = RepairCostEngine.estimate_range(report, brand=brand)
        cost = RepairCostEngine._round_to_50(sum(cost_range) / 2)
        return {
            **car,
            "forensic_report": report,
            "repair_cost_eur": cost,
            "repair_cost_range_eur": cost_range,
        }

    results = await asyncio.gather(*[_analyze_one(car) for car in listings])
    return list(results)
