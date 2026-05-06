"""
ForensicAgent — local AI damage triage via Ollama (deepseek-r1:8b).

Zero cloud cost. Runs fully offline against localhost:11434.
Semaphore(1) ensures the local GPU processes one request at a time — prevents OOM on RTX 3060.

Output contract (backward-compatible with main.py):
    report.status   → "damaged" | "clean" | "dudoso"
    report.summary  → human-readable explanation
    report.tiene_averia → bool

RepairCostEngine is preserved as a stub — part-level cost estimation requires
a structured pass (future iteration). Returns 0 for now.
"""

import asyncio
import json
import re
from typing import Optional

import ollama
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

class ForensicReport(BaseModel):
    tiene_averia: bool
    motivo: str
    status: str   # "damaged" | "clean" | "dudoso"
    summary: str  # mirrors motivo — kept for pipeline compatibility


# ---------------------------------------------------------------------------
# Repair cost stub
# ---------------------------------------------------------------------------

class RepairCostEngine:
    """Part-level cost estimation requires structured output (future iteration).
    Returns 0 until a fine-grained analysis pass is added."""

    @staticmethod
    def estimate(report: ForensicReport, brand: str = "") -> float:
        return 0.0


# ---------------------------------------------------------------------------
# Ollama configuration
# ---------------------------------------------------------------------------

_OLLAMA_HOST    = "http://localhost:11434"
_MODEL          = "deepseek-r1:8b"
_SEMAPHORE_SIZE = 1

_PROMPT_PREFIX = (
    "/no_think\n"  # disable deepseek-r1 chain-of-thought — cuts latency from ~200s to ~5s
    "Analiza esta descripción de un coche. "
    "¿Menciona averías, golpes, necesidad de grúa o piezas rotas? "
    'Responde ÚNICAMENTE con un JSON válido: '
    '{"tiene_averia": true/false, "motivo": "explicación breve"}'
    "\n\nDescripción: "
)


# ---------------------------------------------------------------------------
# JSON extraction — robust against deepseek-r1 <think> blocks
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> dict:
    """Strip <think>…</think> blocks and extract the first JSON object."""
    clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    match = re.search(r"\{[^{}]*\}", clean, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {clean[:200]!r}")
    return json.loads(match.group())


# ---------------------------------------------------------------------------
# ForensicAgent
# ---------------------------------------------------------------------------

class ForensicAgent:
    def __init__(self) -> None:
        self._client    = ollama.AsyncClient(host=_OLLAMA_HOST)
        self._semaphore = asyncio.Semaphore(_SEMAPHORE_SIZE)

    async def analyze(self, text: str, brand: str = "") -> ForensicReport:
        """
        Analyze one listing description.
        Semaphore caps parallel GPU requests to _SEMAPHORE_SIZE.
        Any parse failure returns status="dudoso" so the pipeline never crashes.
        """
        async with self._semaphore:
            prompt = _PROMPT_PREFIX + text[:1_500]
            try:
                response = await self._client.chat(
                    model=_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    format="json",
                    think=False,               # API-level disable for r1 CoT
                    options={"temperature": 0},
                )
                data         = _extract_json(response.message.content)
                tiene_averia = bool(data.get("tiene_averia", False))
                motivo       = str(data.get("motivo", "")).strip() or "Sin descripción de daños."
                return ForensicReport(
                    tiene_averia = tiene_averia,
                    motivo       = motivo,
                    status       = "damaged" if tiene_averia else "clean",
                    summary      = motivo,
                )
            except Exception as exc:
                oom = any(kw in str(exc).lower() for kw in ("out of memory", "oom", "connection", "refused", "unavailable"))
                tag = "OOM/conexión" if oom else "respuesta malformada"
                print(f"  [FORENSIC WARN] {tag}: {exc!r} — marcado como avería por precaución")
                msg = f"Error de procesamiento IA ({tag})."
                return ForensicReport(
                    tiene_averia = True,
                    motivo       = msg,
                    status       = "damaged",
                    summary      = msg,
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
    Enrich each listing dict with 'forensic_report' and 'repair_cost_eur'.
    Concurrency is enforced by the agent's internal semaphore, not here.
    """
    async def _analyze_one(car: dict) -> dict:
        text  = (car.get("description") or car.get("title") or "").strip()
        brand = car.get("brand", "")

        if not text:
            report = ForensicReport(
                tiene_averia = False,
                motivo       = "Sin texto disponible.",
                status       = "dudoso",
                summary      = "Sin texto disponible.",
            )
        else:
            report = await agent.analyze(text=text, brand=brand)

        cost = RepairCostEngine.estimate(report, brand=brand)
        return {**car, "forensic_report": report, "repair_cost_eur": cost}

    results = await asyncio.gather(*[_analyze_one(car) for car in listings])
    return list(results)
