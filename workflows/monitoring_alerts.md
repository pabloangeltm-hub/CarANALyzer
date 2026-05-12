# SOP — Monitoring & Alerts

> Cubre Prometheus + Grafana, rotación de logs estructurados (structlog) y alertas Telegram del pipeline.

---

## Métricas Prometheus

### Endpoint

```
GET /metrics
```

Expuesto sin autenticación (configurable vía Nginx si se desea proteger). Implementado en [`tools/api/routers/metrics.py`](../tools/api/routers/metrics.py) y [`tools/api/metrics.py`](../tools/api/metrics.py).

### Métricas disponibles

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `agartha_api_requests_total` | Counter | `method`, `path`, `status_code` | Total de requests HTTP |
| `agartha_api_request_duration_seconds` | Histogram | `method`, `path` | Latencia por request |
| `agartha_api_requests_in_progress` | Gauge | `method` | Requests activos simultáneamente |

Histogram buckets: 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s.

### Activar / desactivar

```env
# .env
AGARTHA_PROMETHEUS_ENABLED=true   # defecto: true
```

El middleware [`PrometheusMetricsMiddleware`](../tools/api/middleware/prometheus_metrics.py) omite la instrumentación de `/metrics` para evitar auto-referencia.

---

## Configurar Prometheus

### docker-compose con Prometheus (añadir al compose)

```yaml
# Añadir a docker-compose.yml como servicio adicional
  prometheus:
    image: prom/prometheus:v2.51.0
    volumes:
      - ./deploy/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.retention.time=30d
    expose:
      - "9090"
    networks:
      - internal
    restart: unless-stopped

volumes:
  prometheus_data:
```

### prometheus.yml

```yaml
# deploy/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: agartha-api
    static_configs:
      - targets: ["api:8000"]
    metrics_path: /metrics
```

Scrape cada 15 s desde la red interna Docker (sin exponer al exterior).

---

## Grafana Dashboard

Dashboard preconfigurado en [`deploy/grafana/agartha_dashboard.json`](../deploy/grafana/agartha_dashboard.json).

### Paneles incluidos

| Panel | Tipo | Descripción |
|-------|------|-------------|
| Error Rate (5xx) | Stat | Tasa de errores — umbral rojo >5% |
| p95 Latency | Stat | Latencia percentil 95 — umbral rojo >1s |
| Request Rate | Stat | req/s total |
| In-Flight Requests | Stat | Requests simultáneos |
| Request Rate by Status Class | Time series | 2xx / 4xx / 5xx |
| Request Latency Percentiles | Time series | p50, p95, p99 |
| Request Rate by Path | Time series | Desglose por endpoint |
| p95 Latency by Path | Time series | Latencia por endpoint |
| Endpoint Summary Table | Table | Vista tabular con req/s, errors/s, p95 |
| In-Flight by Method | Time series | GET/POST en paralelo |
| Request Distribution by Status Code | Bar chart | Distribución de códigos HTTP |

### Importar en Grafana

1. Ve a **Dashboards → Import**.
2. Sube `deploy/grafana/agartha_dashboard.json` o pega el JSON.
3. Selecciona la datasource Prometheus configurada.
4. Haz clic en **Import**.

### Configurar Grafana con Docker Compose (añadir al compose)

```yaml
  grafana:
    image: grafana/grafana-oss:10.4.0
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-changeme}
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./deploy/grafana/agartha_dashboard.json:/etc/grafana/provisioning/dashboards/agartha.json:ro
    expose:
      - "3000"
    networks:
      - internal
    restart: unless-stopped

volumes:
  grafana_data:
```

Expón Grafana detrás de Nginx en `/grafana/` si necesitas acceso externo (no recomendado en producción sin autenticación adicional).

---

## Alertas en Grafana

### Reglas de alerta recomendadas

| Condición | Umbral | Canal | Nota |
|-----------|--------|-------|------|
| Error rate 5xx | > 5% durante 5 min | Telegram | Servicios caídos |
| p95 latency | > 2s durante 5 min | Telegram | Degradación rendimiento |
| In-flight requests | > 50 durante 2 min | Telegram | Posible saturación |
| API down (no scrape) | Sin datos > 2 min | Telegram | Contenedor caído |

### Configurar notificaciones Telegram en Grafana

1. **Grafana → Alerting → Contact points → New contact point**
2. Tipo: **Telegram**
3. Bot token: el mismo `TELEGRAM_BOT_TOKEN` del `.env`
4. Chat ID: el mismo `TELEGRAM_CHAT_ID`
5. Guardar y vincular a las reglas de alerta

---

## Logs estructurados (structlog)

### Formato

Todos los logs de la API se emiten en JSON vía structlog. Ejemplo de línea:

```json
{
  "timestamp": "2026-05-10T12:00:00.123456Z",
  "level": "info",
  "logger": "agartha.api",
  "event": "request_completed",
  "method": "GET",
  "path": "/listings",
  "status_code": 200,
  "latency_ms": 42.3,
  "dealer_id": 7,
  "request_id": "abc123"
}
```

### Variables de entorno

```env
AGARTHA_LOG_LEVEL=INFO            # DEBUG en desarrollo
AGARTHA_LOG_FILE_PATH=/opt/agartha/logs/app.log
AGARTHA_AUDIT_LOG_PATH=/opt/agartha/logs/audit.log
```

### Audit log

Cada request autenticado genera una línea en `audit.log` con:
- `request_id`, `dealer_id`, `method`, `path`, `status_code`, `latency_ms`

---

## Rotación de logs

Gestionada por `logrotate` en el VPS. Configurar en `/etc/logrotate.d/agartha`:

```
/opt/agartha/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        docker compose -f /opt/agartha/docker-compose.yml \
          exec api kill -USR1 1 2>/dev/null || true
    endscript
}
```

Verificar:
```bash
logrotate --debug /etc/logrotate.d/agartha
```

---

## Alertas del pipeline (Telegram)

El pipeline de scraping envía alertas directas vía `tools/utils/telegram_notifier.py`:

| Evento | Mensaje Telegram |
|--------|-----------------|
| Nueva oportunidad (ROI > umbral) | 🚗 `[BRAND MODEL YEAR]` — ROI X% — €PRICE |
| Session pool agotado | ⚠️ Session pool crítico: N sesiones restantes |
| IP bloqueada permanentemente | 🔴 IP block detectado — cooldowns: N |
| Scrape completado | ✅ Scrape N páginas en T minutos |

Configurar en `.env`:
```env
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_CHAT_ID=<chat-id>
```

---

## Health checks

### API health

```bash
curl https://tu-dominio.com/api/health
# {"status": "ok", "version": "X.Y.Z", "uptime_seconds": 3600}

curl https://tu-dominio.com/api/ready
# {"status": "ok", "db": "ok"}
```

### Docker Compose health

```bash
docker compose ps
# NAME                STATUS
# agartha-api-1       Up X minutes (healthy)
# agartha-nginx-1     Up X minutes
# agartha-frontend-1  Up X minutes (healthy)
# agartha-pipeline-1  Up X minutes
```

Healthcheck de la API: `GET http://127.0.0.1:8000/health` cada 30s, timeout 5s, 3 reintentos.

---

## Runbook rápido

| Síntoma | Diagnóstico | Acción |
|---------|-------------|--------|
| Error rate > 10% | `docker compose logs api` | Verificar traceback; rollback si es code |
| p95 > 2s en `/listings` | `/api/metrics` | Revisar query SQLite; añadir índice si falta |
| Contenedor API reinicia en bucle | `docker compose ps` | `docker compose logs api --tail 50` |
| Telegram sin alertas de scrape | `docker compose logs pipeline` | Verificar `TELEGRAM_BOT_TOKEN` y sesiones |
| Disco lleno | `df -h` | Limpiar `.tmp/` y logs antiguos; `docker system prune` |
| Certbot expirado | `curl -I https://dominio.com` | `docker compose --profile certbot run --rm certbot renew` |
