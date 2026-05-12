# SOP — DevOps & Despliegue

> Cubre el stack Docker, el aprovisionamiento del VPS, SSL, despliegue continuo y procedimientos de rollback.

---

## Arquitectura de despliegue

```
Internet
    │
    ▼
[Nginx :80/:443 — rate limiting + SSL termination]
    ├── /api/auth/* ──► [FastAPI :8000]   (rate: 2r/s burst 10)
    ├── /api/*      ──► [FastAPI :8000]   (rate: 10r/s burst 30)
    └── /*          ──► [Frontend :80]

[FastAPI container]
    ├── SQLite WAL (.tmp/agartha.db via volume agartha_data)
    └── Audit log (volume agartha_logs)

[Pipeline container]
    └── main.py radar 24/7 → SQLite (volume compartido agartha_data)

[Certbot container] (profile: certbot — solo para renovaciones)
```

Definición completa: [`docker-compose.yml`](../docker-compose.yml)

---

## Requisitos del VPS

| Recurso | Mínimo recomendado |
|---------|-------------------|
| OS | Ubuntu 22.04 LTS o 24.04 LTS |
| CPU | 2 vCPU |
| RAM | 4 GB (pipeline + Ollama son intensivos) |
| Disco | 40 GB SSD |
| GPU | RTX 3060 (para Ollama deepseek-r1:8b) |
| Puertos abiertos | 22, 80, 443 |

---

## Primer despliegue (VPS limpio)

### 1. Aprovisionar el VPS

```bash
# Desde tu máquina local — requiere acceso root al VPS
AGARTHA_REPO_URL=https://github.com/tu-usuario/agartha \
AGARTHA_BRANCH=main \
  ssh root@<ip-vps> 'bash -s' < setup_vps.sh
```

El script [`setup_vps.sh`](../setup_vps.sh) realiza:
1. Instala paquetes base (git, curl, gnupg, ufw)
2. Instala Docker Engine + Compose plugin (desde repositorio oficial)
3. Clona el repo en `/opt/agartha` (si `AGARTHA_REPO_URL` está definido)
4. Instala la unidad systemd `agartha.service`
5. Configura UFW (22, 80, 443)
6. Construye imágenes Docker y arranca el servicio (si `.env` existe)

### 2. Configurar secretos en el VPS

```bash
ssh root@<ip-vps>
cp /opt/agartha/.env.production.example /opt/agartha/.env
nano /opt/agartha/.env   # rellenar todos los valores
```

Ver [`workflows/secrets_management.md`](secrets_management.md) para gestión con sops+age.

### 3. Ejecutar migraciones

```bash
ssh root@<ip-vps>
cd /opt/agartha
docker compose run --rm api \
  python tools/run_migrations.py --db-path /app/.tmp/agartha.db
```

### 4. Obtener certificado SSL

```bash
# Desde el VPS — el dominio debe apuntar a la IP del VPS
DOMAIN=tu-dominio.com EMAIL=tu@email.com \
  bash tools/setup_letsencrypt.sh
```

El script:
1. Inicia Nginx en modo HTTP para el challenge ACME
2. Solicita el certificado a Let's Encrypt
3. Sustituye `nginx.conf` por la plantilla SSL en `deploy/nginx/nginx.ssl.conf.template`
4. Recarga Nginx con SSL activo

### 5. Iniciar el servicio

```bash
systemctl start agartha.service
systemctl status agartha.service

# Verificar
curl https://tu-dominio.com/api/health
```

---

## Estructura de Docker Compose

| Servicio | Imagen | Puerto interno | Descripción |
|----------|--------|----------------|-------------|
| `api` | `agartha-api:latest` | 8000 | FastAPI + uvicorn |
| `pipeline` | `agartha-pipeline:latest` | — | Radar scraping 24/7 |
| `frontend` | `agartha-frontend:latest` | 80 | SPA React estática |
| `nginx` | `nginx:1.27-alpine` | 80, 443 | Reverse proxy + SSL |
| `certbot` | `certbot/certbot:latest` | — | Solo perfil certbot |

Volúmenes compartidos:
- `agartha_data` → `/app/.tmp` (api + pipeline) — SQLite WAL
- `agartha_logs` → `/app/logs` (api) + `/var/log/nginx` (nginx)
- `certbot_www` + `certbot_conf` → Let's Encrypt

---

## Despliegue continuo (CI/CD)

### CI (`.github/workflows/ci.yml`)

Se dispara en `push main` y pull requests:
1. **Python**: `pytest -q` (todos los tests)
2. **Frontend**: `npm ci`, `npm run lint`, `npm run build`, `playwright test`
3. **Compose**: `docker compose config --no-interpolate`

### CD (`.github/workflows/cd.yml`)

Se dispara cuando CI pasa en `main`:
1. Abre SSH al VPS usando secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
2. `git fetch origin main && git reset --hard origin/main`
3. `docker compose build`
4. `docker compose run --rm api python tools/run_migrations.py`
5. `systemctl restart agartha.service`

#### Configurar secrets en GitHub

En `Settings → Secrets and variables → Actions → Repository secrets`:

| Secret | Valor |
|--------|-------|
| `VPS_HOST` | IP o hostname del VPS |
| `VPS_PORT` | Puerto SSH (defecto: 22) |
| `VPS_USER` | Usuario SSH (defecto: root) |
| `VPS_SSH_KEY` | Clave privada SSH (RSA/Ed25519) |

```bash
# Generar par de claves dedicado para CD
ssh-keygen -t ed25519 -C "agartha-cd" -f ~/.ssh/agartha_cd
cat ~/.ssh/agartha_cd.pub >> /root/.ssh/authorized_keys  # en el VPS
cat ~/.ssh/agartha_cd     # pegar como VPS_SSH_KEY en GitHub
```

---

## Renovación de certificado SSL

Let's Encrypt expira cada 90 días. Renovación automática con el timer systemd:

```bash
# Ver timers instalados por setup_letsencrypt.sh
systemctl list-timers | grep certbot
systemctl status agartha-certbot-renew.timer

# Renovar manualmente si es urgente
docker compose --profile certbot run --rm certbot renew
docker compose exec nginx nginx -s reload
```

---

## Comandos operacionales frecuentes

```bash
# Estado del stack
cd /opt/agartha
docker compose ps

# Logs en tiempo real
docker compose logs -f api
docker compose logs -f pipeline

# Reiniciar solo la API (sin downtime en nginx/frontend)
docker compose restart api

# Rebuildir y reiniciar solo la API
docker compose build api && docker compose up -d api

# Reiniciar todo el stack
systemctl restart agartha.service

# Migraciones en producción (con backup automático)
docker compose run --rm api python tools/run_migrations.py --db-path /app/.tmp/agartha.db

# Backup manual de la DB
docker compose run --rm api python tools/backup_db.py

# Shell en el contenedor API
docker compose exec api bash
```

---

## Rollback

### Rollback de código

```bash
cd /opt/agartha

# Ver commits recientes
git log --oneline -10

# Volver a un commit anterior
git reset --hard <sha>

# Reconstruir y reiniciar
docker compose build
systemctl restart agartha.service
```

### Rollback de base de datos

```bash
# Los backups se guardan en .tmp/backups/
ls /opt/agartha/.tmp/backups/

# Restaurar backup
cp /opt/agartha/.tmp/backups/agartha_20260510_120000.db \
   /opt/agartha/.tmp/agartha.db

# Reiniciar API para que coja el fichero nuevo
docker compose restart api
```

---

## Checklist de despliegue en producción

- [ ] `.env` completo en `/opt/agartha/.env` con claves live
- [ ] DNS del dominio apuntando a la IP del VPS
- [ ] Certificado SSL válido (`curl https://tu-dominio.com/api/health`)
- [ ] Productos Stripe creados en modo live (`setup_stripe_products.py`)
- [ ] Webhook Stripe configurado con URL producción
- [ ] Tests CI pasando en verde
- [ ] `docker compose ps` muestra todos los servicios healthy
- [ ] `GET /api/health` responde `{"status": "ok"}`
- [ ] `GET /api/metrics` accesible (o protegido por Nginx si se desea)
- [ ] Secrets en GitHub Actions configurados para CD automático
- [ ] Timer certbot activo para renovación automática
