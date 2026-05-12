# SOP — Data Pipeline: Scrape → SQLite

**Tarea:** F1-T21  
**Estado:** Operacional  
**Última actualización:** 2026-05-07  
**Archivos clave:** `main.py`, `tools/scrape_cars.py`, `tools/utils/db.py`, `tools/market_catalog.py`, `tools/utils/valuation_engine.py`, `tools/utils/forensic_agent.py`, `tools/utils/telegram_notifier.py`

---

## 1. Visión General

El pipeline convierte anuncios de segunda mano en oportunidades de arbitraje calificadas y las persiste en SQLite. Tiene dos modos de ejecución:

| Modo | Comando | Comportamiento |
|------|---------|----------------|
| **Radar** (por defecto) | `python main.py` | Bucle infinito. Un burst cada `COOLDOWN_SECONDS` (900 s / 15 min). Filtra anuncios ya vistos. |
| **Histórico** | `python main.py --disable-brake --start-page N --pages M` | Un único burst, ignora historial, termina al completar. Útil para auditorías y backfill. |

---

## 2. Prerequisitos

### 2.1 Instalación de dependencias

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2.2 Variables de entorno (`.env`)

| Variable | Obligatoria | Default | Descripción |
|----------|-------------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Sí | — | Token del bot de Telegram para alertas |
| `TELEGRAM_CHAT_ID` | Sí | — | Chat ID donde se envían las oportunidades |
| `AGARTHA_DB_PATH` | No | `.tmp/agartha.db` | Ruta del fichero SQLite |
| `AGARTHA_DB_POOL_SIZE` | No | `5` | Conexiones en el pool async |
| `AGARTHA_DB_BUSY_TIMEOUT_MS` | No | `5000` | Timeout SQLITE_BUSY en ms |
| `AGARTHA_DB_MAX_RETRIES` | No | `5` | Reintentos con backoff exponencial |
| `AGARTHA_DB_RETRY_BASE_DELAY` | No | `0.05` | Delay base (s) para el backoff |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Endpoint Ollama para ForensicAgent |
| `GOOGLE_SHEET_ID` | No | `""` | Si se rellena, activa exportación a Sheets (deshabilitado por defecto) |
| `AGARTHA_PREFILTER_YEAR_MIN` | No | `""` | Año mínimo aceptado antes del cálculo ROI |
| `AGARTHA_PREFILTER_YEAR_MAX` | No | `""` | Año máximo aceptado antes del cálculo ROI |
| `AGARTHA_PREFILTER_PRICE_BAND` | No | `""` | Rango de precio `min:max`, por ejemplo `5000:18000` |
| `AGARTHA_PREFILTER_PRICE_MIN` | No | `""` | Precio mínimo explícito; tiene prioridad sobre `PRICE_BAND` |
| `AGARTHA_PREFILTER_PRICE_MAX` | No | `""` | Precio máximo explícito; tiene prioridad sobre `PRICE_BAND` |
| `AGARTHA_PREFILTER_SELLER_TYPE` | No | `""` | `private`, `professional` o lista separada por comas |

### 2.3 Sesiones Playwright

Antes de un run de producción, asegúrate de tener sesiones válidas en `.tmp/sessions/`:

```bash
python tools/generate_session.py
```

Ver `workflows/scraping_anti_bot.md` para el protocolo completo de gestión de sesiones y recuperación Datadome.

---

## 3. Arquitectura del Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  main.py → _run_pipeline()                                   │
│                                                             │
│  [1/5] MilanunciosScraper.scrape()                          │
│        ↓  lista bruta de listings (dicts)                   │
│  [1.5/5] MarketCatalog.update_batch()                       │
│          → pre-filtro ROI >= min_roi (default 5 %)          │
│        ↓  profitable_listings                               │
│  [2/5] ForensicAgent.analyze_batch()    ← Ollama (local)    │
│        ↓  listings enriquecidos con forensic_report         │
│  [3/5] ValuationEngine.compute()                            │
│        → market_price, roi_bruto, roi_neto por coche        │
│        ↓  analysed (lista de dicts con métricas)            │
│  [4/5] db.upsert_listing()              ← SQLite WAL        │
│        ↓  todos los listings persistidos                    │
│  [5/5] TelegramNotifier.send_opportunity()                  │
│        → alertas solo para: profitable AND NOT damaged      │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Pasos Detallados

### Paso 1 — Scraping (MilanunciosScraper)

**Archivo:** `tools/scrape_cars.py`  
**Parámetros clave:**

| Parámetro | Descripción |
|-----------|-------------|
| `max_pages` | Páginas por burst (default `BURST_MAX_PAGES=10`) |
| `seen_ids` | Set de `ad_id` ya conocidos; el scraper frena cuando los encuentra en modo radar |
| `start_page` | Página inicial (default 1; `--start-page N` en histórico) |
| `disable_brake` | Si `True`, ignora `seen_ids` y no frena ante overlap |

**Salida por listing:**

```python
{
    "portal":      "milanuncios",
    "ad_id":       "123456789",
    "brand":       "BMW",
    "model":       "320d",
    "year":        2019,
    "mileage":     145000,
    "price":       14500.0,
    "title":       "BMW 320d 2019 Diesel",
    "description": "Motor averiado…",
    "url":         "https://www.milanuncios.com/...",
    "scraped_at":  "2026-05-07T20:15:00",
}
```

Sesión y anti-bot: ver `workflows/scraping_anti_bot.md`.

### Paso 1.5 — Catálogo de Mercado y Pre-filtro

**Archivo:** `tools/market_catalog.py`

- Antes del catálogo se aplica un pre-filtro heurístico opcional desde `.env`.
- Variables soportadas: `AGARTHA_PREFILTER_YEAR_MIN`, `AGARTHA_PREFILTER_YEAR_MAX`, `AGARTHA_PREFILTER_PRICE_BAND`, `AGARTHA_PREFILTER_PRICE_MIN`, `AGARTHA_PREFILTER_PRICE_MAX`, `AGARTHA_PREFILTER_SELLER_TYPE`.
- Si un filtro está activo y el anuncio no tiene el campo necesario (`year`, `price` o `seller_type`), el anuncio se descarta para ese burst. Los `ad_id` descubiertos se guardan igualmente en radar para evitar repetir descartes.
- `MarketCatalog.update_batch(slug, prices)` actualiza precio medio por `(brand, model, year)`.
- `calculate_max_bid(market_avg, mileage, year)` devuelve el precio máximo justificado.
- Se calcula un ROI estimado; listings con ROI < `min_roi` se marcan `_profitable=False` y no pasan al análisis forense (ahorro de llamadas a Ollama).

### Paso 2 — Análisis Forense

**Archivo:** `tools/utils/forensic_agent.py`  
**Dependencia:** Ollama corriendo en `OLLAMA_BASE_URL`

- Solo procesa `profitable_listings`.
- Concurrencia configurable (default `concurrency=5`).
- Enriquece cada listing con:

```python
car["forensic_report"]   # ForensicReport(status, summary, damages, ...)
car["repair_cost_eur"]   # float — coste estimado de reparación
```

- `status` puede ser `"clean"`, `"damaged"`, `"unknown"`.
- Si Ollama no está disponible, el agente devuelve `status="unknown"` (no bloquea el pipeline).

### Paso 3 — Valoración de Mercado

**Archivo:** `tools/utils/valuation_engine.py`

- Agrupa por `(brand, model, year)`.
- Requiere muestra mínima (`MIN_SAMPLE=2`); grupos más pequeños lanzan `InsufficientDataError` y se omiten (no bloquean).
- Produce por listing:

```python
{
    "market_price": 18500.0,   # precio_ajustado o precio_mercado_base
    "roi":          27.6,      # ROI bruto %
    "roi_neto":     21.3,      # ROI neto (descontando repair_cost)
    "sample_size":  8,
}
```

### Paso 4 — Persistencia SQLite

**Archivo:** `tools/utils/db.py`

```python
await db.init_db()            # crea tablas si no existen + backup automático
await db.upsert_listing(car)  # INSERT OR UPDATE por (portal, ad_id)
```

Se persisten **todos** los listings (incluso no rentables), para análisis histórico. Los campos `market_price`, `roi_bruto`, `roi_neto` se rellenan solo si el listing pasó el paso de valoración.

**Backup automático:** al primer `init_db()` del proceso se crea `.tmp/backups/agartha_YYYYMMDD_HHMMSS.db`. No modifica la DB si el backup falla.

### Paso 5 — Alertas Telegram

Solo dispara si el listing cumple **ambas condiciones**:
1. `_profitable=True` (ROI >= min_roi tras valoración)
2. `forensic_report.status != "damaged"`

El mensaje incluye: marca/modelo, precio lista, precio mercado, ROI neto %, URL del anuncio, año, km y coste de reparación estimado.

---

## 5. Esquema SQLite

### Tabla `listings`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER PK | Auto-incremental |
| `portal` | TEXT | `"milanuncios"`, `"wallapop"`, etc. |
| `ad_id` | TEXT | ID único del anuncio en el portal |
| `brand` | TEXT | Marca del vehículo |
| `model` | TEXT | Modelo |
| `year` | INTEGER | Año de fabricación |
| `mileage` | INTEGER | Kilómetros |
| `price` | REAL | Precio de lista del anuncio |
| `market_price` | REAL | Precio medio de mercado calculado |
| `roi_bruto` | REAL | ROI bruto % |
| `roi_neto` | REAL | ROI neto % (descuenta repair_cost) |
| `repair_cost` | REAL | Coste estimado de reparación (EUR) |
| `forensic_status` | TEXT | `"clean"` / `"damaged"` / `"unknown"` / NULL |
| `forensic_summary` | TEXT | Resumen del análisis forense |
| `url` | TEXT | URL del anuncio |
| `scraped_at` | TEXT | ISO-8601 timestamp del scrape |
| UNIQUE | | `(portal, ad_id)` — evita duplicados cross-burst |

**ON CONFLICT:** actualiza `price`, `market_price`, `roi_bruto`, `roi_neto`, `repair_cost`, estado forense y `scraped_at`. El `id` original se preserva.

### Tabla `market_prices`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `slug` | TEXT PK | `brand-model-year` normalizado |
| `market_average_price` | REAL | Precio medio de mercado |
| `sample_size` | INTEGER | Número de muestras |
| `last_updated` | TEXT | ISO-8601 timestamp |

---

## 6. Modo Histórico vs Radar

### Radar (producción continua)

```bash
python main.py
# Opcional: ajustar parámetros
python main.py --pages 15 --min-roi 10
```

- Carga `seen_ids` desde `.tmp/last_seen_ids.json` al inicio.
- Tras cada burst, persiste los nuevos `ad_id` en ese archivo.
- El scraper frena (brake) al encontrar anuncios ya conocidos — evita re-scraping de páginas antiguas.
- Cooldown de 15 min entre bursts (configurable vía `COOLDOWN_SECONDS` en `main.py`).

### Histórico (backfill o auditoría)

```bash
# Páginas 1-10 (sin filtro de anuncios conocidos)
python main.py --disable-brake --pages 10

# Páginas 20-40 (auditoría de inventario más antiguo)
python main.py --disable-brake --start-page 20 --pages 20 --min-roi 0
```

- Ignora `seen_ids` completamente.
- Ejecuta un único burst y termina — no entra en el bucle radar.
- Útil para poblar la DB desde cero o auditar precios históricos.
- `--min-roi 0` incluye todos los listings en SQLite (incluso no rentables).

---

## 7. Parámetros CLI

```
python main.py [--start-page N] [--pages N] [--min-roi F] [--disable-brake]
```

| Flag | Default | Descripción |
|------|---------|-------------|
| `--start-page N` | `1` | Primera página a scraper en el primer burst |
| `--pages N` | `10` | Páginas por burst |
| `--min-roi F` | `5.0` | ROI mínimo % para pre-filtro y alertas |
| `--disable-brake` | off | Activa modo histórico (un burst, sin seen_ids) |

---

## 8. Configuración del Pool SQLite

El pool async (`tools/utils/db.py`) se puede ajustar via `.env` sin tocar código:

```dotenv
AGARTHA_DB_POOL_SIZE=5          # 5 conexiones concurrentes (suficiente para pipeline + API)
AGARTHA_DB_BUSY_TIMEOUT_MS=5000 # 5 s antes de lanzar SQLITE_BUSY
AGARTHA_DB_MAX_RETRIES=5        # reintentos con backoff exponencial (0.05 s base)
```

El modo WAL permite una conexión escritora simultánea con múltiples lectores — sin contención en el caso de uso actual (pipeline escribiendo + API leyendo).

---

## 9. Outputs Esperados

Al terminar un burst el log debe mostrar:

```
[1/5] Scraping Milanuncios...
      42 new listing(s) | 41 unique ID(s).

[1.5/5] Updating market catalog and filtering by max bid...
      18 profitable / 42 total after ROI >= 5.0% filter.

[2/5] Running forensic analysis on 18 listing(s)...
      3 damaged | avg estimated repair 850 EUR

[3/5] Computing market valuations...
      42 car(s) valued | 2 group(s) skipped (sample too small) | 0 group(s) skipped (error)
      15 clean profitable opportunity/ies ready for alert.

[4/5] Persisting 42 listing(s) to SQLite...
  [OK] 42 listing(s) upserted to .tmp/agartha.db

[5/5] Sending Telegram alerts (profitable + forensically clean)...
  [OK] 15/15 alert(s) sent.
```

---

## 10. Diagnóstico de Problemas Habituales

| Síntoma | Causa probable | Acción |
|---------|---------------|--------|
| `0 new listing(s)` en radar | `seen_ids` llenos + no hay anuncios nuevos | Normal si la web no ha actualizado; esperar siguiente burst |
| `Scraping failed` | Datadome / sesión quemada | Ver `workflows/scraping_anti_bot.md` sección 4 |
| `InsufficientDataError` en todos los grupos | Burst demasiado pequeño | Aumentar `--pages` o usar modo histórico para acumular muestra |
| `SQLite write failed: database is locked` | Pool agotado o proceso externo | Aumentar `AGARTHA_DB_POOL_SIZE` o `AGARTHA_DB_BUSY_TIMEOUT_MS` |
| ForensicAgent `status=unknown` en todos | Ollama no responde | `ollama serve` + `ollama pull <model>` |
| `0 alert(s) sent` tras valoración normal | Todos los listings con `status=damaged` | Revisar prompt ForensicAgent (ver F1-T08) |
| Telegram `401 Unauthorized` | Token incorrecto o bot eliminado | Regenerar token en `@BotFather`, actualizar `.env` |

---

## 11. Estructura de Directorios Relevante

```
.tmp/
├── agartha.db              ← Base de datos SQLite principal
├── last_seen_ids.json      ← IDs vistos en radar (persiste entre bursts)
├── sessions/               ← Pool de sesiones Playwright
│   ├── session_001.json
│   └── burnt/              ← Sesiones detectadas (para post-mortem)
└── backups/                ← Backups automáticos pre-init
    └── agartha_YYYYMMDD_HHMMSS.db
```

---

## 12. Próximas Mejoras (Backlog)

- **F1-T12**: Añadir columnas `condition_score`, `images_count`, `seller_type`, `location`, `price_history_json` al schema.
- **F1-T13**: Deduplicación cross-portal (mismo coche en Milanuncios + Wallapop).
- **F1-T14**: Acumulación de serie temporal de precios en `price_history_json`.
- **F1-T05**: Ejecución concurrente Milanuncios + Wallapop con `asyncio.gather`.
