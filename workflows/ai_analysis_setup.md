# SOP — AI Analysis Setup: ForensicAgent + RepairCostEngine

**Tarea:** F1-T20  
**Estado:** Operacional  
**Última actualización:** 2026-05-08  
**Archivos clave:** `tools/utils/forensic_agent.py`, `tools/test_vllm.py`, `main.py`

---

## 1. Visión General

La capa de análisis IA evalúa cada anuncio de segunda mano para detectar daños mecánicos, siniestros y riesgos documentales **sin coste de API en la nube**. Todo corre localmente vía Ollama sobre una RTX 3060.

El análisis se activa únicamente sobre anuncios **pre-filtrados como potencialmente rentables** (ROI ≥ `min_roi`%), reduciendo la carga GPU a los listings que de verdad importan.

### Componentes

| Componente | Archivo | Rol |
|-----------|---------|-----|
| `ForensicAgent` | `tools/utils/forensic_agent.py` | Llama al modelo vía Ollama y retorna `ForensicReport` |
| `RepairCostEngine` | `tools/utils/forensic_agent.py` | Estima coste de reparación EUR por tipo de daño y marca |
| `analyze_batch()` | `tools/utils/forensic_agent.py` | Orquesta análisis batch con concurrencia controlada |
| `test_vllm.py` | `tools/test_vllm.py` | Benchmark throughput/latencia vLLM vs Ollama |

---

## 2. Prerequisitos

### 2.1 Hardware

| Componente | Mínimo | Recomendado |
|-----------|--------|-------------|
| GPU VRAM | 8 GB | 12 GB (RTX 3060) |
| RAM sistema | 16 GB | 32 GB |

El modelo `deepseek-r1:8b` ocupa ~5 GB VRAM en cuantización Q4. Con la RTX 3060 (12 GB) hay margen suficiente.

### 2.2 Ollama

```bash
# Instalar Ollama (Linux/WSL)
curl -fsSL https://ollama.com/install.sh | sh

# Windows — descargar desde https://ollama.com/download

# Arrancar el servidor
ollama serve
```

Verificar que el servidor responde:

```bash
curl http://localhost:11434/api/tags
```

### 2.3 Modelo deepseek-r1:8b

```bash
ollama pull deepseek-r1:8b
```

Descarga ~5 GB. Solo necesario la primera vez.

### 2.4 Dependencias Python

```bash
pip install -r requirements.txt
```

El paquete `ollama` (PyPI) ya está incluido en `requirements.txt`.

---

## 3. Arquitectura del ForensicAgent

```
main.py
  │
  ├─ analyze_batch(profitable_listings, agent)
  │       │
  │       └─ ForensicAgent.analyze(text, brand)   ← asyncio.Semaphore(1)
  │               │
  │               ├─ ollama.AsyncClient.chat(model="deepseek-r1:8b", format="json")
  │               │       └─ _extract_json()       ← strip <think> blocks
  │               │       └─ _normalize_report()   ← schema v2 + keyword fallback
  │               │
  │               └─ ForensicReport (schema v2)
  │
  └─ RepairCostEngine.estimate_range(report, brand)
          │
          └─ (min_eur, max_eur) → repair_cost_range_eur
```

### Semáforo de concurrencia

El agente usa `asyncio.Semaphore(1)` internamente. Esto serializa las llamadas GPU aunque `analyze_batch` lance N tareas concurrentes. Evita OOM en GPUs < 16 GB.

---

## 4. ForensicReport — Schema v2

El modelo devuelve un JSON que se normaliza al siguiente schema:

```python
class ForensicReport(BaseModel):
    schema_version: str       # siempre "v2"
    tiene_averia: bool        # True si hay evidencia explícita de daño
    status: str               # "damaged" | "clean" | "dudoso"
    confidence_score: float   # 0.0 – 1.0
    damage_keywords: list[str]  # palabras clave encontradas en el texto
    damage_types: list[str]   # categorías: "motor", "siniestro", etc.
    motivo: str               # explicación breve
    summary: str              # alias de motivo (compatibilidad pipeline)
```

#### Reglas de normalización (`_normalize_report`)

| Condición | Acción |
|-----------|--------|
| `status` no en `{damaged, clean, dudoso}` | Se infiere por `tiene_averia` |
| `status == "damaged"` | `tiene_averia = True` forzado |
| `status == "clean"` | `tiene_averia = False` forzado |
| `confidence_score` fuera de [0, 1] | Clamp a rango |
| `confidence_score` ausente | Default: 0.55 (dudoso) / 0.80 (otros) |
| `damage_keywords` vacío | Se añaden keyword hits del texto fuente |
| `damage_types` con tipo no reconocido | Se descarta |
| `damage_types` vacío + `status == "damaged"` | `["averia_generica"]` |

#### Política de fallo seguro

Ante cualquier error (conexión rechazada, OOM, JSON malformado), el agente devuelve:

```python
ForensicReport(status="damaged", confidence_score=0.35, ...)
```

El pipeline principal descarta automáticamente los listings `"damaged"` para las alertas Telegram, así que marcarlos como dañados ante la duda es la decisión conservadora correcta.

---

## 5. Tipos de Daño y Palabras Clave

### Tipos permitidos (`damage_types`)

| Tipo | Descripción | Coste base (EUR) |
|------|-------------|-----------------|
| `motor` | Averías mecánicas del motor | 1.800 – 4.500 |
| `transmision` | Caja de cambios, embrague | 900 – 2.500 |
| `carroceria` | Golpes, abolladuras | 600 – 2.200 |
| `chasis` | Bastidor, estructura | 2.500 – 6.500 |
| `airbag` | Airbags desplegados | 900 – 2.600 |
| `documentacion_itv` | ITV desfavorable o sin ITV | 150 – 700 |
| `frenos` | Frenos, ABS | 250 – 800 |
| `suspension` | Suspensión | 350 – 1.200 |
| `direccion` | Dirección | 500 – 1.500 |
| `electrico` | Centralita, eléctrico | 250 – 1.600 |
| `siniestro` | Accidente con partes afectadas | 2.000 – 8.000 |
| `inundacion` | Inundado | 1.500 – 6.000 |
| `incendio` | Incendio | 2.500 – 9.000 |
| `averia_generica` | Fallback cuando no hay tipo específico | 500 – 2.000 |

### Palabras clave monitorizadas (`damage_keywords`)

El sistema busca ~40 términos en el texto del anuncio como red de seguridad adicional al output del modelo:

```
averia, averiado, no arranca, no funciona, fallo motor, motor roto, motor gripado,
culata, junta culata, turbo, embrague, caja de cambios, inyectores, airbag,
siniestro, accidentado, golpe, choque, colision, chasis, bastidor, estructura,
itv desfavorable, itv negativa, sin itv, inundado, incendio, para reparar, ...
```

---

## 6. RepairCostEngine

Estima el rango de coste de reparación combinando:

1. **Rangos base** por tipo de daño (tabla `_BASE_RANGES_EUR`)
2. **Multiplicador de marca** (`_BRAND_MULTIPLIERS`): desde 0.85 (Dacia) hasta 1.70 (Porsche)
3. **Ajuste por `confidence_score`**: rangos se reducen si confianza < 1.0
4. **Descuento dudoso**: si `status == "dudoso"`, min×0.50 / max×0.60
5. **Daños múltiples**: segundo daño + 45% min / 35% max del primero

```python
# Ejemplo de uso
cost_range = RepairCostEngine.estimate_range(report, brand="BMW")
# → (2250.0, 5850.0)

cost_midpoint = RepairCostEngine.estimate(report, brand="BMW")
# → 4050.0
```

Los resultados se redondean a múltiplos de 50 EUR.

El coste estimado se almacena en los listings como:
- `repair_cost_eur` — punto medio, usado para ROI neto
- `repair_cost_range_eur` — tupla (min, max)

### ROI Neto

```
roi_neto = (market_price - (list_price + repair_cost_eur)) / list_price * 100
```

Solo los listings con `status != "damaged"` y ROI neto positivo reciben alerta Telegram.

---

## 7. Integración en el Pipeline Principal

La capa AI se activa en el **Step 2** de `main.py`, después del pre-filtro financiero:

```python
# Step 2: Forensic analysis (profitable listings only)
forensic_agent = ForensicAgent()
enriched = await analyze_batch(profitable_listings, agent=forensic_agent, concurrency=5)
```

El parámetro `concurrency=5` es nominal — el `Semaphore(1)` interno del agente serializa las llamadas reales. No hay ventaja en subirlo hasta que el semáforo se amplíe.

### Flujo completo

```
[1/5] Scrape Milanuncios + Wallapop
[1.5/5] Market catalog → filtro ROI ≥ min_roi%
[2/5] ForensicAgent.analyze() en profitable_listings   ← AQUÍ
[3/5] ValuationEngine — ROI bruto + ROI neto
[4/5] SQLite upsert
[5/5] Telegram alerts — solo status != "damaged"
```

---

## 8. Variables de Entorno

| Variable | Obligatoria | Default | Descripción |
|----------|-------------|---------|-------------|
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Endpoint del servidor Ollama |

El modelo y los parámetros del agente están hardcodeados en `forensic_agent.py`:

```python
_OLLAMA_HOST = "http://localhost:11434"
_MODEL       = "deepseek-r1:8b"
_SEMAPHORE_SIZE = 1
```

Para cambiar el modelo editar estas constantes directamente.

---

## 9. Benchmark vLLM vs Ollama — `tools/test_vllm.py`

Herramienta de benchmark para comparar throughput y latencia entre vLLM y Ollama.

### Uso básico

```bash
# Arrancar vLLM primero (si se quiere comparar)
vllm serve deepseek-r1:8b --host 127.0.0.1 --port 8000

# Benchmark ambos providers
python tools/test_vllm.py --providers both --model deepseek-r1:8b

# Solo Ollama (caso habitual)
python tools/test_vllm.py --providers ollama --requests 20 --concurrency 1

# Solo vLLM con modelo GPTQ
python tools/test_vllm.py --providers vllm \
    --vllm-model TheBloke/Mistral-7B-Instruct-v0.2-GPTQ \
    --requests 20 --concurrency 2
```

### Parámetros

| Flag | Default | Descripción |
|------|---------|-------------|
| `--providers` | `both` | `vllm`, `ollama`, o `both` |
| `--model` | `deepseek-r1:8b` | Modelo para ambos providers |
| `--vllm-model` | — | Override solo para vLLM |
| `--ollama-model` | — | Override solo para Ollama |
| `--requests` | `8` | Total de requests a lanzar |
| `--concurrency` | `1` | Workers paralelos |
| `--max-tokens` | `64` | Tokens máximos por respuesta |
| `--timeout` | `120` | Timeout por request (segundos) |
| `--output-dir` | `.tmp/` | Directorio para guardar reportes |

### Métricas recogidas

- `throughput_req_s` — requests por segundo
- `tokens_s` — tokens generados por segundo
- `latency_ms_avg / p50 / p95` — latencias en milisegundos
- `gpu_before / gpu_after` — snapshot VRAM via `nvidia-smi`

Los reportes se guardan en `.tmp/vllm_benchmark_YYYYMMDD_HHMMSS.{json,md}`.

### Prompts de prueba

El benchmark usa 4 prompts rotatorios que simulan el uso real del ForensicAgent (detección de averías en texto español).

---

## 10. Decisión de Stack: vLLM vs Ollama

| Criterio | Ollama | vLLM |
|----------|--------|------|
| Setup | Un comando | Requires CUDA toolkit + pip install vllm |
| Latencia (p50, RTX 3060) | ~800-2000 ms | ~300-800 ms |
| Throughput | 1 req/s | 2-4 req/s |
| Quantización | Q4 built-in | GPTQ/AWQ externo |
| Memoria | ~5 GB Q4 | ~5 GB Q4 |
| API | Propia + OpenAI-compatible | OpenAI-compatible |
| Estabilidad | Alta (producción probada) | Alta |

**Decisión actual:** Ollama en producción. La latencia extra (~1-2 s/listing) es aceptable porque el análisis forense solo corre sobre listings pre-filtrados como rentables (típicamente < 50/burst). Si el volumen crece a > 200 listings/burst, migrar a vLLM.

---

## 11. Troubleshooting

### El agente siempre devuelve `status="damaged"`

Causas habituales:
1. Ollama no está corriendo → `ollama serve`
2. Modelo no descargado → `ollama pull deepseek-r1:8b`
3. Error de conexión → verificar `curl http://localhost:11434/api/tags`

El fallo seguro intencional marca como `damaged` ante cualquier error de conexión. Revisar los logs `[FORENSIC WARN]` en stdout.

### OOM en la GPU

El `Semaphore(1)` evita paralelismo GPU. Si aun así ocurre OOM:
1. Cerrar otras aplicaciones GPU
2. Usar modelo más pequeño: `ollama pull deepseek-r1:1.5b` y actualizar `_MODEL`
3. Reducir `--max-tokens` en el benchmark

### El modelo genera texto en lugar de JSON

`deepseek-r1:8b` puede ignorar `format="json"` ocasionalmente. `_extract_json()` maneja esto buscando el primer `{...}` en la respuesta y descartando bloques `<think>...</think>`.

### `ollama` no disponible en el entorno

Si Ollama no está instalado, `ForensicAgent` falla en la importación. Para entornos sin GPU (CI, tests), usar el mock:

```python
from unittest.mock import AsyncMock, patch
with patch("tools.utils.forensic_agent.ollama"):
    agent = ForensicAgent()
```

Los tests en `tests/test_forensic_agent.py` ya lo hacen así.

---

## 12. Añadir Nuevos Tipos de Daño

1. Añadir la entrada en `RepairCostEngine._BASE_RANGES_EUR`
2. Añadir mappings en `RepairCostEngine._KEYWORD_TYPE_HINTS`
3. Añadir el tipo en la constante `_DAMAGE_TYPES` del módulo
4. Actualizar el `_PROMPT_PREFIX` con el nuevo tipo en la lista "Tipos permitidos"
5. Ejecutar `python -m pytest tests/test_forensic_agent.py` para verificar que no hay regresiones
