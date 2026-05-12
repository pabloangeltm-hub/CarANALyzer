# Agartha — Master Execution Roadmap

> **Framework WAT** | Versión objetivo: SaaS B2B en producción comercial
> Estado actual: Scrapers Python + SQLite básico → Meta: Suscripciones activas, Dashboard B2B, VPS desplegado

---

## Estado Actual del Sistema

| Componente | Estado | Archivo clave |
|---|---|---|
| Scraper Milanuncios (Playwright + stealth) | ✅ Funcional | `tools/scrape_cars.py` |
| Scraper Wallapop (REST API) | ⚠️ 403 parcial | `tools/scrape_cars.py` |
| Motor de valoración estadística | ✅ Funcional | `tools/utils/valuation_engine.py` |
| Agente forense Ollama (deepseek-r1:8b) | ✅ Funcional | `tools/utils/forensic_agent.py` |
| SQLite CRM (WAL mode, 2 tablas) | ✅ Funcional | `tools/utils/db.py` |
| Notificador Telegram | ✅ Funcional | `tools/utils/telegram_notifier.py` |
| Orquestador radar 24/7 | ✅ Funcional | `main.py` |
| FastAPI B2B Catalog (MVP) | ⚠️ Un solo endpoint, auth básica | `tools/catalog_app.py` |
| Auth multi-tenant (JWT + API keys) | ❌ No existe | — |
| Stripe / Monetización | ❌ No existe | — |
| Dashboard Frontend (SPA) | ⚠️ Jinja2 básico | `tools/templates/` |
| Tests unitarios / integración | ❌ No existen | — |
| Docker / DevOps | ❌ No existe | — |
| Monitorización (Prometheus/Grafana) | ❌ No existe | — |

---

## Arquitectura Target

```
Internet
    │
    ▼
[Nginx + SSL / Let's Encrypt]
    │
    ├─── /api/* ──────► [FastAPI Service :8000]
    │                         │
    │                    [JWT Auth Middleware]
    │                    [Rate Limiter / Plan Guard]
    │                    [Audit Logger]
    │                         │
    │                    [aiosqlite CRM]──► [SQLite WAL]
    │                         │
    │                    [Stripe Webhooks]
    │
    ├─── /* ──────────► [Frontend SPA (nginx static)]
    │
    └─── Pipeline (internal, no expuesto)
              │
              ▼
         [main.py Radar 24/7]
              │
    ┌─────────┼──────────┐
    ▼         ▼           ▼
[Milanuncios] [Wallapop] [Futuros portales]
    │
    ▼
[Session Pool / Anti-bot]
    │
    ▼
[ForensicAgent — Ollama local]
    │
    ▼
[ValuationEngine — estadístico]
    │
    ▼
[SQLite CRM] ──► [Telegram Alerts]
              └──► [FastAPI reads]
```

---

## Tech Stack Decisions

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| Scraping | Playwright + stealth (evaluar Scrapling) | Anti-bot battle-tested; Scrapling como alternativa más ligera |
| LLM local | Ollama deepseek-r1:8b (evaluar vLLM) | Sin coste cloud; RTX 3060 limita concurrencia |
| API | FastAPI + aiosqlite | Async nativo, OpenAPI automático, tipado Pydantic |
| Base de datos | SQLite WAL → path a PostgreSQL | Simplicidad ahora; migración limpia cuando concurrencia lo requiera |
| Auth | JWT HS256 + API Keys (SHA-256) | Estándar B2B, sin OAuth overhead |
| Pagos | Stripe (stripe-python) | Estándar industria, webhooks robustos |
| Frontend | **Por determinar — Claude ejecuta `/find-skills`** | Se evalúa en Fase 3 |
| Email transaccional | Resend (primario) / SendGrid (fallback) | API simple, entregabilidad alta |
| DevOps | Docker + Nginx + GitHub Actions | VPS commodity, CI/CD sin fricciones |
| Monitorización | Prometheus + Grafana + Telegram | Alertas en tiempo real, dashboards gratuitos |
| Logs | structlog (JSON) + logrotate | Parseables, rotativos, sin coste |

---

## FASE 1 — Data Pipeline & AI Core

### Objetivo
Elevar la fiabilidad del scraping al 95%+ de páginas procesadas sin bloqueo manual, paralelizar fuentes, implementar estimación real de costes de reparación y fortalecer la capa de persistencia SQLite.

### SOPs a crear
| SOP | Ruta | Contenido |
|-----|------|-----------|
| Scraping Anti-Bot | `workflows/scraping_anti_bot.md` | Gestión session pool, protocolo de recuperación Datadome, rotación de IPs, métricas de bloqueo |
| AI Analysis Setup | `workflows/ai_analysis_setup.md` | Configuración Ollama/vLLM, selección de modelo, gestión de GPU (RTX 3060 OOM prevention), latencias esperadas |
| Data Pipeline | `workflows/data_pipeline.md` | Pipeline scrape → filtro → forense → valoración → SQLite; variables de configuración; modo histórico vs radar |

### Tools a desarrollar / modificar

| ID | Acción | Archivo | Descripción |
|----|--------|---------|-------------|
| F1-T01 | Investigar + PoC | `tools/benchmark_scrapers.py` (NEW) | Instalar Scrapling, ejecutar 20 páginas Milanuncios, registrar block rate y latencia vs Playwright |
| F1-T02 | Evaluar | `tools/benchmark_scrapers.py` | Comparativa formal: Scrapling vs Playwright — cobertura, velocidad, tasa de éxito Datadome |
| F1-T03 | Modificar | `tools/scrape_cars.py` | Integrar Scrapling como backend si PoC demuestra mejora ≥ 20% en block rate |
| F1-T04 | Corregir | `tools/scrape_cars.py` | Wallapop: corregir auth headers (`x-signature`, `x-timestamp`) para resolver 403 |
| F1-T05 | Implementar | `tools/scrape_cars.py` | Orchestration concurrente: `asyncio.gather(milanuncios, wallapop)` — pipeline multi-source en paralelo |
| F1-T06 | Crear | `tools/replenish_sessions.py` (NEW) | Auto-replenishment de session pool vía 2captcha API cuando pool < 5 sesiones válidas |
| F1-T07 | Modificar | `tools/scrape_cars.py` | Pre-filtro heurístico configurable: año_min/max desde .env, banda de precio, seller_type |
| F1-T08 | Modificar | `tools/utils/forensic_agent.py` | Mejorar prompt de daños: añadir confidence_score (0–1), ampliar keywords de avería |
| F1-T09 | Implementar | `tools/utils/forensic_agent.py` | RepairCostEngine real: tabla marca/tipo_daño → coste estimado (rango min-max EUR) |
| F1-T10 | Evaluar | `tools/test_vllm.py` (NEW) | Benchmark vLLM vs Ollama: throughput req/s, latencia p50/p95, VRAM usage en RTX 3060 |
| F1-T11 | Modificar | `tools/utils/db.py` | Migrar a aiosqlite: todas las operaciones DB async; connection pool con timeout y retry on SQLITE_BUSY |
| F1-T12 | Modificar | `tools/utils/db.py` | Migración de schema: añadir columnas `condition_score REAL`, `images_count INT`, `seller_type TEXT`, `location TEXT`, `price_history_json TEXT` |
| F1-T13 | Implementar | `tools/utils/db.py` | Cross-portal deduplicación: detectar mismo vehículo en Milanuncios + Wallapop por (brand, model, year, price ±5%, mileage ±10%) |
| F1-T14 | Implementar | `tools/utils/db.py` | Time-series de precios: `price_history_json` acumula `[{price, scraped_at}]` por ad_id |
| F1-T15 | Integrar | `tools/utils/request_handler.py` | Proxy rotation: ScrapingBee / BrightData como fallback cuando session pool < 3 y IP bloqueada |
| F1-T16 | Crear | `tests/test_valuation_engine.py` (NEW) | Tests unitarios ValuationEngine: muestra mínima, trim de outliers, ajuste mileage, ROI calc — cobertura ≥ 90% |
| F1-T17 | Crear | `tests/test_forensic_agent.py` (NEW) | Tests unitarios ForensicAgent: mock Ollama, extracción JSON, fallback safe, analyze_batch concurrencia |
| F1-T18 | Crear | `tests/test_scraper.py` (NEW) | Tests unitarios parsers: parse_price, parse_mileage, parse_year, make_slug, calculate_max_bid |
| F1-T19 | SOP | `workflows/scraping_anti_bot.md` | Claude Code redacta SOP completo |
| F1-T20 | SOP | `workflows/ai_analysis_setup.md` | Claude Code redacta SOP completo |
| F1-T21 | SOP | `workflows/data_pipeline.md` | Claude Code redacta SOP completo |

### Criterios de Aceptación — Fase 1 CERRADA cuando:
- [ ] PoC Scrapling documentado con métricas: block rate, latencia p50, cobertura de campos
- [ ] Scraper ejecuta 50 páginas consecutivas sin bloqueo manual en horario de tráfico normal
- [ ] Wallapop devuelve resultados reales (≥ 10 listings por búsqueda estándar)
- [ ] Pipeline procesa Milanuncios + Wallapop en paralelo en < 12 minutos para 10 páginas cada uno
- [ ] RepairCostEngine retorna rango de coste (no stub 0.0) para los 10 tipos de daño más comunes
- [ ] ForensicAgent con confidence_score en todos los reports
- [ ] SQLite opera sin errores SQLITE_BUSY bajo 5 escritores concurrentes (test de carga)
- [ ] aiosqlite integrado: 0 llamadas síncronas `sqlite3` en el pipeline principal
- [ ] Tests unitarios: `valuation_engine` ≥ 90% coverage, `forensic_agent` ≥ 80%, parsers ≥ 95%
- [ ] Schema migration ejecutada sin pérdida de datos en DB existente

---

## FASE 2 — API Layer & B2B Logic

### Objetivo
Construir una API REST producción-grade que exponga todos los datos del pipeline con filtros dinámicos, métricas de mercado, arquitectura multi-tenant y rate limiting por plan.

### SOPs a crear
| SOP | Ruta | Contenido |
|-----|------|-----------|
| API Layer | `workflows/api_layer.md` | Catálogo completo de endpoints, flujo de autenticación, rate limits por plan, ejemplos curl, códigos de error |

### Tools a desarrollar / modificar

| ID | Acción | Archivo | Descripción |
|----|--------|---------|-------------|
| F2-T01 | Crear | `tools/api/` (NEW package) | Reestructurar FastAPI: `app.py`, `routers/`, `schemas/`, `models/`, `dependencies/`, `middleware/` |
| F2-T02 | Crear | `tools/api/schemas/listings.py` | Pydantic: `ListingOut`, `ListingFilter`, `PaginatedListings`, `ListingDetail` |
| F2-T03 | Crear | `tools/api/schemas/market.py` | Pydantic: `MarketStatsOut`, `BrandMetrics`, `ROIHistogram`, `PriceTrend` |
| F2-T04 | Crear | `tools/api/schemas/dealer.py` | Pydantic: `DealerOut`, `DealerCreate`, `DealerUpdate`, `PlanInfo` |
| F2-T05 | Crear | `tools/api/schemas/auth.py` | Pydantic: `TokenOut`, `LoginIn`, `APIKeyOut`, `APIKeyCreate` |
| F2-T06 | Crear | `tools/api/routers/listings.py` | `GET /listings` (filter+paginate), `GET /listings/{id}`, `DELETE /listings/{id}` (soft delete) |
| F2-T07 | Crear | `tools/api/routers/market.py` | `GET /market/stats`, `GET /market/roi-histogram`, `GET /market/by-brand`, `GET /market/trends` |
| F2-T08 | Crear | `tools/api/routers/dealers.py` | `POST /dealers`, `GET /dealers/me`, `PATCH /dealers/me`, `GET /dealers` (admin only) |
| F2-T09 | Crear | `tools/api/routers/auth.py` | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/api-key` |
| F2-T10 | Crear | `tools/api/routers/admin.py` | `GET /admin/stats`, `PATCH /admin/dealers/{id}/plan`, `GET /admin/health` |
| F2-T11 | Crear | `tools/api/middleware/rate_limiter.py` | slowapi o custom: 100 req/min trial, 500 basic, 2000 premium — por API key |
| F2-T12 | Crear | `tools/api/middleware/audit_logger.py` | structlog middleware: request_id, dealer_id, endpoint, status_code, latency_ms → JSON |
| F2-T13 | Implementar | `tools/api/routers/listings.py` | Motor de filtros dinámicos: `brand`, `year_min/max`, `price_min/max`, `roi_min`, `forensic_status`, `portal`, `seller_type` |
| F2-T14 | Implementar | `tools/api/routers/listings.py` | Full-text search: `q` param con LIKE slugificado en brand + model |
| F2-T15 | Implementar | `tools/api/routers/listings.py` | Paginación por offset + cursor: `page`, `page_size` (max 100), `X-Total-Count` header |
| F2-T16 | Crear | `tools/api/dependencies/auth.py` | `get_current_dealer()`: valida JWT o API key, inyecta dealer en request |
| F2-T17 | Crear | `tools/api/dependencies/db.py` | `get_db()`: async context manager aiosqlite con pool |
| F2-T18 | Implementar | `tools/api/app.py` | Error handlers RFC 7807 Problem Details para 400/401/403/404/422/429/500 |
| F2-T19 | Configurar | `tools/api/app.py` | CORS: allowlist por entorno (dev: *, prod: dominio propio) |
| F2-T20 | Crear | `tools/api/routers/health.py` | `GET /health` (< 100ms), `GET /ready` (DB ping + pipeline status) |
| F2-T21 | Crear | `tests/test_api_listings.py` (NEW) | Integration tests router listings con DB de test |
| F2-T22 | Crear | `tests/test_api_market.py` (NEW) | Integration tests router market |
| F2-T23 | Crear | `tests/test_api_auth.py` (NEW) | Integration tests auth flow: login, refresh, API key |
| F2-T24 | Diseñar | `workflows/api_layer.md` | Claude Code: diseño del contrato API, ejemplos, errores — luego redacta SOP |

### Criterios de Aceptación — Fase 2 CERRADA cuando:
- [ ] OpenAPI docs en `/docs` con todos los endpoints documentados y ejemplos de respuesta
- [ ] Filtros dinámicos funcionan en combinación (AND lógico, todos los parámetros testeados)
- [ ] Paginación devuelve `X-Total-Count` correcto con cualquier combinación de filtros
- [ ] Rate limiting activo y retorna `429` con `Retry-After` header
- [ ] `/health` responde en < 100ms; `/ready` detecta caída de DB en < 500ms
- [ ] Tests de integración: 100% de routers con ≥ 1 test por endpoint
- [ ] Error responses en formato RFC 7807 en todos los casos de error
- [ ] 0 endpoints accesibles sin autenticación (excepto `/health`, `/ready`, `/docs`)

---

## FASE 3 — Frontend B2B Dashboard

### Objetivo
Construir el dashboard que los concesionarios usan para gestionar oportunidades, analizar el mercado y tomar decisiones de compra de alta ROI.

### SOPs a crear
| SOP | Ruta | Contenido |
|-----|------|-----------|
| Frontend B2B | `workflows/frontend_b2b.md` | Stack elegido, mapa de componentes, comandos de desarrollo, proceso de build y deploy |

### Tools a desarrollar / modificar

| ID | Acción | Archivo | Descripción |
|----|--------|---------|-------------|
| F3-T01 | Research | Claude ejecuta `/find-skills` | Descubrir skills para: tabla virtual scroll alto rendimiento, gráficas ROI, filtros reactivos, framework SPA |
| F3-T02 | Diseñar | `workflows/frontend_b2b.md` (borrador) | Claude: wireframes ASCII del dashboard (listings table, KPI widgets, filter panel, ROI charts) |
| F3-T03 | Decidir | `.agents/coordination.md` | Claude: selección final del stack frontend + component library basado en find-skills |
| F3-T04 | Scaffolding | `frontend/` (NEW) | Codex: inicializar proyecto según stack elegido por Claude |
| F3-T05 | Crear | `frontend/src/api/client.ts` | Typed fetch wrapper para todos los endpoints de la API |
| F3-T06 | Crear | `frontend/src/pages/Login.tsx` | Página de login: email + contraseña → JWT → localStorage, redirect |
| F3-T07 | Crear | `frontend/src/components/ListingsTable.tsx` | Tabla virtual scroll: columnas (brand, model, year, mileage, price, roi_neto, forensic_status), sort, row click |
| F3-T08 | Crear | `frontend/src/components/FilterPanel.tsx` | Panel filtros: brand dropdown, year range slider, price range, roi_min input, forensic select, debounce 300ms |
| F3-T09 | Crear | `frontend/src/components/ROIBarChart.tsx` | Gráfica barras: top 10 marcas por ROI medio — datos de `GET /market/by-brand` |
| F3-T10 | Crear | `frontend/src/components/PriceTrendChart.tsx` | Time-series precio por slug — datos de `GET /market/trends?slug=X` |
| F3-T11 | Crear | `frontend/src/components/ListingDrawer.tsx` | Drawer/modal detalle: forense completo, ValuationResult breakdown, precio historia, link portal |
| F3-T12 | Crear | `frontend/src/components/KPIWidgets.tsx` | 4 widgets: oportunidades hoy, ROI medio, listings totales, alertas enviadas — `GET /market/stats` |
| F3-T13 | Crear | `frontend/src/pages/Dashboard.tsx` | Layout principal: KPIWidgets + FilterPanel + ListingsTable + ROIBarChart |
| F3-T14 | Crear | `frontend/src/pages/MarketAnalysis.tsx` | Página análisis mercado: PriceTrendChart, ROI histograma, comparativa por marca |
| F3-T15 | Crear | `frontend/src/pages/AlertCenter.tsx` | Historial de alertas Telegram desde `GET /listings?sort=scraped_at&forensic_status=clean` |
| F3-T16 | Crear | `frontend/src/components/SavedSearches.tsx` | Watchlists: guardar filtro actual como búsqueda con nombre, persiste en API |
| F3-T17 | Implementar | `frontend/src/components/ExportButton.tsx` | CSV/Excel download: `GET /listings?format=csv` con filtros actuales |
| F3-T18 | Implementar | `frontend/` | Responsive layout: grid breakpoints tablet (1024px) + desktop (1280px+) |
| F3-T19 | Implementar | `frontend/` | Dark mode: CSS variables, detección `prefers-color-scheme`, toggle manual |
| F3-T20 | Implementar | `frontend/` | Loading states: skeleton loaders en tabla y widgets durante fetch |
| F3-T21 | Implementar | `frontend/` | Error boundaries: UI de fallback en errores API, retry automático en 401 (refresh JWT) |
| F3-T22 | Crear | `tests/e2e/dealer_flow.spec.ts` (NEW) | Playwright E2E: login → filtrar → ver detalle → exportar CSV — CI obligatorio |

### Criterios de Aceptación — Fase 3 CERRADA cuando:
- [ ] Tabla renderiza 500+ listings sin degradación de performance (< 100ms render time)
- [ ] Filtros actualizan resultados en < 400ms end-to-end (debounce + API + render)
- [ ] Gráfica ROI por marca renderiza sin errores con datos reales de producción
- [ ] Login funcional, sesión persiste tras F5, rutas protegidas redirigen a login
- [ ] Usable en tablet 1024px y desktop 1440px sin scroll horizontal
- [ ] Lighthouse score ≥ 85 en Performance, Accessibility, Best Practices
- [ ] E2E tests pasan en CI: login → filtrar → ver detalle → exportar

---

## FASE 4 — Auth & Monetización

### Objetivo
Sistema completo de autenticación multi-tenant, planes de suscripción B2B y procesamiento de pagos con Stripe con webhooks robustos y portal de autogestion para clientes.

### SOPs a crear
| SOP | Ruta | Contenido |
|-----|------|-----------|
| Auth & Monetización | `workflows/auth_monetization.md` | Sistema de roles, ciclo de vida API keys, límites por plan, flujo de registro |
| Stripe Integration | `workflows/stripe_integration.md` | Setup de productos en dashboard Stripe, testing local con Stripe CLI, portal de facturación |

### Tools a desarrollar / modificar

| ID | Acción | Archivo | Descripción |
|----|--------|---------|-------------|
| F4-T01 | Crear schema | `tools/api/migrations/002_dealers.sql` | Tabla `dealers`: id, name, email, password_hash, plan, api_key_hash, stripe_customer_id, created_at, active, calls_today |
| F4-T02 | Crear schema | `tools/api/migrations/003_api_usage.sql` | Tabla `api_usage`: id, dealer_id, date, endpoint, calls_count |
| F4-T03 | Crear schema | `tools/api/migrations/004_saved_searches.sql` | Tabla `saved_searches`: id, dealer_id, name, filter_json, created_at |
| F4-T04 | Implementar | `tools/api/services/auth_service.py` (NEW) | bcrypt password hashing, JWT HS256 (access 1h + refresh 7d), blacklist tokens en SQLite |
| F4-T05 | Implementar | `tools/api/services/api_key_service.py` (NEW) | Generar UUID v4, mostrar prefijo `agrt_`, almacenar SHA-256 hash, validar en requests |
| F4-T06 | Definir | `tools/api/models/plan.py` (NEW) | Enum planes: `trial` (50 req/día, 0 alertas), `basic` (500 req/día, alertas), `premium` (ilimitado, todas features) |
| F4-T07 | Implementar | `tools/api/middleware/plan_guard.py` (NEW) | Middleware: leer dealer.plan + calls_today, bloquear con 402 si supera límite, incrementar contador |
| F4-T08 | Integrar | `tools/api/services/stripe_service.py` (NEW) | stripe-python: crear Customer, crear Subscription, crear CheckoutSession, crear BillingPortal |
| F4-T09 | Crear | `tools/api/routers/payments.py` (NEW) | `POST /payments/checkout` (retorna URL), `GET /payments/portal` (retorna URL), `POST /webhooks/stripe` |
| F4-T10 | Implementar | `tools/api/routers/payments.py` | Webhook handler `checkout.session.completed`: activar dealer, asignar plan, confirmar API key |
| F4-T11 | Implementar | `tools/api/routers/payments.py` | Webhook handler `invoice.payment_failed`: suspender dealer (active=False), enviar email |
| F4-T12 | Implementar | `tools/api/routers/payments.py` | Webhook handler `customer.subscription.deleted`: downgrade a trial |
| F4-T13 | Implementar | `tools/api/routers/payments.py` | Verificación firma HMAC `STRIPE_WEBHOOK_SECRET` antes de procesar cualquier evento |
| F4-T14 | Integrar | `tools/api/services/email_service.py` (NEW) | Resend API: welcome email, payment_failed email, plan_upgrade confirmation |
| F4-T15 | Crear | `tools/api/routers/auth.py` | Extender: `POST /auth/register` → crear dealer + Stripe customer + enviar welcome email |
| F4-T16 | Implementar | `tools/api/routers/admin.py` | Override plan (admin), suspender dealer, listar revenue por mes vía Stripe API |
| F4-T17 | Crear | `tests/test_payments.py` (NEW) | Tests Stripe webhooks con payloads firmados ficticios; test plan_guard con mock DB |
| F4-T18 | Crear | `tests/test_auth_service.py` (NEW) | Tests bcrypt, JWT encode/decode, API key generation + validation |
| F4-T19 | SOP | `workflows/auth_monetization.md` | Claude Code redacta SOP completo |
| F4-T20 | SOP | `workflows/stripe_integration.md` | Claude Code redacta SOP completo |

### Criterios de Aceptación — Fase 4 CERRADA cuando:
- [ ] Flujo completo funcional: registro → email bienvenida → Stripe checkout → plan activo → acceso dashboard
- [ ] Webhook `checkout.session.completed` procesado en < 5 segundos end-to-end
- [ ] Plan limits enforcement: dealer trial bloqueado con 402 al superar 50 req/día
- [ ] Stripe Billing Portal accesible desde dashboard: upgrade/downgrade/cancelación self-serve
- [ ] Email de bienvenida enviado en < 30s tras registro exitoso (Resend)
- [ ] API key rotation sin interrumpir sesión activa del dealer
- [ ] 0 secretos Stripe (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`) en logs o respuestas API
- [ ] Tests cubren los 3 eventos webhook críticos con firma válida e inválida

---

## FASE 5 — DevOps & Despliegue

### Objetivo
Sistema completamente contenedorizado, desplegado en VPS con SSL, monitorización activa, CI/CD automatizado y procedimientos de backup y rollback documentados.

### SOPs a crear
| SOP | Ruta | Contenido |
|-----|------|-----------|
| DevOps & Deployment | `workflows/devops_deployment.md` | Build Docker, deploy VPS, rollback, gestión de secretos en producción |
| Monitoring & Alerts | `workflows/monitoring_alerts.md` | Métricas Prometheus, setup Grafana, reglas de alerta Telegram, runbook de incidencias |

### Tools a desarrollar / modificar

| ID | Acción | Archivo | Descripción |
|----|--------|---------|-------------|
| F5-T01 | Crear | `Dockerfile.pipeline` (NEW) | Python 3.12-slim + playwright install + chromium + ffmpeg; entrypoint: `python main.py` |
| F5-T02 | Crear | `Dockerfile.api` (NEW) | Python 3.12-slim + uvicorn; entrypoint: `uvicorn tools.api.app:app --host 0.0.0.0 --port 8000` |
| F5-T03 | Crear | `Dockerfile.frontend` (NEW) | Node 22 build stage → nginx:alpine serve stage; copia `dist/` a nginx html |
| F5-T04 | Crear | `docker-compose.yml` (NEW) | Servicios: pipeline, api, frontend, nginx; volumes: db, sessions, logs; networks: internal + public |
| F5-T05 | Crear | `nginx.conf` (NEW) | Reverse proxy `/api/*` → api:8000, `/*` → frontend:80; SSL termination; `limit_req_zone` por IP |
| F5-T06 | Crear | `.env.production.example` (NEW) | Template de todas las variables requeridas en producción, con comentarios explicativos |
| F5-T07 | Crear | `tools/backup_db.py` (NEW) | Backup diario SQLite → S3/R2 vía boto3 o rclone; retención 30 días; alerta Telegram si falla |
| F5-T08 | Crear | `tools/api/migrations/001_initial.sql` | SQL de schema inicial (listings + market_prices) como migración versionada |
| F5-T09 | Crear | `tools/api/migrations/run_migrations.py` (NEW) | Ejecutor de migraciones en orden, idempotente (tracks applied migrations en DB) |
| F5-T10 | Implementar | `tools/api/routers/health.py` | `/health` devuelve `{status, version, uptime_s}`; `/ready` hace ping a DB y verifica pipeline alive |
| F5-T11 | Implementar | `tools/api/middleware/metrics.py` (NEW) | Prometheus counters: `http_requests_total`, `scrapes_total`, `opportunities_found`, `alerts_sent` |
| F5-T12 | Crear | `tools/api/routers/metrics.py` (NEW) | `GET /metrics` — Prometheus text format (protegido por IP allowlist interna) |
| F5-T13 | Configurar | `structlog` | JSON logging en todos los módulos: `request_id`, `dealer_id`, `level`, `timestamp`, `message` |
| F5-T14 | Crear | `deploy/logrotate.conf` (NEW) | Logrotate: diario, 14 días retención, compress |
| F5-T15 | Crear | `deploy/agartha-pipeline.service` (NEW) | Systemd unit: `ExecStart=docker-compose up pipeline`, `Restart=on-failure`, `RestartSec=30s` |
| F5-T16 | Crear | `deploy/setup_vps.sh` (NEW) | Script idempotente Ubuntu 22.04: apt update, docker install, certbot, usuario deploy, firewall ufw |
| F5-T17 | Configurar | VPS | SSL/TLS Let's Encrypt: certbot nginx plugin, auto-renewal cron |
| F5-T18 | Crear | `.github/workflows/ci.yml` (NEW) | CI: ruff lint, mypy type check, pytest (unit + integration), build Docker images |
| F5-T19 | Crear | `.github/workflows/cd.yml` (NEW) | CD: on push main → SSH to VPS → `docker-compose pull && docker-compose up -d --no-deps` |
| F5-T20 | Diseñar | Grafana | Claude: JSON export del dashboard Grafana para métricas Agartha (scrapes, ROI, revenue) |
| F5-T21 | SOP | `workflows/devops_deployment.md` | Claude Code redacta SOP completo |
| F5-T22 | SOP | `workflows/monitoring_alerts.md` | Claude Code redacta SOP completo |

### Criterios de Aceptación — Fase 5 CERRADA cuando:
- [ ] `docker-compose up` levanta stack completo en VPS limpio (Ubuntu 22.04) en < 5 minutos
- [ ] SSL/TLS activo con certificado Let's Encrypt válido, HTTPS redirect funcionando
- [ ] Pipeline radar arranca automáticamente tras reinicio del VPS (systemd + Docker restart policy)
- [ ] Backup automático SQLite cada 24h confirmado en S3/R2 (verificar objeto en bucket)
- [ ] CI pipeline pasa en < 4 minutos: lint + type check + unit tests + build
- [ ] CD despliega en < 3 minutos tras merge a main sin downtime (rolling update)
- [ ] Métricas Prometheus exportadas, Grafana dashboard operativo con datos reales
- [ ] Alerta Telegram llega en < 60s cuando el pipeline falla o DB no responde
- [ ] `run_migrations.py` ejecuta migrations idempotentemente (doble ejecución = sin cambios)

---

## Dependencias Entre Fases

```
F1 ──────────────────────────────────► F2
     (aiosqlite, schema migrado)            │
                                            ▼
                                       F3 (API estable como contrato frontend)
                                            │
                                       F4 (Frontend existente para flujo registro)
                                            │
                                       F5 (Todo funcional antes de dockerizar)
```

- F2 puede iniciar cuando F1-T11 (aiosqlite) y F1-T12 (schema) estén completos
- F3 puede iniciar cuando F2 tenga al menos `/listings` y `/auth` funcionales (F2-T06, F2-T13, F2-T15)
- F4 puede iniciar en paralelo con F3 cuando F2 esté al 80% completo
- F5 inicia cuando F1+F2+F3+F4 superen sus criterios de aceptación

---

*Roadmap generado: 2026-05-07 | Versión: 1.0 | Próxima revisión: al cerrar Fase 1*
