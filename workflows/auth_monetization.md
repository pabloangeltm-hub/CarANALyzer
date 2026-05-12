# SOP — Auth & Monetización

> Fase 4 completada. Este documento describe el sistema de autenticación multi-tenant, ciclo de vida de las API keys, límites por plan y flujo completo de registro.

---

## Arquitectura

```
POST /auth/register
    │── create_dealer() ──► SQLite dealers
    │── ensure_customer() ──► Stripe Customer
    │── send_welcome_email() ──► Resend
    └── devuelve JWT + API key

Bearer token / X-API-Key / X-Dealer-ID
    │
    ▼
get_current_active_dealer() [dependencies/auth.py]
    │
    ▼
PlanGuardMiddleware [middleware/plan_guard.py]
    │  si calls_today >= daily_limit → 402
    └── incrementa calls_today
```

---

## Planes de suscripción

| Plan | `daily_limit` | Alertas | Stripe | Uso |
|------|-------------|---------|--------|-----|
| `trial` | 50 req/día | No | No | Cuenta recién creada |
| `basic` | 500 req/día | Sí | €79/mes | `STRIPE_PRICE_BASIC` |
| `premium` | Ilimitado | Sí | €199/mes | `STRIPE_PRICE_PREMIUM` |
| `admin` | Ilimitado | Sí | No | Uso interno |

Modelo en [`tools/api/models/plan.py`](../tools/api/models/plan.py).

---

## Autenticación

### JWT HS256

- **Access token**: 1 hora · header `Authorization: Bearer <token>`
- **Refresh token**: 7 días · endpoint `POST /auth/refresh`
- **Secreto**: variable `JWT_SECRET` (≥ 32 bytes aleatorios)
- **Blacklist**: tokens revocados se almacenan en SQLite hasta expiración
- Implementado en [`tools/api/services/auth_service.py`](../tools/api/services/auth_service.py)

```bash
# Generar JWT_SECRET
python -c "import secrets; print(secrets.token_hex(32))"
```

### API Keys

- Formato visible: `agrt_<uuid4_sin_guiones>` (prefijo fijo)
- Almacenamiento: SHA-256 del token completo en columna `api_key_hash`
- Header: `X-API-Key: agrt_...`
- Rotación: `POST /auth/api-key` invalida la anterior y devuelve la nueva
- Implementado en [`tools/api/services/api_key_service.py`](../tools/api/services/api_key_service.py)

### Contraseñas

- Hashing: **bcrypt** con cost factor por defecto (12)
- Nunca se almacena ni loguea la contraseña en claro

### Métodos de autenticación soportados simultáneamente

| Método | Header / campo | Prioridad |
|--------|---------------|-----------|
| Bearer JWT | `Authorization: Bearer <token>` | 1 |
| API Key | `X-API-Key: agrt_...` | 2 |
| Dealer ID legacy | `X-Dealer-ID: <id>` | 3 (solo dev) |

---

## Flujo de registro

```
Cliente                     API                      Stripe           Resend
  │                          │                          │                │
  ├── POST /auth/register ──►│                          │                │
  │   {name, email, password}│                          │                │
  │                          ├── bcrypt hash pwd        │                │
  │                          ├── INSERT dealers ────────────────────────►│
  │                          │   plan=trial             │                │
  │                          ├── Customer.create ──────►│                │
  │                          │                          │◄── customer_id │
  │                          ├── UPDATE stripe_cust_id  │                │
  │                          ├── send_welcome_email ────────────────────►│
  │                          ├── create JWT (access+refresh)             │
  │                          ├── generate API key                        │
  │◄── 201 {tokens, api_key}─┤                          │                │
```

**Endpoint**: `POST /auth/register`  
**Body**: `{"name": "...", "email": "...", "password": "..."}` (mínimo 8 caracteres)  
**Response 201**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "api_key": "agrt_...",
  "dealer": { "id": 1, "name": "...", "email": "...", "plan": "trial" }
}
```

Si `RESEND_API_KEY` o `STRIPE_SECRET_KEY` no están configurados, el registro continúa sin email ni customer Stripe (gracias a `except EmailConfigurationError` y `except StripeConfigurationError`).

---

## Flujo de login

```
POST /auth/login   {"email": "...", "password": "..."}
    │
    ├── verify_password() ── bcrypt check
    └── create_jwt(access + refresh)
    └── Response 200: {access_token, refresh_token, token_type}
```

**Refresh**: `POST /auth/refresh` · header `Authorization: Bearer <refresh_token>`  
**Logout**: `POST /auth/logout` · blacklist el token actual

---

## Plan Guard Middleware

Archivo: [`tools/api/middleware/plan_guard.py`](../tools/api/middleware/plan_guard.py)

- Se ejecuta **antes** de los routers en todas las rutas autenticadas
- Si `dealer.calls_today >= plan.daily_limit` → respuesta **402 Payment Required**
- Body de error: `{"detail": "Daily API limit reached. Upgrade your plan."}`
- Incrementa `calls_today` en cada request autorizado
- El contador se resetea diariamente (ver `POST /admin/dealers/{id}/usage/reset`)

---

## Endpoints de autenticación

| Método | Ruta | Auth requerida | Descripción |
|--------|------|---------------|-------------|
| `POST` | `/auth/register` | No | Crear cuenta + Stripe customer |
| `POST` | `/auth/login` | No | Obtener JWT |
| `POST` | `/auth/refresh` | Bearer refresh token | Renovar access token |
| `POST` | `/auth/logout` | Bearer access token | Revocar token |
| `POST` | `/auth/api-key` | Bearer o X-API-Key | Rotar API key |

---

## Endpoints de admin

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/admin/stats` | KPIs globales (dealers, listings, ROI) |
| `PATCH` | `/admin/dealers/{id}/plan` | Cambiar plan manualmente |
| `PATCH` | `/admin/dealers/{id}/active` | Activar / suspender dealer |
| `POST` | `/admin/dealers/{id}/usage/reset` | Resetear calls_today |
| `POST` | `/admin/dealers/{id}/stripe/customer` | Provisionar Stripe Customer |
| `GET` | `/admin/health` | Health DB con tabla dealers |

Todos requieren plan `admin`. Crear el primer admin directamente en SQLite:
```sql
UPDATE dealers SET plan = 'admin' WHERE email = 'your@email.com';
```

---

## Variables de entorno necesarias

```env
# Obligatorias
JWT_SECRET=<32+ bytes hex>
AGARTHA_DB_PATH=.tmp/agartha.db

# Stripe (opcionales en dev; obligatorias en prod para planes de pago)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_BASIC=price_...
STRIPE_PRICE_PREMIUM=price_...
AGARTHA_PUBLIC_URL=https://tu-dominio.com

# Resend (opcional; sin él los emails se omiten silenciosamente)
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=noreply@tu-dominio.com
```

---

## Rotación de API keys en producción

1. El dealer llama `POST /auth/api-key` con su Bearer token activo.
2. La API genera un nuevo UUID, almacena su SHA-256 y devuelve la key en texto claro **una sola vez**.
3. La key anterior queda invalidada inmediatamente.
4. El dealer debe actualizar su integración antes de llamar a este endpoint.

---

## Runbook de incidentes

| Síntoma | Causa probable | Acción |
|---------|---------------|--------|
| 402 en todos los requests de un dealer | `calls_today` lleno | Admin reset vía `POST /admin/dealers/{id}/usage/reset` o upgrade de plan |
| 401 con token válido | Token en blacklist o expirado | El cliente debe hacer refresh con su refresh token |
| Registro devuelve 503 | `STRIPE_SECRET_KEY` inválida | Verificar key en dashboard Stripe; el registro funciona sin Stripe |
| API key no funciona tras rotación | Cliente usando key antigua | Recordar al cliente que solo se muestra una vez |
| 403 en `/admin/*` | Dealer no tiene plan `admin` | `UPDATE dealers SET plan='admin' WHERE id=X` en SQLite |
