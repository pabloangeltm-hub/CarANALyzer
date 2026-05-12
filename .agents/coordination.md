# Agent Coordination - Agartha SaaS

Shared work log for Claude Code (architecture, UX, SOPs, research) and Codex (Python implementation, tests, DevOps).
Read this file BEFORE touching files. Update it BEFORE and AFTER each task.

> RECOVERY NOTE 2026-05-08 Codex: file was restored after a zero-byte write caused by full disk (ENOSPC). Content reconstructed from the session readout plus `workflows/master_roadmap.md` and existing workflow docs. Previous completed-task state and locks below are preserved to the best available fidelity.

---

## Roles de Agente

| Agente | Responsabilidades |
|--------|-------------------|
| Claude Code | Arquitectura, diseno UX/UI, seleccion de dependencias via `/find-skills`, SOPs, revision API, Grafana |
| Codex | Implementacion Python, bugs, refactoring, tests, Docker, SQL migrations, CI/CD |

## Protocolo Estricto

1. Leer este archivo completo antes de editar.
2. Verificar tarea objetivo en Backlog o Active Tasks.
3. Mover tarea a Active Tasks, poner `In Progress`, anadir lock.
4. Si un archivo esta locked por otro agente, no editar: dejar Handoff.
5. Al terminar: status `Done`, liberar lock, registrar comandos/verificacion y changelog.
6. Si falla: status `Blocked` o `Failed`, liberar lock, anadir Handoff y Registro de Cambios.

## Active Tasks

| ID | Tarea | Propietario | Status | Lock de archivos | Notas |
|----|-------|-------------|--------|-----------------|-------|
| F8-T1 | index.css — dark token system + Inter typography scale | Claude Code | Done | `frontend/src/index.css`, `frontend/tailwind.config.cjs` | Completado 2026-05-10. Dark-first HSL tokens (surface/surface-elevated/primary/accent/warning), Inter font @import, shimmer, page-enter, scrollbar, text-display/heading/body/caption. `npm run build` OK. |
| F8-T2 | AppShell.tsx — sidebar colapsable + top bar | Claude Code | Done | `frontend/src/components/layout/AppLayout.tsx` | Completado 2026-05-10. Sidebar 64px↔240px CSS transition, localStorage persistence, mobile drawer + backdrop. Top bar: ⌘K search hint, bell, ThemeToggle, logout. `npm run build` OK. |
| F8-T3 | ListingCard.tsx — shimmer skeleton, ROI badge semáforo, hover glow | Claude Code | Done | `frontend/src/components/listings/ListingCard.tsx`, `frontend/src/components/ui/skeleton.tsx` | Completado 2026-05-10. Card con foto-strip, ROI badge semáforo (verde/ámbar/gris/lock), shimmer skeleton, hover glow, ListingCardGrid. `npm run build` OK. |
| F8-T5 | KPIBar.tsx — 4 stats con animación useCountUp | Claude Code | Done | `frontend/src/components/kpi/KPIBar.tsx` | Completado 2026-05-10. Hook useCountUp con ease-out cubic, 4 métricas (listings, oportunidades, ROI, alertas). `npm run build` OK. |
| F8-T7 | useToast.ts + ToastContainer — sistema de notificaciones | Claude Code | Done | `frontend/src/hooks/useToast.ts`, `frontend/src/components/ui/toast.tsx`, `frontend/src/App.tsx` | Completado 2026-05-10. Singleton event bus, 4 variantes (success/error/warning/info), auto-dismiss 4s, portal en document.body. `npm run build` OK. |
| F8-T8 | Dashboard.tsx — refactor con KPIBar + ListingCard grid | Claude Code | Done | `frontend/src/pages/Dashboard.tsx` | Completado 2026-05-10. Toggle tabla/grid, KPIBar, ListingCardGrid con 8 skeletons mientras carga, paginación. `npm run build` OK. |
| F8-T14 | Login.tsx — split layout: form + value prop | Claude Code | Done | `frontend/src/pages/Login.tsx` | Completado 2026-05-10. Split 55/45: features list + stat strip izquierda, form derecha. `npm run build` OK. |
| F8-T9 | Market.tsx — grid de cards + filtros sidebar | Claude Code | Done | `frontend/src/pages/Market.tsx` | Completado 2026-05-10. Grid/tabla toggle, filtros colapsables con animate-slide-down, paginación, EmptyState. `npm run build` OK. |
| F8-T10 | Pricing.tsx — tabla 4 planes + toggle mensual/anual | Claude Code | Done | `frontend/src/pages/Pricing.tsx`, `frontend/src/App.tsx` | Completado 2026-05-10. 4 planes (Free/Starter/Pro/Elite), toggle anual (−20%), feature comparison table, CTA. Ruta /pricing añadida. `npm run build` OK. |
| F6-T1 | Plan model ROI paywall | Codex | Done | `tools/api/models/plan.py`, `tools/api/schemas/dealers.py`, `tools/api/schemas/admin.py`, `tools/api/migrations/002_dealers.sql`, `tests/test_plan_model.py` | Completado 2026-05-10. Planes Free/Starter/Pro/Elite con roi_max_pct y feature limits; aliases legacy normalizados. |
| F6-T2 | Plan guard ROI redaction | Codex | Done | `tools/api/middleware/plan_guard.py`, `tools/api/routers/listings.py`, `tools/api/schemas/listings.py`, `tests/test_plan_guard_roi.py` | Completado 2026-05-10. `/listings` redacted por SQL segun roi_max_pct; payload no incluye datos premium para filas capadas. |
| F6-T4 | Payments plan names + Stripe price IDs | Codex | Done | `tools/api/routers/payments.py`, `tools/api/schemas/payments.py`, `tools/api/services/stripe_service.py`, `tests/test_payments_checkout.py`, `tests/test_stripe_service.py` | Completado 2026-05-10. Checkout usa Starter/Pro/Elite y env vars `STRIPE_PRICE_*` nuevas con fallback legacy. |
| F6-T5 | Stripe products setup 4 planes | Codex | Done | `tools/api/setup_stripe_products.py`, `.env.example` | Completado 2026-05-10. Script idempotente crea Starter 49, Pro 99, Elite 199. |
| F5-T13 | Grafana dashboard JSON | Claude Code | Done | `deploy/grafana/agartha_dashboard.json` | Completado 2026-05-10. 15 paneles: error rate, p95, req/s, in-flight, timeseries por status/path/latencia, tabla resumen. JSON válido. |
| F4-T24 | SOP auth_monetization.md | Claude Code | Done | `workflows/auth_monetization.md` | Completado 2026-05-10. Planes, JWT, API keys, flujo registro/login, plan guard, admin, runbook. |
| F4-T25 | SOP stripe_integration.md | Claude Code | Done | `workflows/stripe_integration.md` | Completado 2026-05-10. Setup productos, webhooks, Stripe CLI local, portal, paso a producción, runbook. |
| F5-T06 | .env.production.example | Claude Code | Done | `.env.production.example` | Completado 2026-05-10. Todas las vars de API, Stripe, Resend, Telegram, pipeline, proxies, LLM y CD. |
| F5-T21 | SOP devops_deployment.md | Claude Code | Done | `workflows/devops_deployment.md` | Completado 2026-05-10. Arquitectura Docker, VPS setup, SSL, CI/CD, rollback, comandos operacionales, checklist producción. |
| F5-T22 | SOP monitoring_alerts.md | Claude Code | Done | `workflows/monitoring_alerts.md` | Completado 2026-05-10. Prometheus config, Grafana dashboard, alertas Telegram, structlog, log rotation, healthchecks, runbook. |
| F4-T11 | Stripe Products — setup script + .env.example | Claude Code | Done | `tools/api/setup_stripe_products.py`, `.env.example` | Completado 2026-05-09. Script idempotente crea/reutiliza Products + Prices BASIC (€79/mo) y PREMIUM (€199/mo). `.env.example` ampliado con JWT_SECRET, STRIPE_*, RESEND_*. `py_compile` OK. |
| F4-T12 | Stripe service | Codex | Done | `tools/api/services/stripe_service.py`, `tests/test_stripe_service.py` | Completado 2026-05-09. `/find-skills`: `docs.stripe.com@stripe-projects` 16.8K, `stripe/ai@stripe-projects` 584, `stripe/com@stripe-projects` 22; sin instalar skill. Servicio crea/reutiliza Stripe customers, checkout sessions, billing portal sessions y verifica webhooks. |
| F4-T13 | Router /payments/checkout | Codex | Done | `tools/api/routers/payments.py`, `tools/api/app.py`, `tools/api/routers/__init__.py`, `tools/api/schemas/payments.py`, `tools/api/schemas/__init__.py`, `tests/test_payments_checkout.py` | Completado 2026-05-10. `/find-skills`: `stripe-payments` 922/458, `web-payments` 157, otros <40; sin instalar skill. Endpoint protegido crea checkout session via `StripeBillingService`; errores Stripe config -> 503 y servicio -> 400. |
| F4-T14 | Router /payments/portal | Codex | Done | `tools/api/routers/payments.py`, `tools/api/schemas/payments.py`, `tools/api/schemas/__init__.py`, `tests/test_payments_portal.py` | Completado 2026-05-10. `/find-skills`: `web-payments` 157, `stripe-integration` 30, `stripe` 25, otros <25; sin instalar skill. Endpoint protegido crea billing portal session via `StripeBillingService`; errores Stripe config -> 503 y servicio -> 400. |
| F4-T15 | Router /webhooks/stripe | Codex | Done | `tools/api/routers/webhooks.py`, `tools/api/app.py`, `tools/api/routers/__init__.py`, `tests/test_stripe_webhooks_router.py` | Completado 2026-05-10. `/find-skills`: `webhook-automation` 888, `stripe-webhooks` 227/72, `webhook-handler-patterns` 154; sin instalar skill. Endpoint publico valida firma Stripe con payload crudo y confirma recepcion de evento. |
| F4-T16 | Webhook checkout.session.completed | Codex | Done | `tools/api/routers/webhooks.py`, `tests/test_stripe_webhook_checkout_completed.py`, `tests/test_stripe_webhooks_router.py` | Completado 2026-05-10. `/find-skills`: `stripe-webhooks` 227/72, `payment-integration` 53, otros <31; sin instalar skill. Handler activa plan Basic/Premium y persiste `stripe_customer_id` desde checkout metadata. |
| F4-T17 | Webhook invoice.payment_failed | Codex | Done | `tools/api/routers/webhooks.py`, `tools/api/services/dealer_service.py`, `tests/test_dealer_service.py`, `tests/test_stripe_webhook_payment_failed.py` | Completado 2026-05-10. `/find-skills`: `stripe-payments` 922/458, `stripe-webhooks` 227/72, `invoice` 213, otros <55; sin instalar skill. Handler localiza dealer por `stripe_customer_id` y envia email de pago fallido. |
| F4-T18 | Webhook customer.subscription.deleted | Codex | Done | `tools/api/routers/webhooks.py`, `tests/test_stripe_webhook_subscription_deleted.py` | Completado 2026-05-10. `/find-skills`: `stripe-subscriptions` 191/71/42, `stripe-sync` 90, `stripe-webhooks` 72; sin instalar skill. Handler baja el dealer a plan `trial` cuando Stripe elimina la suscripcion. |
| F4-T20 | Router /auth/register | Codex | Done | `tools/api/routers/auth.py`, `tools/api/schemas/auth.py`, `tools/api/schemas/__init__.py`, `tests/test_auth_register.py` | Completado 2026-05-10. `/find-skills`: `stripe-integration` 326, `stripe-webhooks` 227/72, `developer-onboarding` 49, otros <26; sin instalar skill. `/auth/register` crea dealer, customer Stripe, email welcome y devuelve JWT + API key inicial. |
| F4-T21 | Admin controls | Codex | Done | `tools/api/routers/admin.py`, `tools/api/schemas/admin.py`, `tests/test_admin_controls.py` | Completado 2026-05-10. `/find-skills`: `stripe-payments` 458, `stripe-subscriptions` 191/71/42, `stripe-sync` 90; sin instalar skill. Controles admin para active, reset usage y ensure Stripe customer. |
| F4-T22 | Tests Stripe webhooks | Codex | Done | `tests/test_stripe_webhooks_integration.py` | Completado 2026-05-10. `/find-skills`: `webhook-automation` 888, `stripe-webhooks` 227/72, `pytest` 40; sin instalar skill. Test integrado cubre upgrade, email pago fallido y downgrade por cancelacion. |
| F5-T01 | Dockerfile.pipeline | Codex | Done | `Dockerfile.pipeline` | Completado 2026-05-10. `/find-skills`: `web-scraping` 2.2K, `playwright-scraper` 1.3K, otros <=157; sin instalar skill. Python 3.12-slim con requirements, Chromium Playwright y entrypoint `python main.py`. |
| F5-T02 | Dockerfile.api | Codex | Done | `Dockerfile.api` | Completado 2026-05-10. `/find-skills`: `fastapi-local-dev` 148, `fastapi-fullstack` 45, `uvicorn` 41; sin instalar skill. Python 3.12-slim + uvicorn `tools.api.app:app`, healthcheck `/health`. |
| F5-T03 | Dockerfile.frontend | Codex | Done | `Dockerfile.frontend` | Completado 2026-05-10. `/find-skills`: `docker-generator` 307, `vite-react` 43, `react-dockerfile` 23; sin instalar skill. Node 22 build stage + nginx alpine con fallback SPA y healthcheck. |
| F5-T04 | docker-compose.yml | Codex | Done | `docker-compose.yml` | Completado 2026-05-10. `/find-skills`: `fastapi-python` 8.4K, `docker-compose-orchestration` 1.3K, `docker-generator` 307; sin instalar skill. Servicios pipeline/api/frontend/nginx con redes, volumes y env_file `.env`. |
| F5-T05 | nginx.conf | Codex | Done | `nginx.conf` | Completado 2026-05-10. `/find-skills`: `docker-compose-orchestration` 1.3K, `fastapi-backend-template` 131, `reverse-proxy` 60; sin instalar skill. Reverse proxy `/api/*` -> api:8000 sin prefijo, frontend SPA y ACME challenge. |
| F5-T07 | backup_db.py | Codex | Done | `tools/backup_db.py`, `tests/test_backup_db.py` | Completado 2026-05-10. `/find-skills`: `database-backups` 41, `python-script` 17; sin instalar skill ni dependencia nueva. Backup SQLite consistente, retencion local y rclone opcional con alerta Telegram en fallo. |
| F5-T08 | run_migrations.py prod-safe | Codex | Done | `tools/run_migrations.py`, `tests/test_run_migrations.py` | Completado 2026-05-10. `/find-skills`: `alembic` 202, `python-package-migrator` 86, `django-migrations` 67; sin instalar skill ni dependencia nueva. Runner SQLite prod-safe con backup previo, `BEGIN IMMEDIATE`, ledger y checksums. |
| F5-T09 | Structlog JSON | Codex | Done | `requirements.txt`, `tools/api/logging.py`, `tools/api/app.py`, `tools/api/errors.py`, `tools/api/middleware/audit_logger.py`, `tests/test_structlog_logging.py` | Completado 2026-05-10. `/find-skills`: `fastapi-python` 8.4K, `logging-configurator` 306, `structlog` 46/24; Structlog JSON configurado para stdlib/API y audit events. |
| F5-T10 | Log rotation | Codex | Done | `tools/api/logging.py`, `tools/api/middleware/audit_logger.py`, `tests/test_log_rotation.py` | Completado 2026-05-10. `/find-skills`: `secrets-rotation` 286 no relevante, `python-logging-strategist` 87, `logs-python` 62; rotacion stdlib para logs JSON y audit JSONL. |
| F5-T11 | Prometheus metrics middleware | Codex | Done | `requirements.txt`, `tools/api/metrics.py`, `tools/api/middleware/prometheus_metrics.py`, `tools/api/middleware/__init__.py`, `tools/api/app.py`, `tests/test_prometheus_metrics_middleware.py` | Completado 2026-05-10. `/find-skills`: `fastapi-python` 8.4K, `grafana/prometheus` 209, `observability-monitoring` 111; middleware registra requests, latencia e in-flight con `prometheus-client`. |
| F5-T12 | Router /metrics | Codex | Done | `tools/api/routers/metrics.py`, `tools/api/routers/__init__.py`, `tools/api/app.py`, `tests/test_metrics_router.py` | Completado 2026-05-10. `/find-skills`: `prometheus-configuration` 6.1K, `prometheus-monitoring` 326, `grafana/prometheus` 209; endpoint publico expone registry F5-T11 con content type Prometheus. |
| F5-T14 | Systemd service unit | Codex | Done | `deploy/systemd/agartha.service`, `tests/test_systemd_service_unit.py` | Completado 2026-05-10. `/find-skills`: `docker-compose-production` 151, `compose-patterns-2025` 100, `systemd-services` 52; unidad systemd oneshot para stack Docker Compose. |
| F5-T15 | setup_vps.sh | Codex | Done | `setup_vps.sh`, `tests/test_setup_vps_script.py` | Completado 2026-05-10. `/find-skills`: `docker-compose-setup` 141, `vps-checkup` 79, `docker-vps-2026` 30; script bootstrap Ubuntu/Debian + Docker + systemd. |
| F5-T16 | SSL/TLS Let's Encrypt | Codex | Done | `docker-compose.yml`, `deploy/nginx/nginx.ssl.conf.template`, `tools/setup_letsencrypt.sh`, `deploy/systemd/agartha-certbot-renew.service`, `deploy/systemd/agartha-certbot-renew.timer`, `tests/test_letsencrypt_setup.py` | Completado 2026-05-10. `/find-skills`: `docker-deployment` 47, `ssl-tls-management` 41, `ssl-tls` 33; Certbot webroot con Docker, plantilla SSL nginx y renovacion systemd. |
| F5-T17 | GitHub Actions CI | Codex | Done | `.github/workflows/ci.yml`, `tests/test_ci_workflow.py` | Completado 2026-05-10. `/find-skills`: `github-actions` 371/9, `devops` 42; CI Python, frontend y compose con actions v6. |
| F5-T18 | GitHub Actions CD | Codex | Done | `.github/workflows/cd.yml`, `tests/test_cd_workflow.py` | Completado 2026-05-10. `/find-skills`: `ec2-backend-deployer` 96, `vps-checkup` 79, `devops` 42; deploy SSH sin acciones de terceros tras CI OK/manual. |
| F5-T19 | Nginx rate limiting | Codex | Done | `nginx.conf`, `deploy/nginx/nginx.ssl.conf.template`, `tests/test_nginx_rate_limiting.py` | Completado 2026-05-10. `/find-skills`: `nginx-config-optimizer` 219, `api-rate-limiting` 174, `rate-limiting-abuse-protection` 107; `limit_req` para API/auth con 429. |
| F4-T23 | Tests auth service | Codex | Done | `tests/test_auth_hardening.py` | Completado 2026-05-09. `/find-skills`: `express-production` 266 no relevante, `api-authentication` 220, `auth-expert` 31/10; sin instalar skill, se usa pytest/TestClient existente. |
| F4-T19 | Email service via Resend | Codex | Done | `requirements.txt`, `tools/api/services/email_service.py`, `tests/test_email_service.py` | Completado 2026-05-09. `/find-skills`: `fastapi-python` 8.3K, `fastapi-async-patterns` 774, `resend-webhooks` 92, `resend-email` 32/22; sin instalar skill. Docs oficiales Resend consultados: SDK `resend`, async extra `resend[async]`. |
| F4-T10 | Stripe SDK init | Codex | Done | `requirements.txt`, `tools/api/services/stripe_client.py`, `tests/test_stripe_client.py` | Completado 2026-05-09. `/find-skills`: resultados no Stripe (`fastapi-python` 8.3K, Sentry SDK 790/135, fastapi 99); sin instalar skill. Docs oficiales Stripe consultados: stripe-python latest `stripe>=14.4.0`. |
| F4-T09 | Plan guard middleware | Codex | Done | `tools/api/middleware/plan_guard.py`, `tools/api/middleware/__init__.py`, `tools/api/app.py`, `tests/test_plan_guard_middleware.py` | Completado 2026-05-09. `/find-skills`: `azure-quotas` 170.3K no relevante, `api-rate-limiting` 173, `rate-limiting-abuse-protection` 106, otros <25; sin instalar skill, se usa middleware FastAPI/Starlette existente. |
| F4-T08 | Plan enum + limits | Codex | Done | `tools/api/models/plan.py`, `tools/api/models/__init__.py`, `tools/api/schemas/dealers.py`, `tools/api/schemas/admin.py`, `tools/api/services/dealer_service.py`, `tests/test_plan_model.py` | Completado 2026-05-09. `/find-skills`: `fastapi-python` 8.3K, `python-fastapi-development` 324, `api-rate-limiting` 173, otros <50; sin instalar skill, se usa Enum/dataclass stdlib. |
| F4-T07 | API key service | Codex | Done | `tools/api/services/api_key_service.py`, `tools/api/routers/auth.py`, `tools/api/dependencies/auth.py`, `tests/test_api_key_service.py`, `tests/test_api_auth.py`, `tests/test_api_dependencies.py` | Completado 2026-05-09. `/find-skills`: `secrets-rotation` 280, `uuid-generator` 68/16, `rotate-key` 26; sin instalar skill, se usa stdlib uuid/secrets + SHA-256. |
| F4-T06 | Login/register auth integration | Codex | Done | `tools/api/routers/auth.py`, `tools/api/dependencies/auth.py`, `tools/api/dealer_store.py`, `tools/api/services/auth_service.py`, `tests/test_api_auth.py`, `tests/test_api_dependencies.py` | Completado 2026-05-09. `/find-skills`: `api-authentication` 220, `fastapi-expert` 147, `jwt-authentication` 130 (Node), otros <40; sin instalar skill, se integra servicio F4 con compatibilidad legacy. `/auth/register` publico queda para F4-T20. |
| F4-T05 | Dealers persistence/service layer | Codex | Done | `tools/api/services/dealer_service.py`, `tests/test_dealer_service.py` | Completado 2026-05-09. `/find-skills`: `fastapi-python` 8.3K, `python-fastapi-patterns` 45, `fastapi-coder` 41, otros <30; sin instalar skill, se usa service layer interno sobre SQLite/store existente. |
| F4-T04 | Auth service - bcrypt + JWT | Codex | Done | `tools/api/services/auth_service.py`, `tools/api/services/__init__.py`, `tests/test_auth_service.py`, `requirements.txt` | Completado 2026-05-09. `/find-skills`: `python-fastapi-development` 324, `api-authentication` 220, `jwt-authentication` 130 (Node), `fastapi-auth-patterns` 14; sin instalar skill, se usan paquetes Python `bcrypt` + `PyJWT`. |
| F4-T03 | Saved searches schema migration | Codex | Done | `tools/api/migrations/004_saved_searches.sql`, `tests/test_api_saved_searches_schema.py` | Completado 2026-05-09. `/find-skills`: `sqlite-data` 120, `migrating-json-schemas` 65, `sqlite-as-nosql-store` 37, `json-schema-lookup` 34, `sqlite-to-fast-sql` 25; sin instalar skill, se usa SQL/SQLite existente. |
| F4-T02 | API usage schema migration | Codex | Done | `tools/api/migrations/003_api_usage.sql`, `tests/test_api_usage_schema.py` | Completado 2026-05-09. `/find-skills`: resultados orientados a PostgreSQL (`postgresql-database-engineering` 830, `postgresql-best-practices` 115) y `sqlite-to-fast-sql` 25; sin instalar skill, se usa SQL/SQLite existente. |
| F4-T01 | Dealer schema migration | Codex | Done | `tools/api/migrations/002_dealers.sql`, `tools/api/dealer_store.py`, `tests/test_api_dealer_schema.py` | Completado 2026-05-09. `/find-skills`: `sqlite-data` 120, `schema-designer` 79, `sqlite-to-fast-sql` 25, `migrate-to-better-auth` 13; sin instalar skill, se usa SQL/SQLite existente. |
| F2-T23 | Integration tests router /auth | Codex | Done | `tests/test_api_auth.py` | Completado 2026-05-09. `/find-skills`: `pytest` 899/113/85/70, `fastapi-testing` 44; sin instalar skill, se usa pytest/TestClient existente. |
| F2-T22 | Integration tests router /market | Codex | Done | `tests/test_api_market.py` | Completado 2026-05-09. `/find-skills`: `pytest` 899/113/100, `fastapi-testing` 44; sin instalar skill, se usa pytest/TestClient existente. |
| F2-T21 | Integration tests router /listings | Codex | Done | `tests/test_api_listings.py` | Completado 2026-05-09. `/find-skills`: `fastapi-router-py` 108, `api-test-suite-builder` 104, otros <20; sin instalar skill, se usa pytest/TestClient existente. |
| F2-T20 | Health endpoints | Codex | Done | `tools/api/routers/health.py`, `tools/api/schemas/health.py`, `tools/api/app_meta.py`, `tools/api/app.py`, `tools/api/routers/__init__.py`, `tools/api/schemas/__init__.py`, `tests/test_api_health.py` | Completado 2026-05-09. `/find-skills`: `health-check-endpoints` 292/161, `backend-latency-profiler-helper` 103, otros <70; sin instalar skill, se usa FastAPI stdlib + get_db. |
| F2-T18 | Error handlers RFC 7807 | Codex | Done | `tools/api/errors.py`, `tools/api/app.py`, `tests/test_api_error_handlers.py` | Completado 2026-05-09. `/find-skills`: `api-error-handling` 323/173, `ln-772-error-handler-setup` 307, otros <80; sin instalar skill, se usan handlers FastAPI/Starlette stdlib. |
| F2-T17 | Dependency get_db() | Codex | Done | `tools/api/dependencies/db.py`, `tools/api/dependencies/__init__.py`, `tools/api/routers/listings.py`, `tools/api/routers/market.py`, `tools/api/routers/admin.py`, `tests/test_api_db_dependency.py` | Completado 2026-05-09. `/find-skills`: `fastapi` 181, `sqlite-data` 120, `sqlite-ops` 48, otros <40; sin instalar skill, se usa Depends + pool SQLite existente. |
| F2-T16 | Dependency get_current_dealer() | Codex | Done | `tools/api/dependencies/`, `tools/api/routers/auth.py`, `tools/api/routers/dealers.py`, `tools/api/routers/admin.py`, `tests/test_api_dependencies.py` | Completado 2026-05-09. `/find-skills`: `api-authentication` 220, `fastapi-dependency-injection` 34, `fastapi-auth-patterns` 14; sin instalar skill por baja adopcion, se usa FastAPI Depends + helpers existentes. |
| F2-T15 | Middleware audit logger | Codex | Done | `tools/api/middleware/audit_logger.py`, `tools/api/middleware/__init__.py`, `tools/api/app.py`, `tests/test_api_audit_logger.py` | Completado 2026-05-09. `/find-skills`: `kibana-audit` 469, `security-audit-logging` 351, `audit` 85, `security-fastapi` 58; sin instalar skill, se implementa middleware JSONL con stdlib. |
| F2-T12 | Full-text search `q` | Codex | Done | `tools/utils/db.py`, `tools/api/routers/listings.py` | Completado 2026-05-08. `/find-skills`: `sqlite database expert` 1.3K, `file-search` 161, `sqlite-expert` 110, `how-to-do-full-text-search-with-sqlite` 54; sin instalar skill, se usa SQLite FTS5 con fallback LIKE. |
| F2-T10 | Router /admin | Codex | Done | `tools/api/routers/admin.py`, `tools/api/schemas/admin.py`, `tools/api/app.py` | Completado 2026-05-08. `/find-skills`: `auth0-fastapi-api` 94, `add admin api endpoint` 84, `fastapi-patterns` 29; sin instalar skill/dependencia nueva por baja adopcion. |
| F2-T14 | Middleware rate limiter | Codex | Done | `tools/api/middleware/rate_limiter.py`, `tools/api/app.py` | Completado 2026-05-08. `/find-skills`: `api-rate-limiting` 173, `rate-limiting-abuse-protection` 105, `api-hardening` 87; se usa limiter en memoria sin dependencia nueva. |
| F2-T19 | CORS config | Codex | Done | `tools/api/app.py` | Completado 2026-05-08. `CORSMiddleware` configurable via `AGARTHA_CORS_ORIGINS`. |
| F2-T11 | Motor filtros dinamicos | Codex | Done | `tools/api/routers/listings.py`, `tools/api/schemas/listings.py` | Completado 2026-05-08. `/find-skills`: `api-pagination` 311, `api-filtering-sorting` 286/169; sin instalar skill. |
| F2-T13 | Paginacion completa | Codex | Done | `tools/api/routers/listings.py`, `tools/api/schemas/listings.py` | Completado 2026-05-08; respuesta B2B `{items,total,page,size}`. |
| F2-T09 | Router /auth | Codex | Done | `tools/api/routers/auth.py`, `tools/api/dealer_store.py`, `tools/api/security.py`, `tools/api/app.py` | Completado 2026-05-08. |
| F2-T08 | Router /dealers | Codex | Done | `tools/api/routers/dealers.py`, `tools/api/schemas/dealers.py`, `tools/api/dealer_store.py`, `tools/api/security.py`, `tools/api/app.py` | Completado 2026-05-08. |
| F2-T07 | Router /market | Codex | Done | `tools/api/routers/market.py`, `tools/api/app.py` | Completado 2026-05-08. |
| F2-T06 | Router /listings | Codex | Done | `tools/api/routers/listings.py`, `tools/api/app.py` | Completado 2026-05-08. |
| F2-T05 | Pydantic schemas auth | Codex | Done | `tools/api/schemas/auth.py` | Completado 2026-05-08. |
| F2-T04 | Pydantic schemas market | Codex | Done | `tools/api/schemas/market.py` | Completado 2026-05-08. |
| F2-T03 | Pydantic schema ListingFilter | Codex | Done | `tools/api/schemas/listings.py` | Completado 2026-05-08. |
| F2-T02 | Pydantic schema ListingOut | Codex | Done | `tools/api/schemas/listings.py` | Completado 2026-05-08. |
| F2-T01 | FastAPI restructure - crear paquete `tools/api/` | Codex | Done | `tools/api/` | Completado 2026-05-08. `/find-skills`: `fastapi-python` 8.3K installs, `python-fastapi-development` 323, `python-fastapi-patterns` 45; sin instalar skill. |
| F1-T18 | Tests unitarios parsers | Codex | Done | `tests/test_scraper.py`, `tools/scrape_cars.py` | Completado 2026-05-08. `/find-skills`: `pytest` 899, `pytest` 100, `comprehensive-unit-testing-with-pytest` 63; se usa pytest existente. |
| F1-T17 | Tests unitarios ForensicAgent | Codex | Done | `tests/test_forensic_agent.py` | Completado 2026-05-08. `/find-skills`: `pytest` 899, `pytest-patterns` 298, `pytest-async-testing` 12; se usa pytest con `asyncio.run` sin dependencia nueva. |
| F1-T16 | Tests unitarios ValuationEngine >= 90% coverage | Codex | Done | `tests/test_valuation_engine.py`, `requirements.txt` | Completado 2026-05-08. `/find-skills`: `pytest-coverage` 10K installs, `pytest` 899, `pytest-testing` 110; se usa pytest/pytest-cov sin instalar skill. |
| F1-T15 | Proxy rotation fallback - ScrapingBee/BrightData | Codex | Done | `tools/utils/request_handler.py` | Completado 2026-05-08. `/find-skills`: `scrapingbee` 26 installs, `scrapfly-scraper` 13, `brightdata` 11; sin skill madura para instalar. Docs oficiales consultados: ScrapingBee HTML API y Bright Data Unlocker API. |
| F1-T14 | Price time-series en `price_history_json` | Codex | Done | `tools/utils/db.py` | Completado 2026-05-08. `/find-skills`: `time series analysis` 331 installs pero prompt-only/no SQLite, `time-series-decomposer` 59, `price-history` 36; sin skill relevante para instalar. |
| F1-T13 | Cross-portal deduplication Milanuncios + Wallapop | Codex | Done | `tools/utils/db.py` | Completado 2026-05-08. `/find-skills`: `deduplication` 41 installs, `fuzzy-matching` 38, `hierarchical-matching-systems` 25; sin skill madura/relevante para instalar. |
| F1-T12 | Schema migration - condition_score, images_count, seller_type, location, price_history_json | Codex | Done | `tools/utils/db.py` | Completado 2026-05-08. `/find-skills`: `sqlite-ops` 48 installs, `sqlite-to-fast-sql` 24; sin skill madura/relevante para instalar. |
| F1-T10 | vLLM benchmark - `tools/test_vllm.py` throughput, p50/p95, VRAM RTX 3060 | Codex | Done | `tools/test_vllm.py` | Completado 2026-05-08. `/find-skills`: `serving-llms-vllm` 403 installs, `tensorrt-llm` 314, oficiales `vllm-bench-*` 26-27; sin skill suficientemente madura para instalar. |
| F1-T09 | RepairCostEngine real - tabla brand/damage_type -> cost_range_eur | Codex | Done | `tools/utils/forensic_agent.py` | Completado 2026-05-08. `/find-skills`: `vehicle-routing-problem` 18 installs, `fleet-management` 16, `israeli-vehicle-manager` 12; sin skill madura/relevante para costes de reparacion. |
| F1-T08 | Mejorar prompt ForensicAgent - confidence_score (0.0-1.0), keywords ampliados, output schema v2 | Codex | Done | `tools/utils/forensic_agent.py` | Completado 2026-05-08. Schema v2 con `confidence_score`, `damage_keywords`, `damage_types`; prompt ampliado y normalizacion robusta. `/find-skills`: `schema-markup` 86 installs, `instructor` 38, `llm-structured-output` 32/14; sin skill madura. |
| F1-T05 | Concurrent scraping - `asyncio.gather(milanuncios_task, wallapop_task)` en main.py pipeline | Codex | Done | `main.py` | Completado 2026-05-08. |
| F1-T07 | Pre-filtro heuristico configurable - year_min/max, price_band, seller_type desde .env | Codex | Done | `main.py`, `tools/scrape_cars.py`, `workflows/data_pipeline.md` | Completado 2026-05-08. |
| F1-T03 | Integrar Scrapling en MilanunciosScraper si PoC muestra mejora >= 20% en block rate | Codex | Done | `tools/scrape_cars.py` | Completado 2026-05-08. |
| F1-T04 | Wallapop fix - corregir auth headers (`x-signature` + `x-timestamp`) | Codex | Done | `tools/scrape_cars.py` | Completado 2026-05-08. |
| F1-T01 | Scrapling PoC - benchmark Milanuncios vs Playwright | Codex | Done | `tools/benchmark_scrapers.py`, `requirements.txt` | Completado 2026-05-07. |
| F1-T02 | Scrapling Datadome benchmark - extraer listings desde JSON interno | Codex | Done | `tools/benchmark_scrapers.py` | Completado 2026-05-08. |
| F1-T06 | Session pool auto-replenishment via 2captcha | Codex | Done | `tools/replenish_sessions.py` | Completado 2026-05-08. |
| F1-T11 | SQLite WAL hardening - aiosqlite async pool + retry SQLITE_BUSY | Codex | Done | `tools/utils/db.py` | Completado 2026-05-07. |
| F1-T21 | SOP data_pipeline.md | Claude Code | Done | `workflows/data_pipeline.md` | Completado 2026-05-07. |
| F3-T01 | Research stack frontend | Claude Code | Done | - | Completado 2026-05-08. |
| F3-T02 | UX wireframes ASCII dashboard | Claude Code | Done | - | Completado 2026-05-08. |
| F3-T03 | Decision stack frontend | Claude Code | Done | - | Completado 2026-05-08. |
| F3-T04 | Frontend scaffold | Codex | Done | `frontend/` | Completado 2026-05-08. Vite React TS, Tailwind 3, shadcn/ui base, routing y dashboard shell. |
| F3-T05 | API client layer | Codex | Done | `frontend/src/api/`, `frontend/src/hooks/`, `frontend/src/types/api.ts`, `frontend/src/store/filters.ts` | Completado 2026-05-08. Axios + JWT refresh, TanStack Query hooks para `/listings`, `/market`, `/auth`. |
| F3-T06 | Auth flow | Codex | Done | `frontend/src/App.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/store/auth.ts`, `frontend/src/hooks/useAuth.ts`, `frontend/src/api/client.ts`, `frontend/src/pages/Dashboard.tsx` | Completado 2026-05-08. `/login`, guard de rutas, persistencia de tokens, logout y redireccion. |
| F3-T07 | ListingsTable component | Codex | Done | `frontend/src/components/listings/ListingsTable.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/lib/utils.ts` | Completado 2026-05-08. TanStack Table + Virtual, ordenacion local y paginacion API. |
| F3-T08 | FilterPanel component | Codex | Done | `frontend/src/components/filters/FilterPanel.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/store/filters.ts` | Completado 2026-05-08. Filtros `q`, marca, modelo, portal, vendedor, forense, year, price y ROI. |
| F3-T09 | ROI BarChart component | Codex | Done | `frontend/src/components/market/ROIBarChart.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/vite.config.ts` | Completado 2026-05-08. Recharts sobre `/market/by-brand`; chunk separado para charts. |
| F3-T10 | PriceTrend chart | Codex | Done | `frontend/src/components/market/PriceTrendChart.tsx`, `frontend/src/pages/Market.tsx`, `frontend/src/pages/Dashboard.tsx` | Completado 2026-05-08. |
| F3-T11 | ListingDrawer component | Codex | Done | `frontend/src/components/listings/ListingDrawer.tsx`, `frontend/src/components/listings/ListingsTable.tsx`, `frontend/src/pages/Dashboard.tsx` | Completado 2026-05-08. |
| F3-T12 | KPI Widgets | Codex | Done | `frontend/src/components/kpi/KPIWidgets.tsx`, `frontend/src/pages/Dashboard.tsx` | Completado 2026-05-08. |
| F3-T13 | Dashboard page | Codex | Done | `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/layout/AppLayout.tsx` | Completado 2026-05-08. |
| F3-T14 | MarketAnalysis page | Codex | Done | `frontend/src/pages/Market.tsx`, `frontend/src/App.tsx` | Completado 2026-05-08. |
| F3-T15 | AlertCenter page | Codex | Done | `frontend/src/pages/Alerts.tsx` | Completado 2026-05-08. Alertas derivadas de `/listings?min_roi=20`. |
| F3-T16 | SavedSearches component | Codex | Done | `frontend/src/pages/SavedSearches.tsx` | Completado 2026-05-08. Persistencia local hasta endpoint `/searches`. |
| F3-T17 | ExportButton component | Codex | Done | `frontend/src/components/listings/ExportButton.tsx`, `frontend/src/components/listings/ListingsTable.tsx` | Completado 2026-05-08. |
| F3-T18 | Responsive layout | Codex | Done | `frontend/src/components/layout/AppLayout.tsx`, `frontend/src/pages/` | Completado 2026-05-08. Sidebar desktop + menu movil. |
| F3-T19 | Dark mode | Codex | Done | `frontend/src/store/theme.ts`, `frontend/src/components/layout/ThemeToggle.tsx` | Completado 2026-05-08. |
| F3-T20 | Loading states | Codex | Done | `frontend/src/components/ui/loading.tsx`, `frontend/src/components/*`, `frontend/src/pages/*` | Completado 2026-05-08. |
| F3-T21 | Error boundaries | Codex | Done | `frontend/src/components/ErrorBoundary.tsx`, `frontend/src/App.tsx` | Completado 2026-05-08. |
| F3-T22 | Playwright E2E dealer flow | Codex | Done | `frontend/e2e/dealer-flow.spec.ts`, `frontend/playwright.config.ts`, `frontend/package.json` | Completado 2026-05-08. |
| F5-T20 | Secrets management doc | Claude Code | Done | `workflows/secrets_management.md` | Completado 2026-05-08. |
| F1-T20 | SOP ai_analysis_setup.md | Claude Code | Done | `workflows/ai_analysis_setup.md` | Completado 2026-05-08. ForensicAgent (Ollama deepseek-r1:8b), RepairCostEngine, schema v2, benchmark vLLM vs Ollama, troubleshooting. |
| F2-T24 | Diseno contrato API + OpenAPI customization | Claude Code | Done | `tools/api/app.py`, `tools/api/routers/`, `workflows/api_contract.md` | Completado 2026-05-08. OpenAPI metadata + security schemes + summaries en los 4 routers + contrato completo en workflows. |

## File Locks

| Path | Owner | Razon | Desde | Condicion de liberacion |
|------|-------|-------|-------|------------------------|
| `frontend/src/index.css` | | liberado | 2026-05-10 | COMPLETADO F8-T1 |
| `frontend/tailwind.config.cjs` | | liberado | 2026-05-10 | COMPLETADO F8-T1 |
| `frontend/src/components/layout/AppLayout.tsx` | | liberado | 2026-05-10 | COMPLETADO F8-T2 |
| `frontend/src/components/listings/ListingCard.tsx` | Claude Code | F8-T3 card redesign | 2026-05-10 | COMPLETAR F8-T3 |
| `frontend/src/components/ui/skeleton.tsx` | Claude Code | F8-T3 skeleton component | 2026-05-10 | COMPLETAR F8-T3 |
| `tools/api/models/plan.py` | | liberado | 2026-05-10 | COMPLETADO F6-T1 |
| `tools/api/schemas/dealers.py` | | liberado | 2026-05-10 | COMPLETADO F6-T1 |
| `tools/api/schemas/admin.py` | | liberado | 2026-05-10 | COMPLETADO F6-T1 |
| `tools/api/migrations/002_dealers.sql` | | liberado | 2026-05-10 | COMPLETADO F6-T1 |
| `tests/test_plan_model.py` | | liberado | 2026-05-10 | COMPLETADO F6-T1 |
| `tools/api/middleware/plan_guard.py` | | liberado | 2026-05-10 | COMPLETADO F6-T2 |
| `tools/api/routers/listings.py` | | liberado | 2026-05-10 | COMPLETADO F6-T2 |
| `tools/api/schemas/listings.py` | | liberado | 2026-05-10 | COMPLETADO F6-T2 |
| `tests/test_plan_guard_roi.py` | | liberado | 2026-05-10 | COMPLETADO F6-T2/F6-T7 |
| `tools/api/routers/payments.py` | | liberado | 2026-05-10 | COMPLETADO F6-T4 |
| `tools/api/schemas/payments.py` | | liberado | 2026-05-10 | COMPLETADO F6-T4 |
| `tools/api/services/stripe_service.py` | | liberado | 2026-05-10 | COMPLETADO F6-T4 |
| `tests/test_payments_checkout.py` | | liberado | 2026-05-10 | COMPLETADO F6-T4 |
| `tests/test_stripe_service.py` | | liberado | 2026-05-10 | COMPLETADO F6-T4 |
| `tools/api/setup_stripe_products.py` | | liberado | 2026-05-10 | COMPLETADO F6-T5 |
| `.env.example` | | liberado | 2026-05-10 | COMPLETADO F6-T5 |
| `requirements.txt` | | liberado | 2026-05-10 | COMPLETADO F5-T09 |
| `tools/api/logging.py` | | liberado | 2026-05-10 | COMPLETADO F5-T09 |
| `tools/api/app.py` | | liberado | 2026-05-10 | COMPLETADO F5-T09 |
| `tools/api/errors.py` | | liberado | 2026-05-10 | COMPLETADO F5-T09 |
| `tools/api/middleware/audit_logger.py` | | liberado | 2026-05-10 | COMPLETADO F5-T09 |
| `tests/test_structlog_logging.py` | | liberado | 2026-05-10 | COMPLETADO F5-T09 |
| `tools/api/logging.py` | | liberado | 2026-05-10 | COMPLETADO F5-T10 |
| `tools/api/middleware/audit_logger.py` | | liberado | 2026-05-10 | COMPLETADO F5-T10 |
| `tests/test_log_rotation.py` | | liberado | 2026-05-10 | COMPLETADO F5-T10 |
| `requirements.txt` | | liberado | 2026-05-10 | COMPLETADO F5-T11 |
| `tools/api/metrics.py` | | liberado | 2026-05-10 | COMPLETADO F5-T11 |
| `tools/api/middleware/prometheus_metrics.py` | | liberado | 2026-05-10 | COMPLETADO F5-T11 |
| `tools/api/middleware/__init__.py` | | liberado | 2026-05-10 | COMPLETADO F5-T11 |
| `tools/api/app.py` | | liberado | 2026-05-10 | COMPLETADO F5-T11 |
| `tests/test_prometheus_metrics_middleware.py` | | liberado | 2026-05-10 | COMPLETADO F5-T11 |
| `tools/api/routers/metrics.py` | | liberado | 2026-05-10 | COMPLETADO F5-T12 |
| `tools/api/routers/__init__.py` | | liberado | 2026-05-10 | COMPLETADO F5-T12 |
| `tools/api/app.py` | | liberado | 2026-05-10 | COMPLETADO F5-T12 |
| `tests/test_metrics_router.py` | | liberado | 2026-05-10 | COMPLETADO F5-T12 |
| `deploy/systemd/agartha.service` | | liberado | 2026-05-10 | COMPLETADO F5-T14 |
| `tests/test_systemd_service_unit.py` | | liberado | 2026-05-10 | COMPLETADO F5-T14 |
| `setup_vps.sh` | | liberado | 2026-05-10 | COMPLETADO F5-T15 |
| `tests/test_setup_vps_script.py` | | liberado | 2026-05-10 | COMPLETADO F5-T15 |
| `docker-compose.yml` | | liberado | 2026-05-10 | COMPLETADO F5-T16 |
| `deploy/nginx/nginx.ssl.conf.template` | | liberado | 2026-05-10 | COMPLETADO F5-T16 |
| `tools/setup_letsencrypt.sh` | | liberado | 2026-05-10 | COMPLETADO F5-T16 |
| `deploy/systemd/agartha-certbot-renew.service` | | liberado | 2026-05-10 | COMPLETADO F5-T16 |
| `deploy/systemd/agartha-certbot-renew.timer` | | liberado | 2026-05-10 | COMPLETADO F5-T16 |
| `tests/test_letsencrypt_setup.py` | | liberado | 2026-05-10 | COMPLETADO F5-T16 |
| `.github/workflows/ci.yml` | | liberado | 2026-05-10 | COMPLETADO F5-T17 |
| `tests/test_ci_workflow.py` | | liberado | 2026-05-10 | COMPLETADO F5-T17 |
| `.github/workflows/cd.yml` | | liberado | 2026-05-10 | COMPLETADO F5-T18 |
| `tests/test_cd_workflow.py` | | liberado | 2026-05-10 | COMPLETADO F5-T18 |
| `nginx.conf` | | liberado | 2026-05-10 | COMPLETADO F5-T19 |
| `deploy/nginx/nginx.ssl.conf.template` | | liberado | 2026-05-10 | COMPLETADO F5-T19 |
| `tests/test_nginx_rate_limiting.py` | | liberado | 2026-05-10 | COMPLETADO F5-T19 |
| `tools/run_migrations.py` | | liberado | 2026-05-10 | COMPLETADO F5-T08 |
| `tests/test_run_migrations.py` | | liberado | 2026-05-10 | COMPLETADO F5-T08 |
| `tools/backup_db.py` | | liberado | 2026-05-10 | COMPLETADO F5-T07 |
| `tests/test_backup_db.py` | | liberado | 2026-05-10 | COMPLETADO F5-T07 |
| `nginx.conf` | | liberado | 2026-05-10 | COMPLETADO F5-T05 |
| `docker-compose.yml` | | liberado | 2026-05-10 | COMPLETADO F5-T04 |
| `Dockerfile.frontend` | | liberado | 2026-05-10 | COMPLETADO F5-T03 |
| `Dockerfile.api` | | liberado | 2026-05-10 | COMPLETADO F5-T02 |
| `Dockerfile.pipeline` | | liberado | 2026-05-10 | COMPLETADO F5-T01 |
| `tests/test_stripe_webhooks_integration.py` | | liberado | 2026-05-10 | COMPLETADO F4-T22 |
| `tools/api/routers/admin.py` | | liberado | 2026-05-10 | COMPLETADO F4-T21 |
| `tools/api/schemas/admin.py` | | liberado | 2026-05-10 | COMPLETADO F4-T21 |
| `tests/test_admin_controls.py` | | liberado | 2026-05-10 | COMPLETADO F4-T21 |
| `tools/api/routers/auth.py` | | liberado | 2026-05-10 | COMPLETADO F4-T20 |
| `tools/api/schemas/auth.py` | | liberado | 2026-05-10 | COMPLETADO F4-T20 |
| `tools/api/schemas/__init__.py` | | liberado | 2026-05-10 | COMPLETADO F4-T20 |
| `tests/test_auth_register.py` | | liberado | 2026-05-10 | COMPLETADO F4-T20 |
| `tools/api/routers/webhooks.py` | | liberado | 2026-05-10 | COMPLETADO F4-T18 |
| `tests/test_stripe_webhook_subscription_deleted.py` | | liberado | 2026-05-10 | COMPLETADO F4-T18 |
| `tools/api/routers/webhooks.py` | | liberado | 2026-05-10 | COMPLETADO F4-T17 |
| `tools/api/services/dealer_service.py` | | liberado | 2026-05-10 | COMPLETADO F4-T17 |
| `tests/test_dealer_service.py` | | liberado | 2026-05-10 | COMPLETADO F4-T17 |
| `tests/test_stripe_webhook_payment_failed.py` | | liberado | 2026-05-10 | COMPLETADO F4-T17 |
| `tools/api/routers/webhooks.py` | | liberado | 2026-05-10 | COMPLETADO F4-T16 |
| `tests/test_stripe_webhook_checkout_completed.py` | | liberado | 2026-05-10 | COMPLETADO F4-T16 |
| `tests/test_stripe_webhooks_router.py` | | liberado | 2026-05-10 | COMPLETADO F4-T16 |
| `tools/api/routers/webhooks.py` | | liberado | 2026-05-10 | COMPLETADO F4-T15 |
| `tools/api/app.py` | | liberado | 2026-05-10 | COMPLETADO F4-T15 |
| `tools/api/routers/__init__.py` | | liberado | 2026-05-10 | COMPLETADO F4-T15 |
| `tests/test_stripe_webhooks_router.py` | | liberado | 2026-05-10 | COMPLETADO F4-T15 |
| `tools/api/routers/payments.py` | | liberado | 2026-05-10 | COMPLETADO F4-T14 |
| `tools/api/schemas/payments.py` | | liberado | 2026-05-10 | COMPLETADO F4-T14 |
| `tools/api/schemas/__init__.py` | | liberado | 2026-05-10 | COMPLETADO F4-T14 |
| `tests/test_payments_portal.py` | | liberado | 2026-05-10 | COMPLETADO F4-T14 |
| `tools/api/routers/payments.py` | | liberado | 2026-05-10 | COMPLETADO F4-T13 |
| `tools/api/app.py` | | liberado | 2026-05-10 | COMPLETADO F4-T13 |
| `tools/api/routers/__init__.py` | | liberado | 2026-05-10 | COMPLETADO F4-T13 |
| `tools/api/schemas/payments.py` | | liberado | 2026-05-10 | COMPLETADO F4-T13 |
| `tools/api/schemas/__init__.py` | | liberado | 2026-05-10 | COMPLETADO F4-T13 |
| `tests/test_payments_checkout.py` | | liberado | 2026-05-10 | COMPLETADO F4-T13 |
| `tools/api/services/stripe_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T12 |
| `tools/api/services/__init__.py` | | liberado | 2026-05-09 | COMPLETADO F4-T12 |
| `tests/test_stripe_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T12 |
| `tests/test_auth_hardening.py` | | liberado | 2026-05-09 | COMPLETADO F4-T23 |
| `requirements.txt` | | liberado | 2026-05-09 | COMPLETADO F4-T19 |
| `tools/api/services/email_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T19 |
| `tests/test_email_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T19 |
| `requirements.txt` | | liberado | 2026-05-09 | COMPLETADO F4-T10 |
| `tools/api/services/stripe_client.py` | | liberado | 2026-05-09 | COMPLETADO F4-T10 |
| `tests/test_stripe_client.py` | | liberado | 2026-05-09 | COMPLETADO F4-T10 |
| `tools/api/middleware/plan_guard.py` | | liberado | 2026-05-09 | COMPLETADO F4-T09 |
| `tools/api/middleware/__init__.py` | | liberado | 2026-05-09 | COMPLETADO F4-T09 |
| `tools/api/app.py` | | liberado | 2026-05-09 | COMPLETADO F4-T09 |
| `tests/test_plan_guard_middleware.py` | | liberado | 2026-05-09 | COMPLETADO F4-T09 |
| `tools/api/models/plan.py` | | liberado | 2026-05-09 | COMPLETADO F4-T08 |
| `tools/api/models/__init__.py` | | liberado | 2026-05-09 | COMPLETADO F4-T08 |
| `tools/api/schemas/dealers.py` | | liberado | 2026-05-09 | COMPLETADO F4-T08 |
| `tools/api/schemas/admin.py` | | liberado | 2026-05-09 | COMPLETADO F4-T08 |
| `tools/api/services/dealer_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T08 |
| `tests/test_plan_model.py` | | liberado | 2026-05-09 | COMPLETADO F4-T08 |
| `tools/api/services/api_key_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T07 |
| `tools/api/routers/auth.py` | | liberado | 2026-05-09 | COMPLETADO F4-T07 |
| `tools/api/dependencies/auth.py` | | liberado | 2026-05-09 | COMPLETADO F4-T07 |
| `tests/test_api_key_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T07 |
| `tests/test_api_auth.py` | | liberado | 2026-05-09 | COMPLETADO F4-T07 |
| `tests/test_api_dependencies.py` | | liberado | 2026-05-09 | COMPLETADO F4-T07 |
| `tools/api/routers/auth.py` | | liberado | 2026-05-09 | COMPLETADO F4-T06 |
| `tools/api/dependencies/auth.py` | | liberado | 2026-05-09 | COMPLETADO F4-T06 |
| `tools/api/dealer_store.py` | | liberado | 2026-05-09 | COMPLETADO F4-T06 |
| `tools/api/services/auth_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T06 |
| `tests/test_api_auth.py` | | liberado | 2026-05-09 | COMPLETADO F4-T06 |
| `tests/test_api_dependencies.py` | | liberado | 2026-05-09 | COMPLETADO F4-T06 |
| `tools/api/services/dealer_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T05 |
| `tests/test_dealer_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T05 |
| `tools/api/services/auth_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T04 |
| `tools/api/services/__init__.py` | | liberado | 2026-05-09 | COMPLETADO F4-T04 |
| `tests/test_auth_service.py` | | liberado | 2026-05-09 | COMPLETADO F4-T04 |
| `requirements.txt` | | liberado | 2026-05-09 | COMPLETADO F4-T04 |
| `tools/api/migrations/004_saved_searches.sql` | | liberado | 2026-05-09 | COMPLETADO F4-T03 |
| `tests/test_api_saved_searches_schema.py` | | liberado | 2026-05-09 | COMPLETADO F4-T03 |
| `tools/api/migrations/003_api_usage.sql` | | liberado | 2026-05-09 | COMPLETADO F4-T02 |
| `tests/test_api_usage_schema.py` | | liberado | 2026-05-09 | COMPLETADO F4-T02 |
| `tools/api/migrations/002_dealers.sql` | | liberado | 2026-05-09 | COMPLETADO F4-T01 |
| `tools/api/dealer_store.py` | | liberado | 2026-05-09 | COMPLETADO F4-T01 |
| `tests/test_api_dealer_schema.py` | | liberado | 2026-05-09 | COMPLETADO F4-T01 |
| `tests/test_api_auth.py` | | liberado | 2026-05-09 | COMPLETADO F2-T23 |
| `tests/test_api_market.py` | | liberado | 2026-05-09 | COMPLETADO F2-T22 |
| `tests/test_api_listings.py` | | liberado | 2026-05-09 | COMPLETADO F2-T21 |
| `tools/api/routers/health.py` | | liberado | 2026-05-09 | COMPLETADO F2-T20 |
| `tools/api/schemas/health.py` | | liberado | 2026-05-09 | COMPLETADO F2-T20 |
| `tools/api/app_meta.py` | | liberado | 2026-05-09 | COMPLETADO F2-T20 |
| `tools/api/app.py` | | liberado | 2026-05-09 | COMPLETADO F2-T20 |
| `tools/api/routers/__init__.py` | | liberado | 2026-05-09 | COMPLETADO F2-T20 |
| `tools/api/schemas/__init__.py` | | liberado | 2026-05-09 | COMPLETADO F2-T20 |
| `tests/test_api_health.py` | | liberado | 2026-05-09 | COMPLETADO F2-T20 |
| `tools/api/errors.py` | | liberado | 2026-05-09 | COMPLETADO F2-T18 |
| `tools/api/app.py` | | liberado | 2026-05-09 | COMPLETADO F2-T18 |
| `tests/test_api_error_handlers.py` | | liberado | 2026-05-09 | COMPLETADO F2-T18 |
| `tools/api/dependencies/db.py` | | liberado | 2026-05-09 | COMPLETADO F2-T17 |
| `tools/api/dependencies/__init__.py` | | liberado | 2026-05-09 | COMPLETADO F2-T17 |
| `tools/api/routers/listings.py` | | liberado | 2026-05-09 | COMPLETADO F2-T17 |
| `tools/api/routers/market.py` | | liberado | 2026-05-09 | COMPLETADO F2-T17 |
| `tools/api/routers/admin.py` | | liberado | 2026-05-09 | COMPLETADO F2-T17 |
| `tests/test_api_db_dependency.py` | | liberado | 2026-05-09 | COMPLETADO F2-T17 |
| `tools/api/dependencies/` | | liberado | 2026-05-09 | COMPLETADO F2-T16 |
| `tools/api/routers/auth.py` | | liberado | 2026-05-09 | COMPLETADO F2-T16 |
| `tools/api/routers/dealers.py` | | liberado | 2026-05-09 | COMPLETADO F2-T16 |
| `tools/api/routers/admin.py` | | liberado | 2026-05-09 | COMPLETADO F2-T16 |
| `tests/test_api_dependencies.py` | | liberado | 2026-05-09 | COMPLETADO F2-T16 |
| `tools/api/middleware/audit_logger.py` | | liberado | 2026-05-09 | COMPLETADO F2-T15 |
| `tools/api/middleware/__init__.py` | | liberado | 2026-05-09 | COMPLETADO F2-T15 |
| `tools/api/app.py` | | liberado | 2026-05-09 | COMPLETADO F2-T15 |
| `tests/test_api_audit_logger.py` | | liberado | 2026-05-09 | COMPLETADO F2-T15 |
| `tools/utils/db.py` | | liberado | 2026-05-08 | COMPLETADO F2-T12 |
| `tools/api/routers/listings.py` | | liberado | 2026-05-08 | COMPLETADO F2-T12 |
| `tools/api/routers/admin.py` | | liberado | 2026-05-08 | COMPLETADO F2-T10 |
| `tools/api/schemas/admin.py` | | liberado | 2026-05-08 | COMPLETADO F2-T10 |
| `tools/api/app.py` | | liberado | 2026-05-08 | COMPLETADO F2-T10 |
| `tools/utils/forensic_agent.py` | | liberado | 2026-05-08 | COMPLETADO F1-T09 |
| `tools/test_vllm.py` | | liberado | 2026-05-08 | COMPLETADO F1-T10 |
| `tools/utils/db.py` | | liberado | 2026-05-08 | COMPLETADO F1-T14 |
| `tools/utils/request_handler.py` | | liberado | 2026-05-08 | COMPLETADO F1-T15 |
| `tests/test_valuation_engine.py` | Codex | F1-T16 ValuationEngine tests | 2026-05-08 | COMPLETAR F1-T16 |
| `requirements.txt` | | liberado | 2026-05-08 | COMPLETADO F1-T16 |
| `tests/test_valuation_engine.py` | | liberado | 2026-05-08 | COMPLETADO F1-T16 |
| `tests/test_forensic_agent.py` | | liberado | 2026-05-08 | COMPLETADO F1-T17 |
| `tests/test_scraper.py` | | liberado | 2026-05-08 | COMPLETADO F1-T18 |
| `tools/scrape_cars.py` | | liberado | 2026-05-08 | COMPLETADO F1-T18 |
| `tools/api/` | | liberado | 2026-05-08 | COMPLETADO F2-T01 |
| `tools/api/schemas/listings.py` | | liberado | 2026-05-08 | COMPLETADO F2-T03 |
| `tools/api/schemas/market.py` | | liberado | 2026-05-08 | COMPLETADO F2-T04 |
| `tools/api/schemas/auth.py` | | liberado | 2026-05-08 | COMPLETADO F2-T05 |
| `tools/api/routers/listings.py` | | liberado | 2026-05-08 | COMPLETADO F2-T06 |
| `tools/api/app.py` | | liberado | 2026-05-08 | COMPLETADO F2-T06 |
| `tools/api/routers/market.py` | | liberado | 2026-05-08 | COMPLETADO F2-T07 |
| `tools/api/app.py` | | liberado | 2026-05-08 | COMPLETADO F2-T09 |
| `tools/api/routers/dealers.py` | | liberado | 2026-05-08 | COMPLETADO F2-T08 |
| `tools/api/schemas/dealers.py` | | liberado | 2026-05-08 | COMPLETADO F2-T08 |
| `tools/api/dealer_store.py` | | liberado | 2026-05-08 | COMPLETADO F2-T09 |
| `tools/api/security.py` | | liberado | 2026-05-08 | COMPLETADO F2-T09 |
| `tools/api/routers/auth.py` | | liberado | 2026-05-08 | COMPLETADO F2-T09 |
| `tools/api/routers/listings.py` | | liberado | 2026-05-08 | COMPLETADO F2-T11/F2-T13 |
| `tools/api/schemas/listings.py` | | liberado | 2026-05-08 | COMPLETADO F2-T11/F2-T13 |
| `tools/api/middleware/rate_limiter.py` | | liberado | 2026-05-08 | COMPLETADO F2-T14 |
| `tools/api/app.py` | | liberado | 2026-05-08 | COMPLETADO F2-T14/F2-T19 |
| `main.py` | | liberado | 2026-05-08 | COMPLETADO F1-T05/F1-T07 |
| `tools/scrape_cars.py` | | liberado | 2026-05-08 | COMPLETADO F1-T03/F1-T04/F1-T07 |
| `tools/benchmark_scrapers.py` | | liberado | 2026-05-08 | COMPLETADO F1-T01/F1-T02 |
| `requirements.txt` | | liberado | 2026-05-07 | COMPLETADO F1-T01 |
| `tools/utils/db.py` | | liberado | 2026-05-07 | COMPLETADO F1-T11 |
| `tools/replenish_sessions.py` | | liberado | 2026-05-08 | COMPLETADO F1-T06 |
| `workflows/data_pipeline.md` | | liberado | 2026-05-08 | COMPLETADO F1-T21/F1-T07 |
| `workflows/secrets_management.md` | | liberado | 2026-05-08 | COMPLETADO F5-T20 |
| `frontend/` | | liberado | 2026-05-08 | COMPLETADO F3-T04/F3-T05 |
| `frontend/package.json` | | liberado | 2026-05-08 | COMPLETADO F3-T04 |
| `frontend/src/App.tsx` | | liberado | 2026-05-08 | COMPLETADO F3-T06 |
| `frontend/src/pages/Login.tsx` | | liberado | 2026-05-08 | COMPLETADO F3-T06 |
| `frontend/src/store/auth.ts` | | liberado | 2026-05-08 | COMPLETADO F3-T06 |
| `frontend/src/hooks/useAuth.ts` | | liberado | 2026-05-08 | COMPLETADO F3-T06 |
| `frontend/src/api/client.ts` | | liberado | 2026-05-08 | COMPLETADO F3-T06 |
| `frontend/src/pages/Dashboard.tsx` | | liberado | 2026-05-08 | COMPLETADO F3-T06 |
| `frontend/src/components/listings/ListingsTable.tsx` | | liberado | 2026-05-08 | COMPLETADO F3-T07 |
| `frontend/src/pages/Dashboard.tsx` | | liberado | 2026-05-08 | COMPLETADO F3-T07 |
| `frontend/src/lib/utils.ts` | | liberado | 2026-05-08 | COMPLETADO F3-T07 |
| `frontend/src/components/filters/FilterPanel.tsx` | | liberado | 2026-05-08 | COMPLETADO F3-T08 |
| `frontend/src/pages/Dashboard.tsx` | | liberado | 2026-05-08 | COMPLETADO F3-T08 |
| `frontend/src/store/filters.ts` | | liberado | 2026-05-08 | COMPLETADO F3-T08 |
| `frontend/src/components/market/ROIBarChart.tsx` | | liberado | 2026-05-08 | COMPLETADO F3-T09 |
| `frontend/src/pages/Dashboard.tsx` | | liberado | 2026-05-08 | COMPLETADO F3-T09 |
| `frontend/vite.config.ts` | | liberado | 2026-05-08 | COMPLETADO F3-T09 |
| `frontend/src/` | | liberado | 2026-05-08 | COMPLETADO F3-T10..F3-T21 |
| `frontend/e2e/` | | liberado | 2026-05-08 | COMPLETADO F3-T22 |
| `frontend/package.json` | | liberado | 2026-05-08 | COMPLETADO F3-T22 |
| `frontend/playwright.config.ts` | | liberado | 2026-05-08 | COMPLETADO F3-T22 |

---

## Backlog - Todas las Tareas

### FASE 1 - Data Pipeline & AI Core

| ID | Tarea | Propietario | Status | Bloqueos |
|----|-------|-------------|--------|----------|
| F1-T01 | Scrapling PoC - instalar library, ejecutar 20 paginas Milanuncios, registrar block rate + latencia | Codex | Done | - |
| F1-T02 | Scrapling Datadome benchmark - comparativa formal vs Playwright | Codex | Done | F1-T01 |
| F1-T03 | Integrar Scrapling en MilanunciosScraper | Codex | Done | F1-T02 |
| F1-T04 | Wallapop fix - corregir auth headers | Codex | Done | - |
| F1-T05 | Concurrent scraping en main.py pipeline | Codex | Done | F1-T04 |
| F1-T06 | Session pool auto-replenishment via 2captcha | Codex | Done | - |
| F1-T07 | Pre-filtro heuristico configurable desde .env | Codex | Done | - |
| F1-T08 | Mejorar prompt ForensicAgent - confidence_score, keywords ampliados, output schema v2 | Codex | Done | - |
| F1-T09 | RepairCostEngine real - tabla brand/damage_type -> cost_range_eur | Codex | Done | F1-T08 |
| F1-T10 | vLLM benchmark - `tools/test_vllm.py` throughput, p50/p95, VRAM RTX 3060 | Codex | Done | - |
| F1-T11 | SQLite aiosqlite - async pool + retry SQLITE_BUSY | Codex | Done | - |
| F1-T12 | Schema migration - condition_score, images_count, seller_type, location, price_history_json | Codex | Done | F1-T11 |
| F1-T13 | Cross-portal deduplication Milanuncios + Wallapop | Codex | Done | F1-T12 |
| F1-T14 | Price time-series en `price_history_json` | Codex | Done | F1-T12 |
| F1-T15 | Proxy rotation fallback - ScrapingBee/BrightData | Codex | Done | - |
| F1-T16 | Tests unitarios ValuationEngine >= 90% coverage | Codex | Done | - |
| F1-T17 | Tests unitarios ForensicAgent | Codex | Done | F1-T08 |
| F1-T18 | Tests unitarios parsers | Codex | Done | - |
| F1-T19 | SOP scraping_anti_bot.md | Claude Code | Done | - |
| F1-T20 | SOP ai_analysis_setup.md | Claude Code | Done | F1-T10 |
| F1-T21 | SOP data_pipeline.md | Claude Code | Done | F1-T11 |

### FASE 2 - API Layer & B2B Logic

| ID | Tarea | Propietario | Status | Bloqueos |
|----|-------|-------------|--------|----------|
| F2-T01 | FastAPI restructure - crear paquete `tools/api/` | Codex | Done | F1-T11 |
| F2-T02 | Pydantic schema ListingOut | Codex | Done | F2-T01 |
| F2-T03 | Pydantic schema ListingFilter | Codex | Done | F2-T01 |
| F2-T04 | Pydantic schemas market | Codex | Done | F2-T01 |
| F2-T05 | Pydantic schemas auth | Codex | Done | F2-T01 |
| F2-T06 | Router /listings | Codex | Done | F2-T02, F2-T03 |
| F2-T07 | Router /market | Codex | Done | F2-T04 |
| F2-T08 | Router /dealers | Codex | Done | F2-T05 |
| F2-T09 | Router /auth | Codex | Done | F2-T05 |
| F2-T10 | Router /admin | Codex | Done | F2-T08, F2-T09 |
| F2-T11 | Motor filtros dinamicos | Codex | Done | F2-T06 |
| F2-T12 | Full-text search `q` | Codex | Done | F2-T11 |
| F2-T13 | Paginacion completa | Codex | Done | F2-T06 |
| F2-T14 | Middleware rate limiter | Codex | Done | F2-T09 |
| F2-T15 | Middleware audit logger | Codex | Done | F2-T09 |
| F2-T16 | Dependency get_current_dealer() | Codex | Done | F2-T09 |
| F2-T17 | Dependency get_db() | Codex | Done | F1-T11 |
| F2-T18 | Error handlers RFC 7807 | Codex | Done | F2-T01 |
| F2-T19 | CORS config | Codex | Done | F2-T01 |
| F2-T20 | Health endpoints | Codex | Done | F2-T17 |
| F2-T21 | Integration tests router /listings | Codex | Done | F2-T06, F2-T13 |
| F2-T22 | Integration tests router /market | Codex | Done | F2-T07 |
| F2-T23 | Integration tests router /auth | Codex | Done | F2-T09 |
| F2-T24 | Diseno contrato API + OpenAPI customization | Claude Code | Done | F2-T06, F2-T07 |

### FASE 3 - Frontend B2B Dashboard

| ID | Tarea | Propietario | Status | Bloqueos |
|----|-------|-------------|--------|----------|
| F3-T01 | Research stack frontend | Claude Code | Done | - |
| F3-T02 | UX wireframes ASCII | Claude Code | Done | - |
| F3-T03 | Decision stack + component library | Claude Code | Done | F3-T01 |
| F3-T04 | Frontend scaffold | Codex | Done | F3-T03 |
| F3-T05 | API client layer | Codex | Done | F3-T04, F2-T06 |
| F3-T06 | Auth flow | Codex | Done | F3-T05, F2-T09 |
| F3-T07 | ListingsTable component | Codex | Done | F3-T05, F3-T01 |
| F3-T08 | FilterPanel component | Codex | Done | F3-T05 |
| F3-T09 | ROI BarChart component | Codex | Done | F3-T05, F2-T07 |
| F3-T10 | PriceTrend chart | Codex | Done | F3-T05, F2-T07 |
| F3-T11 | ListingDrawer component | Codex | Done | F3-T07 |
| F3-T12 | KPI Widgets | Codex | Done | F3-T05, F2-T07 |
| F3-T13 | Dashboard page | Codex | Done | F3-T07, F3-T08, F3-T09, F3-T12 |
| F3-T14 | MarketAnalysis page | Codex | Done | F3-T09, F3-T10 |
| F3-T15 | AlertCenter page | Codex | Done | F3-T05 |
| F3-T16 | SavedSearches component | Codex | Done | F3-T05 |
| F3-T17 | ExportButton component | Codex | Done | F3-T05 |
| F3-T18 | Responsive layout | Codex | Done | F3-T13 |
| F3-T19 | Dark mode | Codex | Done | F3-T04 |
| F3-T20 | Loading states | Codex | Done | F3-T13 |
| F3-T21 | Error boundaries | Codex | Done | F3-T05 |
| F3-T22 | Playwright E2E dealer flow | Codex | Done | F3-T13 |

### FASE 4 - Auth & Monetizacion

| ID | Tarea | Propietario | Status | Bloqueos |
|----|-------|-------------|--------|----------|
| F4-T01 | Dealer schema migration | Codex | Done | F2 completa |
| F4-T02 | API usage schema migration | Codex | Done | F4-T01 |
| F4-T03 | Saved searches schema migration | Codex | Done | F4-T01 |
| F4-T04 | Auth service - bcrypt + JWT | Codex | Done | F4-T01 |
| F4-T05 | Dealers persistence/service layer | Codex | Done | F4-T01 |
| F4-T06 | Login/register auth integration | Codex | Done | F4-T04 |
| F4-T07 | API key service | Codex | Done | F4-T01 |
| F4-T08 | Plan enum + limits | Codex | Done | F4-T01 |
| F4-T09 | Plan guard middleware | Codex | Done | F4-T08 |
| F4-T10 | Stripe SDK init | Codex | Done | - |
| F4-T11 | Stripe Products | Claude Code | Done | F4-T10 |
| F4-T12 | Stripe service | Codex | Done | F4-T10, F4-T11 |
| F4-T13 | Router /payments/checkout | Codex | Done | F4-T12 |
| F4-T14 | Router /payments/portal | Codex | Done | F4-T12 |
| F4-T15 | Router /webhooks/stripe | Codex | Done | F4-T12 |
| F4-T16 | Webhook checkout.session.completed | Codex | Done | F4-T15 |
| F4-T17 | Webhook invoice.payment_failed | Codex | Done | F4-T15 |
| F4-T18 | Webhook customer.subscription.deleted | Codex | Done | F4-T15 |
| F4-T19 | Email service via Resend | Codex | Done | - |
| F4-T20 | Router /auth/register | Codex | Done | F4-T06, F4-T12, F4-T19 |
| F4-T21 | Admin controls | Codex | Done | F4-T01, F4-T12 |
| F4-T22 | Tests Stripe webhooks | Codex | Done | F4-T16, F4-T17, F4-T18 |
| F4-T23 | Tests auth service | Codex | Done | F4-T06, F4-T07 |
| F4-T24 | SOP auth_monetization.md | Claude Code | Done | F4-T08, F4-T20 |
| F4-T25 | SOP stripe_integration.md | Claude Code | Done | F4-T15 |

### FASE 5 - DevOps & Despliegue

| ID | Tarea | Propietario | Status | Bloqueos |
|----|-------|-------------|--------|----------|
| F5-T01 | Dockerfile.pipeline | Codex | Done | F1 completa |
| F5-T02 | Dockerfile.api | Codex | Done | F2 completa |
| F5-T03 | Dockerfile.frontend | Codex | Done | F3 completa |
| F5-T04 | docker-compose.yml | Codex | Done | F5-T01, F5-T02, F5-T03 |
| F5-T05 | nginx.conf | Codex | Done | F5-T04 |
| F5-T06 | .env.production.example | Claude Code | Done | F4 completa |
| F5-T07 | backup_db.py | Codex | Done | - |
| F5-T08 | run_migrations.py prod-safe | Codex | Done | F4-T05 |
| F5-T09 | Structlog JSON | Codex | Done | F2-T15 |
| F5-T10 | Log rotation | Codex | Done | F5-T09 |
| F5-T11 | Prometheus metrics middleware | Codex | Done | F2-T01 |
| F5-T12 | Router /metrics | Codex | Done | F5-T11 |
| F5-T13 | Grafana dashboard JSON | Claude Code | Done | F5-T11 |
| F5-T14 | Systemd service unit | Codex | Done | F5-T04 |
| F5-T15 | setup_vps.sh | Codex | Done | - |
| F5-T16 | SSL/TLS Let's Encrypt | Codex | Done | F5-T05, F5-T15 |
| F5-T17 | GitHub Actions CI | Codex | Done | F1+F2+F3+F4 tests |
| F5-T18 | GitHub Actions CD | Codex | Done | F5-T17 |
| F5-T19 | Nginx rate limiting | Codex | Done | F5-T05 |
| F5-T20 | Secrets management doc | Claude Code | Done | - |
| F5-T21 | SOP devops_deployment.md | Claude Code | Done | F5-T04, F5-T15 |
| F5-T22 | SOP monitoring_alerts.md | Claude Code | Done | F5-T12, F5-T13 |

### FASE 6 - Pricing por ROI

| ID | Tarea | Propietario | Status | Bloqueos |
|----|-------|-------------|--------|----------|
| F6-T1 | Plan model — añadir roi_max_pct, history_days, api_key_access, forensic_full, export_enabled, poll_interval_minutes | Codex | Done | - |
| F6-T2 | Plan guard middleware — ROI injection + redaction (roi_redacted field, sin bloquear request) | Codex | Done | F6-T1 |
| F6-T3 | Router /listings — campo roi_redacted en response schema + endpoint /listings/{id} detalle | Codex | Done | F6-T2 |
| F6-T4 | Router /payments — actualizar plan names + Stripe price IDs (Free, Starter €49, Pro €99, Elite €199) | Codex | Done | F6-T1 |
| F6-T5 | setup_stripe_products.py — añadir Starter (€49) y Elite (€199), renombrar Basic→Pro | Codex | Done | F6-T4 |
| F6-T6 | Migration — añadir columnas roi_max_pct, history_days etc a tabla dealers | Codex | Todo | F6-T1 |
| F6-T7 | Tests — test_plan_guard_roi.py verificar redacción por plan | Codex | Done | F6-T2 |

### FASE 7 - Scrapers Adicionales

| ID | Tarea | Propietario | Status | Bloqueos |
|----|-------|-------------|--------|----------|
| F7-T1 | CochesNetScraper — HTML scraping article.mt-CardBasic, session pool, delay 2-3s | Codex | Todo | - |
| F7-T2 | AutoScout24Scraper — JSON-LD en script tag, session pool con cookies | Codex | Todo | - |
| F7-T3 | MotorScraper — HTML simple, sin proteccion significativa | Codex | Todo | - |
| F7-T4 | Normalizar campo portal en DB schema, deduplicacion cross-portal extendida | Codex | Todo | F7-T1, F7-T2, F7-T3 |
| F7-T5 | Benchmark yield/hora por portal en tools/benchmark_scrapers.py | Codex | Todo | F7-T1, F7-T2, F7-T3 |

### FASE 8 - Frontend Redesign (Linear/Vercel aesthetic)

| ID | Tarea | Propietario | Status | Bloqueos |
|----|-------|-------------|--------|----------|
| F8-T1 | index.css — nuevo sistema de tokens oscuros (background/surface/primary/accent/warning HSL) + escala tipografica Inter | Claude Code | Done | - |
| F8-T2 | AppShell.tsx — sidebar colapsable 64px→240px + top bar con busqueda y avatar | Claude Code | Done | F8-T1 |
| F8-T3 | ListingCard.tsx — rediseno con shimmer skeleton, ROI badge semaforo, hover glow | Claude Code | Done | F8-T2 |
| F8-T4 | ROIGauge.tsx — gauge semicircular Recharts roi_neto vs roi_bruto | Claude Code | Todo | F8-T3 |
| F8-T5 | KPIBar.tsx — 4 stats con animacion useCountUp | Claude Code | Done | F8-T2 |
| F8-T6 | CommandPalette.tsx — Cmd+K busqueda global con categorias | Claude Code | Todo | F8-T2 |
| F8-T7 | useToast.ts + ToastContainer — sistema de notificaciones (success/error/warning/info) | Claude Code | Done | F8-T2 |
| F8-T8 | Dashboard.tsx — refactor con KPIBar + ListingCard grid | Claude Code | Done | F8-T3, F8-T5 |
| F8-T9 | Market.tsx — grid de cards + filtros en sidebar colapsable | Claude Code | Done | F8-T3 |
| F8-T10 | Pricing.tsx — pagina publica con tabla 4 planes + toggle mensual/anual | Claude Code | Done | F6-T1 |
| F8-T11 | Onboarding.tsx — wizard 3 pasos primer login (marcas, precio, Telegram) | Claude Code | Todo | F8-T7 |
| F8-T12 | ListingDetail.tsx — vista detalle con ROIGauge + fotos + ForensicAgent output | Claude Code | Todo | F8-T4 |
| F8-T13 | Alerts.tsx — timeline redesign con badge portal y toggle activo/inactivo | Claude Code | Todo | F8-T7 |
| F8-T14 | Login.tsx — split layout: form izquierda, value prop + screenshot derecha | Claude Code | Done | F8-T1 |

---

## Completado

| ID | Tarea | Propietario | Fecha | Verificacion |
|----|-------|-------------|-------|-------------|
| F5-T19 | Nginx rate limiting | Codex | 2026-05-10 | `py_compile`; `python -m pytest tests\test_nginx_rate_limiting.py tests\test_letsencrypt_setup.py -q` -> 7 passed; `docker compose -f docker-compose.yml config --no-interpolate`; `python -m pytest -q` -> 199 passed, 1 skipped |
| F5-T18 | GitHub Actions CD | Codex | 2026-05-10 | `py_compile`; `python -m pytest tests\test_cd_workflow.py tests\test_ci_workflow.py -q` -> 8 passed; `python -m pytest -q` -> 196 passed, 1 skipped |
| F5-T17 | GitHub Actions CI | Codex | 2026-05-10 | `python -m pytest tests\test_ci_workflow.py tests\test_letsencrypt_setup.py -q` -> 8 passed; `npm run lint`; `npm run build`; `npm run test:e2e` -> 1 passed; `docker compose -f docker-compose.yml config --no-interpolate`; `python -m pytest -q` -> 192 passed, 1 skipped |
| F5-T16 | SSL/TLS Let's Encrypt | Codex | 2026-05-10 | `docker compose -f docker-compose.yml config --no-interpolate`; `py_compile`; `python -m pytest tests\test_letsencrypt_setup.py -q` -> 4 passed; `python -m pytest -q` -> 188 passed, 1 skipped |
| F5-T15 | setup_vps.sh | Codex | 2026-05-10 | `py_compile`; `python -m pytest tests\test_setup_vps_script.py -q` -> 4 passed, 1 skipped; `python -m pytest -q` -> 184 passed, 1 skipped |
| F5-T14 | Systemd service unit | Codex | 2026-05-10 | `py_compile`; `python -m pytest tests\test_systemd_service_unit.py -q` -> 2 passed; `python -m pytest -q` -> 180 passed |
| F5-T12 | Router /metrics | Codex | 2026-05-10 | `py_compile`; `python -m pytest tests\test_metrics_router.py tests\test_prometheus_metrics_middleware.py -q` -> 5 passed; `python -m pytest -q` -> 178 passed |
| F5-T11 | Prometheus metrics middleware | Codex | 2026-05-10 | `py_compile`; `python -m pytest tests\test_prometheus_metrics_middleware.py -q` -> 3 passed; `python -m pytest -q` -> 176 passed |
| F5-T10 | Log rotation | Codex | 2026-05-10 | `py_compile`; `python -m pytest tests\test_log_rotation.py tests\test_structlog_logging.py tests\test_api_audit_logger.py -q` -> 5 passed; `python -m pytest -q` -> 173 passed |
| F5-T09 | Structlog JSON | Codex | 2026-05-10 | `py_compile`; `python -m pytest tests\test_structlog_logging.py tests\test_api_audit_logger.py -q` -> 3 passed; `python -m pytest -q` -> 171 passed |
| F5-T08 | run_migrations.py prod-safe | Codex | 2026-05-10 | `py_compile`; `python -m pytest tests\test_run_migrations.py -q` -> 6 passed; `python -m pytest -q` -> 169 passed |
| INIT | Shared agent coordination setup | Codex | 2026-05-03 | AGENTS.md + coordination.md creados |
| ARCH | Master roadmap generado | Claude Code | 2026-05-07 | `workflows/master_roadmap.md` + coordination actualizado |
| F1-T19 | SOP scraping_anti_bot.md | Claude Code | 2026-05-07 | `workflows/scraping_anti_bot.md` creado |
| F1-T11 | SQLite WAL hardening | Codex | 2026-05-07 | `py_compile`; escritura concurrente real OK |
| F1-T21 | SOP data_pipeline.md | Claude Code | 2026-05-07 | `workflows/data_pipeline.md` creado |
| F1-T01 | Scrapling PoC | Codex | 2026-05-07 | benchmark reports en `.tmp/` |
| F1-T02 | Scrapling Datadome benchmark | Codex | 2026-05-08 | Scrapling 20p, 0% block, 840 listings |
| F1-T03 | Integrar Scrapling en MilanunciosScraper | Codex | 2026-05-08 | `py_compile`; scrape Milanuncios 1p OK |
| F1-T04 | Wallapop auth headers | Codex | 2026-05-08 | `py_compile`; scrape Wallapop 1p OK |
| F1-T05 | Concurrent scraping | Codex | 2026-05-08 | `py_compile`; mock concurrente elapsed 0.265s |
| F1-T06 | Session pool auto-replenishment | Codex | 2026-05-08 | `py_compile`; dry-runs OK |
| F1-T07 | Pre-filtro heuristico configurable | Codex | 2026-05-08 | `py_compile`; asserts inline OK |
| F1-T08 | Mejorar prompt ForensicAgent - schema v2 | Codex | 2026-05-08 | `python -m py_compile main.py tools\utils\forensic_agent.py tools\telegram_notifier.py`; asserts inline de schema v2, confidence clamp, keywords y fallback OK |
| F1-T09 | RepairCostEngine real | Codex | 2026-05-08 | `python -m py_compile tools\utils\forensic_agent.py main.py`; asserts inline de rangos, marcas premium, danos multiples y `analyze_batch` OK |
| F1-T10 | vLLM benchmark | Codex | 2026-05-08 | `python -m py_compile tools\test_vllm.py`; `--help`; mock OpenAI-compatible OK; smoke local genero reportes con 0 exitos porque vLLM/Ollama no respondieron en endpoint local |
| F1-T12 | Schema migration listings | Codex | 2026-05-08 | `python -m py_compile tools\utils\db.py`; migracion real sobre DB vieja temporal + upsert campos nuevos OK |
| F1-T13 | Cross-portal deduplication | Codex | 2026-05-08 | `python -m py_compile tools\utils\db.py`; DB temporal con Milanuncios/Wallapop dentro de tolerancia crea 1 par; fuera de tolerancia no duplica |
| F1-T14 | Price time-series | Codex | 2026-05-08 | `python -m py_compile tools\utils\db.py`; DB temporal acumula cambios de precio y conserva historial entrante |
| F1-T15 | Proxy rotation fallback | Codex | 2026-05-08 | `python -m py_compile tools\utils\request_handler.py`; mock 403 con pool bajo activa ScrapingBee; respuesta Bright Data normalizada OK |
| F1-T16 | Tests ValuationEngine | Codex | 2026-05-08 | `python -m pytest tests\test_valuation_engine.py --cov=tools.utils.valuation_engine --cov-report=term-missing` -> 12 passed, 94% coverage |
| F1-T17 | Tests ForensicAgent | Codex | 2026-05-08 | `python -m pytest tests\test_forensic_agent.py --cov=tools.utils.forensic_agent --cov-report=term-missing` -> 12 passed, 95% coverage |
| F1-T18 | Tests parsers | Codex | 2026-05-08 | `python -m py_compile tools\scrape_cars.py tools\market_catalog.py`; `python -m pytest tests\test_scraper.py` -> 22 passed |
| F2-T01 | FastAPI package scaffold | Codex | 2026-05-08 | `python -m py_compile tools\api\...`; import `tools.api.app:app` OK |
| F2-T02 | ListingOut schema | Codex | 2026-05-08 | `python -m py_compile tools\api\schemas\listings.py`; inline Pydantic validation OK |
| F2-T03 | ListingFilter schema | Codex | 2026-05-08 | `python -m py_compile tools\api\schemas\listings.py`; inline validation OK |
| F2-T04 | Market schemas | Codex | 2026-05-08 | `python -m py_compile tools\api\schemas\market.py`; inline validation OK |
| F2-T05 | Auth schemas | Codex | 2026-05-08 | `python -m py_compile tools\api\schemas\auth.py`; inline validation OK |
| F2-T07 | Market router | Codex | 2026-05-08 | `python -m py_compile tools\api\routers\market.py`; TestClient con DB temporal OK |
| F2-T08 | Dealers router | Codex | 2026-05-08 | `python -m py_compile tools\api\routers\dealers.py`; TestClient con DB temporal OK |
| F2-T09 | Auth router | Codex | 2026-05-08 | `python -m py_compile tools\api\routers\auth.py`; TestClient con DB temporal login/refresh/API key OK |
| F2-T11 | Motor filtros listings | Codex | 2026-05-08 | `python -m py_compile tools\api\routers\listings.py`; TestClient con DB temporal filtros OK |
| F2-T13 | Paginacion listings | Codex | 2026-05-08 | TestClient con DB temporal `{items,total,page,size}` OK |
| F2-T14 | Rate limiter middleware | Codex | 2026-05-08 | `python -m py_compile tools\api\middleware\rate_limiter.py`; TestClient limite bajo -> 429 OK |
| F2-T19 | CORS config | Codex | 2026-05-08 | TestClient OPTIONS con `Origin=http://localhost:5173` devuelve cabeceras CORS OK |
| F2-T06 | Listings router | Codex | 2026-05-08 | `python -m py_compile tools\api\app.py tools\api\routers\listings.py`; TestClient con DB temporal OK |
| F2-T10 | Router /admin | Codex | 2026-05-08 | `python -m py_compile tools\api\app.py tools\api\routers\admin.py tools\api\schemas\admin.py`; TestClient temporal stats/health/plan + rechazo no-admin/X-Dealer-ID OK; OpenAPI admin routes OK |
| F2-T12 | Full-text search q | Codex | 2026-05-08 | `python -m py_compile tools\utils\db.py tools\api\routers\listings.py tools\api\app.py`; TestClient temporal FTS q + filtros + fallback LIKE OK; OpenAPI listings OK |
| F2-T15 | Middleware audit logger | Codex | 2026-05-09 | `python -m py_compile tools\api\app.py tools\api\middleware\audit_logger.py tools\api\middleware\__init__.py tests\test_api_audit_logger.py`; `python -m pytest tests\test_api_audit_logger.py -q`; `python -m pytest -q` -> 47 passed |
| F2-T16 | Dependency get_current_dealer() | Codex | 2026-05-09 | `python -m py_compile tools\api\dependencies\auth.py tools\api\dependencies\__init__.py tools\api\routers\auth.py tools\api\routers\dealers.py tools\api\routers\admin.py tests\test_api_dependencies.py`; `python -m pytest tests\test_api_dependencies.py -q`; `python -m pytest -q` -> 52 passed |
| F2-T17 | Dependency get_db() | Codex | 2026-05-09 | `python -m py_compile tools\api\dependencies\db.py tools\api\dependencies\__init__.py tools\api\routers\listings.py tools\api\routers\market.py tools\api\routers\admin.py tests\test_api_db_dependency.py`; `python -m pytest tests\test_api_db_dependency.py -q`; `python -m pytest -q` -> 54 passed |
| F2-T18 | Error handlers RFC 7807 | Codex | 2026-05-09 | `python -m py_compile tools\api\errors.py tools\api\app.py tests\test_api_error_handlers.py`; `python -m pytest tests\test_api_error_handlers.py -q`; `python -m pytest -q` -> 57 passed |
| F2-T20 | Health endpoints | Codex | 2026-05-09 | `python -m py_compile tools\api\app_meta.py tools\api\schemas\health.py tools\api\routers\health.py tools\api\app.py tools\api\schemas\__init__.py tools\api\routers\__init__.py tests\test_api_health.py`; `python -m pytest tests\test_api_health.py -q`; `python -m pytest -q` -> 60 passed |
| F2-T21 | Integration tests router /listings | Codex | 2026-05-09 | `python -m py_compile tests\test_api_listings.py`; `python -m pytest tests\test_api_listings.py -q`; `python -m pytest -q` -> 65 passed |
| F2-T22 | Integration tests router /market | Codex | 2026-05-09 | `python -m py_compile tests\test_api_market.py`; `python -m pytest tests\test_api_market.py -q`; `python -m pytest -q` -> 70 passed |
| F2-T23 | Integration tests router /auth | Codex | 2026-05-09 | `python -m py_compile tests\test_api_auth.py`; `python -m pytest tests\test_api_auth.py -q`; `python -m pytest -q` -> 76 passed |
| F4-T01 | Dealer schema migration | Codex | 2026-05-09 | `python -m py_compile tools\api\dealer_store.py tests\test_api_dealer_schema.py`; `python -m pytest tests\test_api_dealer_schema.py -q`; `python -m pytest -q` -> 78 passed |
| F4-T02 | API usage schema migration | Codex | 2026-05-09 | `python -m py_compile tests\test_api_usage_schema.py`; `python -m pytest tests\test_api_usage_schema.py -q`; `python -m pytest -q` -> 80 passed |
| F4-T03 | Saved searches schema migration | Codex | 2026-05-09 | `python -m py_compile tests\test_api_saved_searches_schema.py`; `python -m pytest tests\test_api_saved_searches_schema.py -q`; `python -m pytest -q` -> 83 passed |
| F4-T04 | Auth service - bcrypt + JWT | Codex | 2026-05-09 | `python -m pip install bcrypt PyJWT`; `python -m py_compile tools\api\services\auth_service.py tools\api\services\__init__.py tests\test_auth_service.py`; `python -m pytest tests\test_auth_service.py -q`; `python -m pytest -q` -> 89 passed |
| F4-T05 | Dealers persistence/service layer | Codex | 2026-05-09 | `python -m py_compile tools\api\services\dealer_service.py tests\test_dealer_service.py`; `python -m pytest tests\test_dealer_service.py -q`; `python -m pytest -q` -> 94 passed |
| F4-T06 | Login/register auth integration | Codex | 2026-05-09 | `python -m py_compile tools\api\routers\auth.py tools\api\dependencies\auth.py tools\api\dealer_store.py tools\api\services\auth_service.py tests\test_api_auth.py tests\test_api_dependencies.py`; `python -m pytest tests\test_api_auth.py tests\test_api_dependencies.py tests\test_auth_service.py -q`; `python -m pytest -q` -> 94 passed |
| F4-T07 | API key service | Codex | 2026-05-09 | `python -m py_compile tools\api\services\api_key_service.py tools\api\routers\auth.py tools\api\dependencies\auth.py tests\test_api_key_service.py tests\test_api_auth.py tests\test_api_dependencies.py`; `python -m pytest tests\test_api_key_service.py tests\test_api_auth.py tests\test_api_dependencies.py -q`; `python -m pytest -q` -> 98 passed |
| F4-T08 | Plan enum + limits | Codex | 2026-05-09 | `python -m py_compile tools\api\models\plan.py tools\api\models\__init__.py tools\api\schemas\dealers.py tools\api\schemas\admin.py tools\api\services\dealer_service.py tests\test_plan_model.py`; `python -m pytest tests\test_plan_model.py -q`; `python -m pytest -q` -> 103 passed |
| F4-T09 | Plan guard middleware | Codex | 2026-05-09 | `python -m py_compile tools\api\middleware\plan_guard.py tools\api\middleware\__init__.py tools\api\app.py tests\test_plan_guard_middleware.py`; `python -m pytest tests\test_plan_guard_middleware.py -q`; `python -m pytest -q` -> 107 passed |
| F4-T10 | Stripe SDK init | Codex | 2026-05-09 | `python -m pip install "stripe>=14.4.0"`; `python -m py_compile tools\api\services\stripe_client.py tests\test_stripe_client.py`; `python -m pytest tests\test_stripe_client.py -q`; `python -m pytest -q` -> 111 passed |
| F4-T12 | Stripe service | Codex | 2026-05-09 | `python -m py_compile tools\api\services\stripe_service.py tools\api\services\__init__.py`; `python -m pytest tests\test_stripe_service.py -q` -> 9 passed; `python -m pytest -q` -> 127 passed |
| F4-T13 | Router /payments/checkout | Codex | 2026-05-10 | `python -m py_compile tools\api\routers\payments.py tools\api\schemas\payments.py tools\api\app.py tools\api\routers\__init__.py tools\api\schemas\__init__.py tests\test_payments_checkout.py`; `python -m pytest tests\test_payments_checkout.py -q` -> 5 passed; `python -m pytest -q` -> 132 passed |
| F4-T14 | Router /payments/portal | Codex | 2026-05-10 | `python -m py_compile tools\api\routers\payments.py tools\api\schemas\payments.py tools\api\schemas\__init__.py tests\test_payments_portal.py`; `python -m pytest tests\test_payments_portal.py -q` -> 5 passed; `python -m pytest -q` -> 137 passed |
| F4-T15 | Router /webhooks/stripe | Codex | 2026-05-10 | `python -m py_compile tools\api\routers\webhooks.py tools\api\app.py tools\api\routers\__init__.py tests\test_stripe_webhooks_router.py`; `python -m pytest tests\test_stripe_webhooks_router.py -q` -> 4 passed; `python -m pytest -q` -> 141 passed |
| F4-T16 | Webhook checkout.session.completed | Codex | 2026-05-10 | `python -m py_compile tools\api\routers\webhooks.py tests\test_stripe_webhook_checkout_completed.py tests\test_stripe_webhooks_router.py`; `python -m pytest tests\test_stripe_webhook_checkout_completed.py tests\test_stripe_webhooks_router.py -q` -> 8 passed; `python -m pytest -q` -> 145 passed |
| F4-T17 | Webhook invoice.payment_failed | Codex | 2026-05-10 | `python -m py_compile tools\api\routers\webhooks.py tools\api\services\dealer_service.py tests\test_dealer_service.py tests\test_stripe_webhook_payment_failed.py`; `python -m pytest tests\test_dealer_service.py tests\test_stripe_webhook_payment_failed.py -q` -> 8 passed; `python -m pytest -q` -> 148 passed |
| F4-T18 | Webhook customer.subscription.deleted | Codex | 2026-05-10 | `python -m py_compile tools\api\routers\webhooks.py tests\test_stripe_webhook_subscription_deleted.py`; `python -m pytest tests\test_stripe_webhook_subscription_deleted.py -q` -> 3 passed; `python -m pytest -q` -> 151 passed |
| F4-T19 | Email service via Resend | Codex | 2026-05-09 | `python -m pip install "resend[async]"`; `python -m py_compile tools\api\services\email_service.py tests\test_email_service.py`; `python -m pytest tests\test_email_service.py -q`; `python -m pytest -q` -> 115 passed |
| F4-T20 | Router /auth/register | Codex | 2026-05-10 | `python -m py_compile tools\api\routers\auth.py tools\api\schemas\auth.py tools\api\schemas\__init__.py tests\test_auth_register.py`; `python -m pytest tests\test_auth_register.py -q` -> 3 passed; `python -m pytest -q` -> 154 passed |
| F4-T21 | Admin controls | Codex | 2026-05-10 | `python -m py_compile tools\api\routers\admin.py tools\api\schemas\admin.py tests\test_admin_controls.py`; `python -m pytest tests\test_admin_controls.py -q` -> 4 passed; `python -m pytest -q` -> 158 passed |
| F4-T22 | Tests Stripe webhooks | Codex | 2026-05-10 | `python -m py_compile tests\test_stripe_webhooks_integration.py`; `python -m pytest tests\test_stripe_webhooks_integration.py -q` -> 1 passed; `python -m pytest -q` -> 159 passed |
| F5-T01 | Dockerfile.pipeline | Codex | 2026-05-10 | `docker --version` OK; `docker build -f Dockerfile.pipeline -t agartha-pipeline:test .` bloqueado porque Docker daemon/Desktop no esta arrancado (`dockerDesktopLinuxEngine` no disponible) |
| F5-T02 | Dockerfile.api | Codex | 2026-05-10 | `python -m py_compile tools\api\app.py`; `docker build -f Dockerfile.api -t agartha-api:test .` bloqueado porque Docker daemon/Desktop no esta arrancado (`dockerDesktopLinuxEngine` no disponible) |
| F5-T03 | Dockerfile.frontend | Codex | 2026-05-10 | `npm run build` OK; `docker build -f Dockerfile.frontend -t agartha-frontend:test .` bloqueado porque Docker daemon/Desktop no esta arrancado (`dockerDesktopLinuxEngine` no disponible) |
| F5-T04 | docker-compose.yml | Codex | 2026-05-10 | `docker compose -f docker-compose.yml config` OK (nota: expande `.env`, no pegar salida en logs publicos) |
| F5-T05 | nginx.conf | Codex | 2026-05-10 | `docker compose -f docker-compose.yml config --no-interpolate` OK; sintaxis nginx no probada en contenedor porque Docker daemon/Desktop no esta arrancado |
| F5-T07 | backup_db.py | Codex | 2026-05-10 | `python -m py_compile tools\backup_db.py tests\test_backup_db.py`; `python -m pytest tests\test_backup_db.py -q` -> 4 passed; `python -m pytest -q` -> 163 passed |
| F4-T23 | Tests auth service | Codex | 2026-05-09 | `python -m py_compile tests\test_auth_hardening.py`; `python -m pytest tests\test_auth_hardening.py -q`; `python -m pytest -q` -> 118 passed |
| F3-T01 | Research stack frontend | Claude Code | 2026-05-08 | find-skills x6; stack documentado |
| F3-T02 | UX wireframes ASCII | Claude Code | 2026-05-08 | `workflows/frontend_b2b_design.md` |
| F3-T03 | Decision stack frontend | Claude Code | 2026-05-08 | React+TS+Vite/shadcn/TanStack/Recharts/Zustand |
| F3-T04 | Frontend scaffold | Codex | 2026-05-08 | `npm run build` OK; `npm run lint` OK; Vite dev server background en `http://127.0.0.1:5173/` responde 200 |
| F3-T05 | API client layer | Codex | 2026-05-08 | `npm run build` OK; hooks/client compilan contra tipos locales derivados de schemas FastAPI |
| F3-T06 | Auth flow | Codex | 2026-05-08 | `npm run build` OK; `npm run lint` OK; `/` y `/login` responden 200 en Vite |
| F3-T07 | ListingsTable component | Codex | 2026-05-08 | `npm run build` OK; `npm run lint` OK; `/login` responde 200 en Vite |
| F3-T08 | FilterPanel component | Codex | 2026-05-08 | `npm run build` OK; `npm run lint` OK; `/login` responde 200 en Vite |
| F3-T09 | ROI BarChart component | Codex | 2026-05-08 | `npm run build` OK sin chunk warning tras manual chunks; `npm run lint` OK; `/login` responde 200 en Vite |
| F3-T10 | PriceTrend chart | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T11 | ListingDrawer component | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T12 | KPI Widgets | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T13 | Dashboard page | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T14 | MarketAnalysis page | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T15 | AlertCenter page | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T16 | SavedSearches component | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T17 | ExportButton component | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T18 | Responsive layout | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T19 | Dark mode | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T20 | Loading states | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T21 | Error boundaries | Codex | 2026-05-08 | `npm run build`; `npm run lint`; `npm run test:e2e` |
| F3-T22 | Playwright E2E dealer flow | Codex | 2026-05-08 | `npx playwright install chromium`; `npm run test:e2e` -> 1 passed |
| F5-T20 | Secrets management doc | Claude Code | 2026-05-08 | `workflows/secrets_management.md` |
| F1-T20 | SOP ai_analysis_setup.md | Claude Code | 2026-05-08 | `workflows/ai_analysis_setup.md` creado |
| F2-T24 | Contrato API + OpenAPI | Claude Code | 2026-05-08 | `tools/api/app.py` enriquecido; 4 routers con summaries; `workflows/api_contract.md` creado |
| F4-T11 | Stripe Products | Claude Code | 2026-05-09 | `tools/api/setup_stripe_products.py` creado; `.env.example` ampliado; `py_compile` OK |
| F5-T13 | Grafana dashboard JSON | Claude Code | 2026-05-10 | `deploy/grafana/agartha_dashboard.json` — 15 paneles; JSON válido (`json.load` OK) |
| F4-T24 | SOP auth_monetization.md | Claude Code | 2026-05-10 | `workflows/auth_monetization.md` creado |
| F4-T25 | SOP stripe_integration.md | Claude Code | 2026-05-10 | `workflows/stripe_integration.md` creado |
| F5-T06 | .env.production.example | Claude Code | 2026-05-10 | `.env.production.example` creado con todas las vars de producción |
| F5-T21 | SOP devops_deployment.md | Claude Code | 2026-05-10 | `workflows/devops_deployment.md` creado |
| F5-T22 | SOP monitoring_alerts.md | Claude Code | 2026-05-10 | `workflows/monitoring_alerts.md` creado |

## Handoffs

| De | Para | Resumen | Siguiente paso |
|----|------|---------|---------------|
| Codex | Claude Code/Frontend | F6 ROI paywall listo: `/listings` incluye `roi_redacted`; cuando es `true`, ROI, market price, repair/condition, historial y forense viajan sin datos premium. Planes canonicos: `free`, `starter`, `pro`, `elite`, `admin`; legacy `trial/basic/premium` se normaliza. | Ajustar UI/pricing F8 para mostrar CTA/blur sobre `roi_redacted` y usar env vars Stripe `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_ELITE`. |
| Claude Code | Codex | F4-T11 completado: `tools/api/setup_stripe_products.py` crea/reutiliza Products + Prices BASIC (€79/mo) y PREMIUM (€199/mo). Ejecutar el script con `STRIPE_SECRET_KEY` válida para obtener `STRIPE_PRICE_BASIC` y `STRIPE_PRICE_PREMIUM`. | F4-T12 (Stripe service) desbloqueado. Consumir `stripe_client.configure_stripe()` y usar los price IDs del `.env`. |
| Codex | Claude Code | Shared coordination files disponibles. | Leer AGENTS.md y este archivo antes de cualquier edicion. |
| Claude Code | Codex | Master roadmap y coordination inicializados. | Iniciar F1-T01 y F1-T11. |
| Codex | Claude Code | F1-T11 completado; `tools/utils/db.py` expone API async con pool aiosqlite. | F1-T21 desbloqueado. |
| Claude Code | Codex | F3-T01/02/03 completados; stack frontend definido. | F3-T04 scaffold con Vite React TS y dependencias documentadas. |
| Codex | Frontend | F2-T07 listo: `/market/stats`, `/market/by-brand`, `/market/roi-histogram`, `/market/trends`. | Consumir estos endpoints para KPI, graficas ROI y tendencias. |
| Codex | Frontend | F2-T08 listo: `/dealers`, `/dealers/me`, `PATCH /dealers/me`. | Usar para perfil de concesionario hasta que F4 endurezca monetizacion/auth. |
| Codex | Frontend | F2-T09 listo: `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/api-key`. | Usar login con email/password y bearer token; guardar API key solo cuando `/auth/api-key` la devuelve. |
| Codex | Frontend | F2-T11/F2-T13 listo: `/listings` devuelve `{items,total,page,size}` y acepta `q`, `brand`, `model`, `portal`, `seller_type`, `forensic_status`, rangos year/price y `min_roi`. | Usar `page` + `size` para tablas B2B; `size` max 100. |
| Codex | Frontend | F2-T14/F2-T19 listo: CORS configurable y rate limit MVP con headers `X-RateLimit-*`. | Configurar `AGARTHA_CORS_ORIGINS` con el origen real del frontend al desplegar. |
| Codex | Codex | Auth actual usa PBKDF2 + tokens HMAC stdlib y tabla `dealers` minima. | En F4 migrar/endurencer con servicio auth dedicado, JWT/bcrypt si se decide, blacklist y limites por plan. |
| Codex | Codex | F3-T04/F3-T05 listos en `frontend/`: scaffold Vite React TS, Tailwind/shadcn base, Axios client con refresh JWT, TanStack Query hooks, Zustand filters y dashboard shell conectado. `/find-skills` adicional ejecutado: resultados React/Vite/Tailwind tenian installs bajos; se mantuvo decision F3-T03. `npm audit` reporta 2 moderadas por Vite 5/esbuild dev server; no se fuerza Vite 8 para respetar stack acordado. | Continuar F3-T06 auth flow o F3-T07/F3-T08 UI real sobre hooks existentes. Dev server background: `http://127.0.0.1:5173/`. |
| Codex | Codex | F3-T06 listo: rutas protegidas por tokens locales, `/login` llama `/auth/login`, logout limpia estado aunque falle red, y el cliente emite evento de cambio de auth. F2-T16 ya permite Bearer en `/dealers/me` y mantiene `X-API-Key`/`X-Dealer-ID` legacy. | Continuar F4 auth hardening cuando toque: JWT/bcrypt dedicado, blacklist y limites por plan. |
| Codex | Codex | F3-T07 listo: `ListingsTable` usa TanStack Table + Virtual, muestra estado/error/vacio, ordenacion local por columnas y pagina contra `/listings` mediante `useFilterStore`. | Continuar F3-T08 FilterPanel para sacar los filtros del dashboard y ampliar marca/modelo/portal/year/price/forense. |
| Codex | Codex | F3-T08 listo: `FilterPanel` concentra filtros soportados por `/listings`, limpia valores vacios y reinicia pagina al cambiar filtros. | Continuar F3-T09/F3-T10 con graficas Recharts sobre hooks de `/market`. |
| Codex | Codex | F3-T09 listo: `ROIBarChart` consume `/market/by-brand`, maneja loading/error/empty y Vite separa chunk `charts`; `chunkSizeWarningLimit` ajustado a 650 KB por peso de Recharts. | Continuar F3-T10 PriceTrend chart y F3-T12 KPIWidgets extraction. |
| Codex | Codex | F3 frontend completo: dashboard, mercado, alertas, busquedas guardadas, drawer, export CSV, dark mode, responsive layout, loading states, error boundary y E2E dealer flow. Alertas y busquedas usan derivacion/localStorage porque aun no existen endpoints dedicados. | Siguiente bloque natural: F5-T03 Dockerfile.frontend o cerrar pendientes F2/F4 que desbloquean perfil bearer y endpoints reales de alertas/searches. |

## Registro de Cambios

| Fecha | Agente | Resumen | Verificacion |
|-------|--------|---------|-------------|
| 2026-05-10 | Codex | F6-T1/F6-T2/F6-T4/F6-T5 completados: planes Free/Starter/Pro/Elite con `roi_max_pct`; `/listings` redacta por SQL campos premium sobre el cap y devuelve `roi_redacted`; Stripe checkout/products pasan a Starter 49, Pro 99, Elite 199 con aliases legacy. | `py_compile`; `python -m pytest tests\test_plan_model.py tests\test_plan_guard_middleware.py tests\test_plan_guard_roi.py tests\test_stripe_client.py tests\test_stripe_service.py tests\test_payments_checkout.py tests\test_stripe_webhook_checkout_completed.py tests\test_stripe_webhook_subscription_deleted.py tests\test_stripe_webhooks_integration.py -q` -> 37 passed; `python -m pytest -q` -> 201 passed, 1 skipped |
| 2026-05-10 | Codex | Verificacion Docker posterior a F5: corregido `requirements.txt` quitando comillas de `uvicorn[standard]`; build completo de compose y smoke de API/frontend/nginx/pipeline OK. | `docker compose build`; `/api/health` OK; `/api/metrics` OK; `nginx -t` OK; smokes internos OK; `python -m pytest -q` -> 199 passed, 1 skipped |
| 2026-05-10 | Codex | F5-T19 completado: `nginx.conf` y plantilla SSL aplican `limit_req_zone` por IP para API general/auth y devuelven 429 sin limitar ACME. | `py_compile`; `python -m pytest tests\test_nginx_rate_limiting.py tests\test_letsencrypt_setup.py -q` -> 7 passed; `docker compose -f docker-compose.yml config --no-interpolate`; `python -m pytest -q` -> 199 passed, 1 skipped |
| 2026-05-10 | Codex | F5-T18 completado: `.github/workflows/cd.yml` despliega por SSH al VPS tras CI OK/manual, resetea main, build compose, migra DB en contenedor API y reinicia systemd. | `py_compile`; `python -m pytest tests\test_cd_workflow.py tests\test_ci_workflow.py -q` -> 8 passed; `python -m pytest -q` -> 196 passed, 1 skipped |
| 2026-05-10 | Codex | F5-T17 completado: `.github/workflows/ci.yml` ejecuta Python tests, frontend lint/build/E2E y validacion de compose con Actions checkout/setup-python/setup-node v6. | `python -m pytest tests\test_ci_workflow.py tests\test_letsencrypt_setup.py -q` -> 8 passed; `npm run lint`; `npm run build`; `npm run test:e2e` -> 1 passed; `docker compose -f docker-compose.yml config --no-interpolate`; `python -m pytest -q` -> 192 passed, 1 skipped |
| 2026-05-10 | Codex | F5-T16 completado: servicio `certbot` en compose, plantilla nginx SSL, script `tools/setup_letsencrypt.sh` y timer/service systemd para renovacion con reload de nginx. | `docker compose -f docker-compose.yml config --no-interpolate`; `py_compile`; `python -m pytest tests\test_letsencrypt_setup.py -q` -> 4 passed; `python -m pytest -q` -> 188 passed, 1 skipped |
| 2026-05-10 | Codex | F5-T15 completado: `setup_vps.sh` instala paquetes base, Docker oficial, prepara `/opt/agartha`, instala systemd, configura UFW y arranca solo si existe `.env`. | `py_compile`; `python -m pytest tests\test_setup_vps_script.py -q` -> 4 passed, 1 skipped; `python -m pytest -q` -> 184 passed, 1 skipped |
| 2026-05-10 | Codex | F5-T14 completado: `deploy/systemd/agartha.service` gestiona el stack Docker Compose desde `/opt/agartha` con `Requires=docker.service`, `RemainAfterExit` y reload/stop. | `py_compile`; `python -m pytest tests\test_systemd_service_unit.py -q` -> 2 passed; `python -m pytest -q` -> 180 passed |
| 2026-05-10 | Codex | F5-T12 completado: router publico `/metrics` expone el registry Prometheus con `CONTENT_TYPE_LATEST` y evita autocontar scrapes. | `py_compile`; `python -m pytest tests\test_metrics_router.py tests\test_prometheus_metrics_middleware.py -q` -> 5 passed; `python -m pytest -q` -> 178 passed |
| 2026-05-10 | Codex | F5-T11 completado: middleware Prometheus con contador por metodo/path/status, histograma de latencia y gauge in-flight sobre registry propio de Agartha. | `py_compile`; `python -m pytest tests\test_prometheus_metrics_middleware.py -q` -> 3 passed; `python -m pytest -q` -> 176 passed |
| 2026-05-10 | Codex | F5-T10 completado: rotacion stdlib para logs JSON opcionales (`AGARTHA_LOG_FILE_PATH`) y audit JSONL con limites `*_MAX_BYTES`/`*_BACKUP_COUNT`. | `py_compile`; `python -m pytest tests\test_log_rotation.py tests\test_structlog_logging.py tests\test_api_audit_logger.py -q` -> 5 passed; `python -m pytest -q` -> 173 passed |
| 2026-05-10 | Codex | F5-T09 completado: `structlog>=25.5.0`, configuracion JSON para stdlib/structlog, bootstrap en FastAPI y audit events estructurados sin perder JSONL. | `py_compile`; `python -m pytest tests\test_structlog_logging.py tests\test_api_audit_logger.py -q` -> 3 passed; `python -m pytest -q` -> 171 passed |
| 2026-05-10 | Codex | F5-T08 completado: `tools/run_migrations.py` aplica migraciones SQLite ordenadas con backup previo, `schema_migrations`, checksums, `BEGIN IMMEDIATE`, `--dry-run` y salida JSON. | `py_compile`; `python -m pytest tests\test_run_migrations.py -q` -> 6 passed; `python -m pytest -q` -> 169 passed |
| 2026-05-03 | Codex | Protocolo de coordinacion multi-agente creado | AGENTS.md + coordination.md |
| 2026-05-07 | Claude Code | Master roadmap generado con backlog multi-fase | `workflows/master_roadmap.md` |
| 2026-05-07 | Codex | F1-T11 completado: aiosqlite pool + retry + backup | `py_compile`; concurrent upsert OK |
| 2026-05-08 | Codex | F1-T01/F1-T02/F1-T03/F1-T04/F1-T05/F1-T06/F1-T07 completados | Ver entradas en Completado |
| 2026-05-08 | Codex | F1-T08 completado: `ForensicReport` ahora emite schema v2 con `confidence_score`, `damage_keywords` y `damage_types`; prompt ampliado con keywords de averia y normalizacion defensiva de JSON. | `python -m py_compile main.py tools\utils\forensic_agent.py tools\telegram_notifier.py`; asserts inline OK |
| 2026-05-08 | Codex | F1-T09 completado: `RepairCostEngine` usa tabla damage_type -> rango EUR, multiplicadores por marca y expone `repair_cost_range_eur` manteniendo `repair_cost_eur` para ROI. | `python -m py_compile tools\utils\forensic_agent.py main.py`; asserts inline OK |
| 2026-05-08 | Codex | F1-T10 completado: creado `tools/test_vllm.py` para benchmark vLLM/Ollama con throughput, p50/p95, tokens/s y snapshots VRAM via `nvidia-smi`. | `python -m py_compile tools\test_vllm.py`; mock server OK; smoke local sin endpoints disponibles |
| 2026-05-08 | Codex | F1-T12 completado: `listings` migra `condition_score`, `images_count`, `seller_type`, `location`, `price_history_json`; `upsert_listing` persiste los nuevos campos. | `python -m py_compile tools\utils\db.py`; migracion temporal OK |
| 2026-05-08 | Codex | F1-T13 completado: `upsert_listing` detecta duplicados cross-portal por brand/model/year, precio +/-5% y mileage +/-10%, persistidos en `listing_duplicates`. | `python -m py_compile tools\utils\db.py`; test temporal OK |
| 2026-05-08 | Codex | F1-T14 completado: `upsert_listing` acumula cambios en `price_history_json` por `(portal, ad_id)` y evita duplicar precios consecutivos iguales. | `python -m py_compile tools\utils\db.py`; test temporal OK |
| 2026-05-08 | Codex | F1-T15 completado: `request_handler.fetch` activa fallback ScrapingBee/BrightData con pool de sesiones bajo y senales de bloqueo. | `python -m py_compile tools\utils\request_handler.py`; mocks OK |
| 2026-05-08 | Codex | F1-T16 completado: tests unitarios de `ValuationEngine` cubren trimming, validaciones, ajuste por kilometraje, ROI y resumen. | `pytest` 12 passed; coverage 94% |
| 2026-05-08 | Codex | F1-T17 completado: tests unitarios de `ForensicAgent` cubren JSON extraction, schema v2, fallback seguro, RepairCostEngine y `analyze_batch`. | `pytest` 12 passed; coverage 95% |
| 2026-05-08 | Codex | F1-T18 completado: tests de parsers/helpers cubren `parse_price`, `parse_mileage`, `parse_year`, `make_slug`, `calculate_max_bid`; corregido `parse_price` para no tomar cuotas mensuales como precio. | `pytest` 22 passed |
| 2026-05-08 | Codex | F2-T01 completado: creado paquete `tools/api/` con `app.py` y subpaquetes `routers`, `schemas`, `models`, `dependencies`, `middleware`. | `py_compile`; import app OK |
| 2026-05-08 | Codex | F2-T02 completado: `ListingOut` expone campos de listing y parsea `price_history_json` como `price_history` tipado. | `py_compile`; inline validation OK |
| 2026-05-08 | Codex | F2-T03 completado: `ListingFilter` define filtros de listing y valida rangos year/price. | `py_compile`; inline validation OK |
| 2026-05-08 | Codex | F2-T04 completado: schemas de mercado para stats, metricas por marca, histograma ROI y tendencia de precios. | `py_compile`; inline validation OK |
| 2026-05-08 | Codex | F2-T05 completado: schemas auth `LoginIn`, `TokenOut`, `APIKeyCreate`, `APIKeyOut`. | `py_compile`; inline validation OK |
| 2026-05-08 | Codex | F2-T06 completado: router `/listings` incluido en `tools.api.app`, con listado filtrable basico y detalle por id. | `py_compile`; TestClient temporal OK |
| 2026-05-08 | Codex | F2-T07 completado: router `/market` devuelve stats globales, metricas por marca, histograma ROI y tendencias desde `price_history_json`. | `py_compile`; TestClient temporal OK |
| 2026-05-08 | Codex | F2-T08 completado: router `/dealers` con alta, listado, perfil propio via header y actualizacion basica, respaldado por SQLite async. | `py_compile`; TestClient temporal OK |
| 2026-05-08 | Codex | F2-T09 completado: router `/auth` con login, refresh, logout no-op y rotacion de API key; integra PBKDF2/HMAC stdlib y SQLite async. | `py_compile`; TestClient temporal OK |
| 2026-05-08 | Codex | F2-T11/F2-T13 completados: `/listings` acepta filtros parametrizados y devuelve respuesta paginada B2B. | `py_compile`; TestClient temporal OK |
| 2026-05-08 | Codex | F2-T14 completado: middleware de rate limit en memoria por API key/IP con respuesta 429 y headers `Retry-After`/`X-RateLimit-*`. | `py_compile`; TestClient OK |
| 2026-05-08 | Codex | F2-T19 completado: `CORSMiddleware` configurado en `tools.api.app`, con origen por defecto dev y override `AGARTHA_CORS_ORIGINS`. | TestClient OPTIONS OK |
| 2026-05-08 | Codex | F2-T10 completado: router `/admin` con `GET /admin/stats`, `PATCH /admin/dealers/{dealer_id}/plan` y `GET /admin/health`, protegido por dealer activo con plan `admin` via Bearer o `X-API-Key`. | `py_compile`; TestClient temporal; OpenAPI admin routes OK |
| 2026-05-08 | Codex | F2-T12 completado: `q` en `/listings` usa SQLite FTS5 sobre `listings_fts` con ranking `bm25`; `init_db` reconstruye indice y `upsert_listing` lo sincroniza; fallback LIKE si no existe FTS. | `py_compile`; TestClient temporal FTS/fallback; OpenAPI listings OK |
| 2026-05-08 | Claude Code | F3-T01/F3-T02/F3-T03 y F5-T20 completados | Ver workflows correspondientes |
| 2026-05-08 | Claude Code | F1-T20 completado: `workflows/ai_analysis_setup.md` — ForensicAgent (Ollama deepseek-r1:8b), RepairCostEngine (tabla brand/damage_type), schema v2, vLLM benchmark, integración pipeline, troubleshooting y guía de extensión. | `workflows/ai_analysis_setup.md` creado |
| 2026-05-08 | Claude Code | F2-T24 completado: OpenAPI customization — `app.py` con metadata, BearerAuth + ApiKeyAuth schemes, openapi_tags; 4 routers con summary/description en todos los endpoints; `workflows/api_contract.md` con referencia completa. | `py_compile` OK; `app.openapi()` genera schema con 19 rutas correctamente |
| 2026-05-08 | Codex | RECOVERY: `coordination.md` restaurado tras zero-byte write por ENOSPC; liberado espacio borrando cache `_npx` y un HTML temporal `.tmp` | `Get-Item .agents/coordination.md`; `npx skills find` OK tras limpieza |
| 2026-05-08 | Codex | F3-T04/F3-T05 completados: creado `frontend/` con Vite React TS, Tailwind 3, shadcn/ui base, dashboard shell, Axios client, auth refresh interceptor, tipos API, TanStack Query hooks y store Zustand para filtros. | `npm run build`; `npm run lint`; `npm audit --audit-level=moderate` (2 moderadas Vite 5/esbuild); Vite background responde 200 en `http://127.0.0.1:5173/` |
| 2026-05-08 | Codex | F3-T06 completado: login page, route guard, auth store, token-change event, logout button y redirect post-login. | `npm run build`; `npm run lint`; smoke HTTP 200 en `/` y `/login` |
| 2026-05-08 | Codex | F3-T07 completado: tabla de listings extraida a componente con TanStack Table, virtual scroll, paginacion API y helpers de formato. | `npm run build`; `npm run lint`; smoke HTTP 200 en `/login` |
| 2026-05-08 | Codex | F3-T08 completado: panel de filtros dedicado e integrado en dashboard; store limpia valores vacios y conserva paginacion API. | `npm run build`; `npm run lint`; smoke HTTP 200 en `/login` |
| 2026-05-08 | Codex | F3-T09 completado: grafica ROI por marca con Recharts e integracion en dashboard; split conservador del chunk charts. | `npm run build`; `npm run lint`; smoke HTTP 200 en `/login` |
| 2026-05-08 | Codex | F3-T10..F3-T22 completados: PriceTrend, ListingDrawer, KPIWidgets, Dashboard final, Market page, AlertCenter, SavedSearches, ExportButton, responsive layout, dark mode, loading states, ErrorBoundary y Playwright E2E. | `npm run build`; `npm run lint`; `npx playwright install chromium`; `npm run test:e2e` -> 1 passed; `/login` HTTP 200 |
| 2026-05-09 | Codex | F2-T15 completado: middleware audit logger JSONL con `request_id`, dealer derivado del Bearer token o `X-Dealer-ID`, endpoint, status, latencia, IP y prefijo seguro de API key; registrado en `tools.api.app`. | `py_compile`; `pytest tests\test_api_audit_logger.py`; `pytest -q` -> 47 passed |
| 2026-05-09 | Codex | F2-T16 completado: dependencia `get_current_dealer()` centralizada en `tools/api/dependencies/auth.py`; valida Bearer access token, `X-API-Key` o `X-Dealer-ID`, con wrappers active/admin usados por `/dealers/me`, `/auth/api-key` y `/admin/*`. | `py_compile`; `pytest tests\test_api_dependencies.py`; `pytest -q` -> 52 passed |
| 2026-05-09 | Codex | F2-T17 completado: dependencia `get_db()` en `tools/api/dependencies/db.py`; `listings`, `market` y `admin` usan conexion SQLite inyectada y sobreescribible en tests. | `py_compile`; `pytest tests\test_api_db_dependency.py`; `pytest -q` -> 54 passed |
| 2026-05-09 | Codex | F2-T18 completado: handlers RFC 7807 registrados en FastAPI para HTTPException, validacion 422 y errores inesperados, con `application/problem+json`, `instance` y `request_id` cuando existe. | `py_compile`; `pytest tests\test_api_error_handlers.py`; `pytest -q` -> 57 passed |
| 2026-05-09 | Codex | F2-T20 completado: router publico `/health` y `/ready`; liveness expone version/uptime y readiness valida ping SQLite via `get_db`, con 503 si la DB falla. | `py_compile`; `pytest tests\test_api_health.py`; `pytest -q` -> 60 passed |
| 2026-05-09 | Codex | F2-T21 completado: tests de integracion `/listings` cubren filtros/paginacion, busqueda `q` con fallback LIKE, detalle con historial de precio, tabla ausente y 404 RFC 7807. | `py_compile`; `pytest tests\test_api_listings.py`; `pytest -q` -> 65 passed |
| 2026-05-09 | Codex | F2-T22 completado: tests de integracion `/market` cubren KPIs globales, metricas por marca, histograma ROI, tendencias desde `price_history_json` y respuestas vacias si falta la tabla. | `py_compile`; `pytest tests\test_api_market.py`; `pytest -q` -> 70 passed |
| 2026-05-09 | Codex | F2-T23 completado: tests de integracion `/auth` cubren login correcto/errores, refresh valido e invalido, dealer inactivo, logout y rotacion de API key con invalidacion de la anterior. | `py_compile`; `pytest tests\test_api_auth.py`; `pytest -q` -> 76 passed |
| 2026-05-09 | Codex | F4-T01 completado: versionada `002_dealers.sql` con tabla dealers e indices para email, API key, plan/active y Stripe; `ensure_dealers_schema()` ejecuta la migracion y completa columnas legacy. | `py_compile`; `pytest tests\test_api_dealer_schema.py`; `pytest -q` -> 78 passed |
| 2026-05-09 | Codex | F4-T02 completado: versionada `003_api_usage.sql` con contador diario por dealer/endpoint, FK cascade a dealers, unicidad para upsert e indices por dealer/fecha y fecha/endpoint. | `py_compile`; `pytest tests\test_api_usage_schema.py`; `pytest -q` -> 80 passed |
| 2026-05-09 | Codex | F4-T03 completado: versionada `004_saved_searches.sql` con busquedas por dealer, `filter_json`, unicidad por nombre dentro del dealer, FK cascade e indice por fecha de creacion. | `py_compile`; `pytest tests\test_api_saved_searches_schema.py`; `pytest -q` -> 83 passed |
| 2026-05-09 | Codex | F4-T04 completado: servicio `auth_service` con bcrypt para passwords, JWT HS256 con `jti`, access/refresh tokens y blacklist SQLite idempotente para revocacion. | `pip install bcrypt PyJWT`; `py_compile`; `pytest tests\test_auth_service.py`; `pytest -q` -> 89 passed |
| 2026-05-09 | Codex | F4-T05 completado: `DealerService` centraliza persistencia de dealers, busqueda por email/id, listado, updates de perfil/plan/activo, Stripe customer id y contador `calls_today`. | `py_compile`; `pytest tests\test_dealer_service.py`; `pytest -q` -> 94 passed |
| 2026-05-09 | Codex | F4-T06 completado: `/auth/login` y `/auth/refresh` emiten JWT HS256 del servicio F4; dependencia Bearer valida blacklist; logout revoca token; alta de dealer ya guarda bcrypt con fallback PBKDF2 legacy. | `py_compile`; `pytest tests\test_api_auth.py tests\test_api_dependencies.py tests\test_auth_service.py`; `pytest -q` -> 94 passed |
| 2026-05-09 | Codex | F4-T07 completado: servicio de API keys con generacion `agrt_` UUID+secreto, hash SHA-256, validacion constante, rotacion por dealer activo e integracion en `X-API-Key` y `/auth/api-key`. | `py_compile`; `pytest tests\test_api_key_service.py tests\test_api_auth.py tests\test_api_dependencies.py`; `pytest -q` -> 98 passed |
| 2026-05-09 | Codex | F4-T08 completado: `tools/api/models/plan.py` centraliza enum `PlanName`, limites diarios y flags de alertas; schemas/admin/dealer service usan el modelo compartido. | `py_compile`; `pytest tests\test_plan_model.py`; `pytest -q` -> 103 passed |
| 2026-05-09 | Codex | F4-T09 completado: `PlanGuardMiddleware` aplica cuota diaria por plan a requests autenticadas, incrementa `calls_today`, expone headers `X-Plan-*` y devuelve 402 problem+json al superar limite. | `py_compile`; `pytest tests\test_plan_guard_middleware.py`; `pytest -q` -> 107 passed |
| 2026-05-09 | Codex | F4-T10 completado: dependencia oficial `stripe>=14.4.0` y helper `stripe_client` para cargar `STRIPE_*`, configurar `stripe.api_key`, retries y app info sin llamadas externas. | `pip install stripe>=14.4.0`; `py_compile`; `pytest tests\test_stripe_client.py`; `pytest -q` -> 111 passed |
| 2026-05-09 | Codex | F4-T12 completado: `StripeBillingService` resuelve price IDs Basic/Premium, crea y persiste customers, crea checkout sessions, billing portal sessions y delega verificacion de webhooks al SDK Stripe. | `py_compile`; `python -m pytest tests\test_stripe_service.py -q` -> 9 passed; `python -m pytest -q` -> 127 passed |
| 2026-05-10 | Codex | F4-T13 completado: router `/payments/checkout` protegido por dealer activo, schemas de checkout, registro en FastAPI/OpenAPI y tests con billing service fake. | `py_compile`; `python -m pytest tests\test_payments_checkout.py -q` -> 5 passed; `python -m pytest -q` -> 132 passed |
| 2026-05-10 | Codex | F4-T14 completado: router `/payments/portal` protegido por dealer activo, schemas de billing portal y tests con billing service fake para exito/auth/errores Stripe. | `py_compile`; `python -m pytest tests\test_payments_portal.py -q` -> 5 passed; `python -m pytest -q` -> 137 passed |
| 2026-05-10 | Codex | F4-T15 completado: router publico `/webhooks/stripe` lee payload crudo, valida `Stripe-Signature` via `StripeBillingService` y responde con id/tipo de evento recibido. | `py_compile`; `python -m pytest tests\test_stripe_webhooks_router.py -q` -> 4 passed; `python -m pytest -q` -> 141 passed |
| 2026-05-10 | Codex | F4-T16 completado: webhook `checkout.session.completed` activa el plan indicado en metadata y persiste `stripe_customer_id`, con fallback a `client_reference_id`. | `py_compile`; `python -m pytest tests\test_stripe_webhook_checkout_completed.py tests\test_stripe_webhooks_router.py -q` -> 8 passed; `python -m pytest -q` -> 145 passed |
| 2026-05-10 | Codex | F4-T17 completado: webhook `invoice.payment_failed` busca dealer por `stripe_customer_id` y envia email transaccional de pago fallido sin suspender la cuenta. | `py_compile`; `python -m pytest tests\test_dealer_service.py tests\test_stripe_webhook_payment_failed.py -q` -> 8 passed; `python -m pytest -q` -> 148 passed |
| 2026-05-10 | Codex | F4-T18 completado: webhook `customer.subscription.deleted` localiza dealer por customer Stripe y lo baja a plan `trial` conservando el customer id. | `py_compile`; `python -m pytest tests\test_stripe_webhook_subscription_deleted.py -q` -> 3 passed; `python -m pytest -q` -> 151 passed |
| 2026-05-09 | Codex | F4-T19 completado: `email_service` usa Resend async para welcome, payment_failed y plan_upgrade, con settings `RESEND_API_KEY`, remitente y URL publica desde env. | `pip install resend[async]`; `py_compile`; `pytest tests\test_email_service.py`; `pytest -q` -> 115 passed |
| 2026-05-10 | Codex | F4-T20 completado: `/auth/register` crea dealer, provisiona customer Stripe, envia welcome si email configurado y devuelve access/refresh token + API key inicial. | `py_compile`; `python -m pytest tests\test_auth_register.py -q` -> 3 passed; `python -m pytest -q` -> 154 passed |
| 2026-05-10 | Codex | F4-T21 completado: admin controls para activar/suspender dealers, resetear `calls_today` y provisionar/reutilizar Stripe customer desde panel admin. | `py_compile`; `python -m pytest tests\test_admin_controls.py -q` -> 4 passed; `python -m pytest -q` -> 158 passed |
| 2026-05-10 | Codex | F4-T22 completado: test integrado de webhooks Stripe valida ciclo checkout -> invoice failed -> subscription deleted con efectos en dealer y email mockeado. | `py_compile`; `python -m pytest tests\test_stripe_webhooks_integration.py -q` -> 1 passed; `python -m pytest -q` -> 159 passed |
| 2026-05-10 | Codex | F5-T01 completado: creado `Dockerfile.pipeline` para radar/pipeline con Python 3.12-slim, requirements, Chromium Playwright, `tools/`, `main.py` y entrypoint `python main.py`. | `docker --version` OK; build no ejecutado porque Docker daemon/Desktop no esta arrancado |
| 2026-05-10 | Codex | F5-T02 completado: creado `Dockerfile.api` para FastAPI con Python 3.12-slim, requirements, `tools/`, uvicorn en puerto 8000 y healthcheck `/health`. | `py_compile`; build no ejecutado porque Docker daemon/Desktop no esta arrancado |
| 2026-05-10 | Codex | F5-T03 completado: creado `Dockerfile.frontend` multi-stage Node 22 -> nginx alpine, build Vite con `VITE_API_BASE_URL=/api`, fallback SPA y healthcheck. | `npm run build` OK; build Docker no ejecutado porque Docker daemon/Desktop no esta arrancado |
| 2026-05-10 | Codex | F5-T04 completado: creado `docker-compose.yml` con servicios pipeline, api, frontend y nginx; volumes para datos/logs/certbot; redes internal/public. | `docker compose config` OK; salida no registrada por contener expansion de `.env` |
| 2026-05-10 | Codex | F5-T05 completado: creado `nginx.conf` reverse proxy con `/api/` hacia FastAPI, frontend SPA y ruta ACME challenge para Certbot. | `docker compose config --no-interpolate` OK; test nginx bloqueado por Docker daemon apagado |
| 2026-05-10 | Codex | F5-T07 completado: `tools/backup_db.py` crea backup SQLite consistente, poda backups antiguos, sube opcionalmente por rclone y emite JSON/alerta en fallo. | `py_compile`; `python -m pytest tests\test_backup_db.py -q` -> 4 passed; `python -m pytest -q` -> 163 passed |
| 2026-05-09 | Codex | F4-T23 completado: tests de hardening auth verifican bcrypt en altas, JWT con `jti`, blacklist por logout y API keys generadas/validadas por el servicio F4. | `py_compile`; `pytest tests\test_auth_hardening.py`; `pytest -q` -> 118 passed |
