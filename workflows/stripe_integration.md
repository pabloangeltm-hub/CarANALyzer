# SOP — Stripe Integration

> Describe la configuración de productos en Stripe, pruebas locales con Stripe CLI y el flujo completo de webhooks y portal de facturación.

---

## Productos y precios

| Plan | Producto Stripe | Precio | Env var |
|------|----------------|--------|---------|
| `basic` | Agartha Basic | €79 / mes | `STRIPE_PRICE_BASIC` |
| `premium` | Agartha Premium | €199 / mes | `STRIPE_PRICE_PREMIUM` |

### Crear productos (una sola vez por entorno)

```bash
# Asegúrate de tener STRIPE_SECRET_KEY=sk_test_... en .env
python tools/api/setup_stripe_products.py
```

El script:
1. Busca productos existentes por metadata (`agartha_plan=basic/premium`) — idempotente.
2. Crea productos y precios si no existen.
3. Imprime los `price_id` que debes añadir al `.env`:

```
STRIPE_PRICE_BASIC=price_XXXXXXXXXX
STRIPE_PRICE_PREMIUM=price_YYYYYYYYYY
```

Repite con `STRIPE_SECRET_KEY=sk_live_...` para el entorno de producción.

---

## Variables de entorno requeridas

```env
STRIPE_SECRET_KEY=sk_test_...          # o sk_live_... en prod
STRIPE_WEBHOOK_SECRET=whsec_...        # generado por Stripe CLI o dashboard
STRIPE_PRICE_BASIC=price_...
STRIPE_PRICE_PREMIUM=price_...
AGARTHA_PUBLIC_URL=https://tu-dominio.com  # para URLs de redirect
```

---

## Flujo de suscripción completo

```
Dealer                    API                       Stripe
  │                        │                          │
  ├── POST /payments/checkout ──────────────────────► │
  │   {"plan": "basic",    │                          │
  │    "success_url": ..., │                          │
  │    "cancel_url": ...}  │                          │
  │                        ├── ensure_customer() ────►│ Customer.create (si no existe)
  │                        ├── Session.create ────────►│ CheckoutSession
  │◄── {url: checkout.stripe.com/...} ─────────────── │
  │                        │                          │
  ├── [Dealer completa pago en Stripe Checkout] ──────►│
  │                        │                          │
  │                        │◄── POST /webhooks/stripe ─┤ checkout.session.completed
  │                        ├── set_plan(dealer, basic) │
  │                        ├── set_stripe_customer_id  │
  │                        └── Response 200: {received: true}
```

### Portal de autogestion (upgrade / downgrade / cancelar)

```
POST /payments/portal   {"return_url": "https://app/billing"}
    │
    ├── ensure_customer() ──► Stripe Customer
    ├── billing_portal.Session.create ──► Stripe
    └── {url: billing.stripe.com/...}
```

El dealer gestiona suscripción directamente en Stripe. No requiere código adicional.

---

## Webhooks

**Endpoint**: `POST /webhooks/stripe`  
**Verificación**: firma HMAC con `STRIPE_WEBHOOK_SECRET` (via `stripe.Webhook.construct_event`)

| Evento | Efecto |
|--------|--------|
| `checkout.session.completed` | Activa plan basic/premium, persiste `stripe_customer_id` |
| `invoice.payment_failed` | Envía email de pago fallido vía Resend (no suspende de inmediato) |
| `customer.subscription.deleted` | Downgradea dealer a plan `trial` |

Implementado en [`tools/api/routers/webhooks.py`](../tools/api/routers/webhooks.py).

---

## Pruebas locales con Stripe CLI

### Instalación

```bash
# Windows (winget)
winget install Stripe.StripeCLI

# Linux/macOS
brew install stripe/stripe-cli/stripe
```

### Login

```bash
stripe login
```

### Escuchar webhooks en local

```bash
# Terminal 1: API local
uvicorn tools.api.app:app --reload

# Terminal 2: Stripe CLI forward
stripe listen --forward-to http://localhost:8000/webhooks/stripe --print-secret
```

Stripe CLI imprime el `STRIPE_WEBHOOK_SECRET` local. Añádelo al `.env` para pruebas.

### Disparar eventos de prueba

```bash
# Simular suscripción completada
stripe trigger checkout.session.completed

# Simular pago fallido
stripe trigger invoice.payment_failed

# Simular cancelación de suscripción
stripe trigger customer.subscription.deleted
```

### Verificar en los logs

```bash
# Los eventos aparecen en el log del servidor uvicorn
# Confirmar que el dealer cambió de plan en SQLite
python -c "
import sqlite3
conn = sqlite3.connect('.tmp/agartha.db')
for row in conn.execute('SELECT id, email, plan, stripe_customer_id FROM dealers'):
    print(row)
"
```

---

## Pruebas con tarjeta de prueba

| Tarjeta | Comportamiento |
|---------|---------------|
| `4242 4242 4242 4242` | Pago exitoso |
| `4000 0000 0000 0002` | Pago rechazado |
| `4000 0025 0000 3155` | Requiere autenticación 3DS |

Fecha: cualquier futura · CVC: cualquier 3 dígitos · CP: cualquier 5 dígitos.

---

## Configurar portal de facturación en Stripe

1. Ve a [Stripe Dashboard → Billing → Customer portal](https://dashboard.stripe.com/settings/billing/portal).
2. Activa las opciones que quieras (cancelar, cambiar método de pago, ver facturas).
3. Añade los productos Agartha Basic y Agartha Premium como opciones de plan disponibles.
4. Guarda.

El endpoint `POST /payments/portal` crea sesiones en este portal configurado.

---

## Paso a producción

1. Obtén `STRIPE_SECRET_KEY=sk_live_...` del dashboard.
2. Ejecuta el setup script para crear productos en modo live:
   ```bash
   STRIPE_SECRET_KEY=sk_live_... python tools/api/setup_stripe_products.py
   ```
3. Añade los `price_id` live al `.env.production`.
4. Configura el webhook en [Stripe Dashboard → Developers → Webhooks](https://dashboard.stripe.com/webhooks):
   - URL: `https://tu-dominio.com/webhooks/stripe`
   - Eventos: `checkout.session.completed`, `invoice.payment_failed`, `customer.subscription.deleted`
   - Copia el signing secret → `STRIPE_WEBHOOK_SECRET`
5. Despliega y verifica con un pago real de test usando tarjeta `4242...` desde el dashboard.

---

## Runbook de incidentes

| Síntoma | Causa | Acción |
|---------|-------|--------|
| Webhook devuelve 400 | Firma inválida | Verificar `STRIPE_WEBHOOK_SECRET` coincide con el de Stripe |
| Dealer no actualiza plan tras pago | Webhook no llegó | Reenviar evento desde Stripe Dashboard → Webhooks → último evento |
| `503 STRIPE_SECRET_KEY is required` | Var de entorno no cargada | Verificar `.env` en VPS; reiniciar servicio |
| `StripeServiceError: plan basic is not billable` | Price ID no configurado | Añadir `STRIPE_PRICE_BASIC` al `.env` |
| Portal devuelve 400 | Dealer sin `stripe_customer_id` | Admin: `POST /admin/dealers/{id}/stripe/customer` |
