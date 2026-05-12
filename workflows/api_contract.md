# SOP — Contrato API B2B: Referencia de Endpoints

**Tarea:** F2-T24  
**Estado:** Operacional  
**Última actualización:** 2026-05-08  
**OpenAPI:** `GET /openapi.json` | **Swagger UI:** `GET /docs` | **ReDoc:** `GET /redoc`  
**Archivos clave:** `tools/api/app.py`, `tools/api/routers/`, `tools/api/schemas/`

---

## 1. Convenciones Generales

### Base URL

| Entorno | URL |
|---------|-----|
| Desarrollo | `http://127.0.0.1:8000` |
| Producción | `https://api.agartha.io` (pendiente F5) |

### Cabeceras estándar

| Cabecera | Cuándo |
|----------|--------|
| `Content-Type: application/json` | En todos los requests con body |
| `Authorization: Bearer <token>` | Endpoints protegidos con JWT |
| `X-API-Key: <key>` | Alternativa para dealers (endpoints `/dealers/me`) |

### Autenticación — flujo completo

```
Cliente                          API
  │                               │
  ├─ POST /auth/login ───────────►│
  │   {email, password}           │
  │                               ├─ verifica PBKDF2-SHA256
  │◄─ {access_token (1h),         │
  │    refresh_token (7d)} ───────┤
  │                               │
  │  [acceso normal — TTL < 1h]   │
  ├─ GET /listings ──────────────►│
  │   Authorization: Bearer <at>  │
  │◄─ {items, total, ...} ────────┤
  │                               │
  │  [renovación de token]        │
  ├─ POST /auth/refresh ─────────►│
  │   Authorization: Bearer <rt>  │
  │◄─ {access_token (1h),         │
  │    refresh_token (7d)} ───────┤
  │                               │
  │  [API key para s2s]           │
  ├─ POST /auth/api-key ─────────►│
  │   Authorization: Bearer <at>  │
  │◄─ {api_key: "agth_..."} ──────┤   ← solo esta vez; guardar inmediatamente
  │                               │
```

### Rate Limiting

- **Ventana:** configurable (MVP: 100 req/min por IP o API key)
- **Cabeceras en todas las respuestas:**

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
```

- **Al superar el límite:** `HTTP 429` con `Retry-After: <segundos>`

### Formato de errores

FastAPI retorna errores en este formato estándar:

```json
{
  "detail": "Invalid email or password"
}
```

Para errores de validación Pydantic (`422 Unprocessable Entity`):

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "email must contain @",
      "type": "value_error"
    }
  ]
}
```

---

## 2. `/auth` — Autenticación

### `POST /auth/login`

Autentica al dealer y retorna tokens.

**Body:**
```json
{
  "email": "dealer@ejemplo.com",
  "password": "contraseña123"
}
```

**Respuesta `200`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errores:**
| Código | Causa |
|--------|-------|
| `401` | Email no registrado o contraseña incorrecta |
| `403` | Dealer inactivo |
| `422` | Email malformado o contraseña demasiado corta |

---

### `POST /auth/refresh`

Renueva el access token con el refresh token.

**Cabecera:** `Authorization: Bearer <refresh_token>`

**Respuesta `200`:** igual que `/auth/login`

**Errores:**
| Código | Causa |
|--------|-------|
| `401` | Refresh token inválido o expirado |
| `403` | Dealer inactivo |

---

### `POST /auth/logout`

Logout semántico. Retorna `204 No Content`. El cliente debe descartar ambos tokens.

---

### `POST /auth/api-key`

Genera una nueva API key, invalidando la anterior.

**Cabecera:** `Authorization: Bearer <access_token>`

**Body:**
```json
{
  "name": "Mi integración CRM",
  "expires_at": null
}
```

**Respuesta `200`:**
```json
{
  "id": 1,
  "name": "Mi integración CRM",
  "prefix": "agth_abc123",
  "api_key": "agth_abc123xyz...",
  "created_at": "2026-05-08T10:00:00",
  "expires_at": null,
  "active": true
}
```

> **Importante:** `api_key` solo aparece en esta respuesta. Guardarla inmediatamente; no es recuperable.

**Errores:**
| Código | Causa |
|--------|-------|
| `401` | Sin access token o token inválido |
| `404` | Dealer no encontrado (estado inconsistente) |

---

## 3. `/dealers` — Concesionarios

### `POST /dealers`

Registra un nuevo dealer. Sin autenticación previa.

**Body:**
```json
{
  "name": "AutoConcesión Norte",
  "email": "contacto@autonorte.es",
  "password": "contraseña_segura",
  "plan": "trial"
}
```

**Planes disponibles:** `trial` | `basic` | `premium` | `admin`

**Respuesta `201`:** `DealerOut` (ver schema)

**Errores:**
| Código | Causa |
|--------|-------|
| `409` | El email ya está registrado |
| `422` | Validación fallida |

---

### `GET /dealers`

Lista todos los dealers. Uso admin.

**Query params:**

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `limit` | int | `100` | Máx. resultados (1–100) |
| `offset` | int | `0` | Desplazamiento para paginación |

**Respuesta `200`:** `list[DealerOut]`

---

### `GET /dealers/me`

Retorna el perfil del dealer autenticado.

**Autenticación:** `X-API-Key: <key>` o `X-Dealer-ID: <id>`

**Respuesta `200`:** `DealerOut`

---

### `PATCH /dealers/me`

Actualiza nombre, plan o estado.

**Autenticación:** `X-API-Key: <key>` o `X-Dealer-ID: <id>`

**Body** (todos los campos opcionales):
```json
{
  "name": "Nuevo Nombre",
  "plan": "basic",
  "active": true
}
```

**Respuesta `200`:** `DealerOut` actualizado

---

### `GET /dealers/{dealer_id}`

Retorna el perfil de un dealer por ID. Uso admin.

**Respuesta `200`:** `DealerOut`

**Errores:**
| Código | Causa |
|--------|-------|
| `404` | Dealer no encontrado |

---

### Schema `DealerOut`

```json
{
  "id": 1,
  "name": "AutoConcesión Norte",
  "email": "contacto@autonorte.es",
  "plan": "trial",
  "active": true,
  "calls_today": 12,
  "api_key_prefix": "agth_abc123",
  "stripe_customer_id": null,
  "created_at": "2026-05-08T10:00:00"
}
```

### Límites por plan

| Plan | Requests/día | Alertas |
|------|-------------|---------|
| `trial` | 50 | No |
| `basic` | 500 | Sí |
| `premium` | Sin límite | Sí |
| `admin` | Sin límite | Sí |

---

## 4. `/listings` — Catálogo de Vehículos

### `GET /listings`

Lista vehículos con filtros y paginación.

**Query params:**

| Param | Tipo | Descripción |
|-------|------|-------------|
| `q` | string | Búsqueda libre en marca, modelo y localización (LIKE) |
| `brand` | string | Marca (LIKE, case-insensitive) |
| `model` | string | Modelo (LIKE, case-insensitive) |
| `portal` | string | `milanuncios` \| `wallapop` (exacto) |
| `seller_type` | string | `private` \| `professional` (exacto) |
| `forensic_status` | string | `clean` \| `damaged` \| `dudoso` (exacto) |
| `year_min` | int | Año mínimo (1900–2099) |
| `year_max` | int | Año máximo (1900–2099) |
| `price_min` | float | Precio mínimo EUR (≥ 0) |
| `price_max` | float | Precio máximo EUR (≥ 0) |
| `roi_min` / `min_roi` | float | ROI neto mínimo % |
| `page` | int | Página (≥ 1, default 1) |
| `size` | int | Resultados por página (1–100, default 25) |

**Respuesta `200`:**
```json
{
  "items": [ /* lista de ListingOut */ ],
  "total": 342,
  "page": 1,
  "size": 25
}
```

**Ejemplo real:**
```
GET /listings?brand=bmw&year_min=2018&price_max=25000&roi_min=10&page=1&size=10
```

---

### `GET /listings/{listing_id}`

Detalle completo de un vehículo por ID interno.

**Respuesta `200`:** `ListingOut`

**Errores:**
| Código | Causa |
|--------|-------|
| `404` | Listing no encontrado |

---

### Schema `ListingOut`

```json
{
  "id": 1042,
  "portal": "milanuncios",
  "ad_id": "mil-123456",
  "brand": "BMW",
  "model": "Serie 3",
  "year": 2019,
  "mileage": 85000,
  "price": 18500.0,
  "market_price": 22400.0,
  "roi_bruto": 21.08,
  "roi_neto": 14.32,
  "repair_cost": 1050.0,
  "condition_score": null,
  "images_count": 8,
  "seller_type": "private",
  "location": "Madrid",
  "price_history": [
    { "price": 19200.0, "scraped_at": "2026-04-15T10:23:00" },
    { "price": 18500.0, "scraped_at": "2026-05-02T08:11:00" }
  ],
  "forensic_status": "clean",
  "forensic_summary": "Sin descripcion de danos.",
  "url": "https://www.milanuncios.com/coches/...",
  "scraped_at": "2026-05-08T07:30:00"
}
```

---

## 5. `/market` — Análisis de Mercado

### `GET /market/stats`

KPIs globales del catálogo.

**Respuesta `200`:**
```json
{
  "total_listings": 1842,
  "total_opportunities": 234,
  "avg_roi_neto": 8.43,
  "avg_price": 14200.50,
  "avg_market_price": 16800.00,
  "by_brand": [ /* top-20 BrandMetrics */ ]
}
```

---

### `GET /market/by-brand`

Métricas agregadas por marca.

**Query params:**

| Param | Default | Descripción |
|-------|---------|-------------|
| `limit` | 20 | Máx. marcas devueltas (1–100) |

**Respuesta `200`:**
```json
[
  {
    "brand": "BMW",
    "listings_count": 156,
    "avg_price": 19800.50,
    "avg_market_price": 22400.00,
    "avg_roi_neto": 11.2,
    "opportunities_count": 42
  }
]
```

Ordenado por `opportunities_count DESC`.

---

### `GET /market/roi-histogram`

Distribución de ROI neto en buckets.

**Query params:**

| Param | Default | Descripción |
|-------|---------|-------------|
| `bucket_size` | 10.0 | Tamaño del bucket en % (0.1–100) |

**Respuesta `200`:**
```json
{
  "buckets": [
    { "min_roi": -20.0, "max_roi": -10.0, "count": 45 },
    { "min_roi": 0.0,   "max_roi": 10.0,  "count": 312 },
    { "min_roi": 10.0,  "max_roi": 20.0,  "count": 148 }
  ],
  "total_count": 1842
}
```

---

### `GET /market/trends`

Tendencia histórica de precios.

**Query params:**

| Param | Tipo | Descripción |
|-------|------|-------------|
| `brand` | string | Filtro por marca (exacto, case-insensitive) |
| `model` | string | Filtro por modelo (exacto) |
| `year` | int | Filtro por año (1900–2099) |

**Respuesta `200`:**
```json
{
  "brand": "BMW",
  "model": "Serie 3",
  "year": 2019,
  "points": [
    { "date": "2026-04-15", "avg_price": 19200.0, "listings_count": 3 },
    { "date": "2026-05-02", "avg_price": 18650.0, "listings_count": 5 }
  ]
}
```

Ordenado por fecha ASC. Sin filtros devuelve tendencia global.

---

## 6. Endpoints Pendientes (Backlog)

Los siguientes endpoints están planificados pero aún no implementados:

| Endpoint | Tarea | Descripción |
|----------|-------|-------------|
| `GET /admin/*` | F2-T10 | Panel de administración |
| `GET /listings?q=<fts>` | F2-T12 | Full-text search SQLite FTS5 |
| `GET /health` | F2-T20 | Health check + DB status |
| `POST /payments/checkout` | F4-T13 | Stripe checkout |
| `POST /payments/portal` | F4-T14 | Stripe customer portal |
| `POST /webhooks/stripe` | F4-T15 | Webhooks Stripe |
| `POST /auth/register` | F4-T20 | Registro público con email verification |
| `GET /metrics` | F5-T12 | Prometheus metrics |

---

## 7. Notas de Implementación

### Autenticación — Advertencia de compatibilidad

El endpoint `GET /dealers/me` y `PATCH /dealers/me` usan `X-Dealer-ID` / `X-API-Key` como autenticación temporal (F2-T08). En F4, cuando `get_current_dealer()` (F2-T16) esté implementado, se migrarán a Bearer token estándar.

### Base de datos vacía

Si la tabla `listings` no existe todavía (primera ejecución), los endpoints de `/listings` y `/market` retornan arrays/objetos vacíos en lugar de `500 Internal Server Error`. La tabla se crea al inicializar la DB con `db.init_db()`.

### CORS

El origen permitido en desarrollo es `*`. En producción, configurar:
```
AGARTHA_CORS_ORIGINS=https://app.agartha.io
```

### Iniciar el servidor

```bash
uvicorn tools.api.app:app --host 0.0.0.0 --port 8000 --reload
```

La documentación interactiva estará disponible en `http://localhost:8000/docs`.
