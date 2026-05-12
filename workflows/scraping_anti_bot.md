# SOP: Scraping Anti-Bot — Session Pool & Recuperación Datadome

## Objetivo
Mantener un pool de sesiones de navegador válidas para bypassar la protección Datadome de Milanuncios y portales equivalentes, detectar y recuperarse de bloqueos automáticamente, y proteger el pool rotando y descartando sesiones comprometidas sin intervención humana.

## Alcance
Este protocolo cubre:
- Generación y mantenimiento del pool de sesiones
- Arquitectura Hit & Run de contextos frescos por página
- Detección de bloqueos Datadome
- Recuperación automática: burn → retry → cooldown → exit
- Alertas y métricas de sesiones restantes

---

## Arquitectura: Session Pool + Hit & Run

### Principio fundamental
Cada página se carga en un **contexto de navegador nuevo** que se destruye al terminar, independientemente del resultado. El estado de autenticación (cookies + LocalStorage + IndexedDB) se inyecta en cada contexto desde un fichero de sesión del pool. Esto desvincula la identidad del bot del proceso del navegador, haciendo cada request prácticamente indistinguible de una visita humana desde ese perfil.

```
Pool de sesiones (.tmp/sessions/*.json)
         │
         ▼
    _pick() → auth_state = session_pool[0]
         │
         ▼
  browser.new_context(storage_state=auth_state)  ← identidad inyectada
         │
         ▼
  Stealth().apply_stealth_async(page)             ← fingerprint limpio
         │
         ▼
  page.goto(url)
         │
    ┌────┴────┐
  BLOCKED?    OK
    │          │
  _burn()    extract_listings()
  retry      context.close()
             sleep(6-10s)
             next page
```

---

## Phase 1 — Generación de Sesiones

### 1.1 Herramienta
`tools/generate_session.py` — abre un Chrome visible (headful) en `https://www.milanuncios.com` y guarda el estado completo del navegador tras 45 segundos.

### 1.2 Procedimiento de generación manual
```bash
python tools/generate_session.py
```

1. Se abre Chrome en Milanuncios.
2. El operador tiene **45 segundos** para:
   - Aceptar el banner de cookies
   - Resolver cualquier captcha que aparezca
   - Navegar 2-3 páginas de anuncios de forma natural (scroll, clic en algún anuncio)
3. El script guarda automáticamente la sesión en:
   ```
   .tmp/sessions/session_{timestamp}.json
   ```
4. Cerrar el navegador manualmente después del guardado.

### 1.3 Cuándo generar nuevas sesiones
| Condición | Acción |
|-----------|--------|
| Pool < 10 sesiones (alerta Telegram) | Generar 5-10 sesiones nuevas inmediatamente |
| Pool < 3 sesiones (umbral crítico) | Parar scraping; generar sesiones antes de reiniciar |
| Todas las sesiones quemadas | Parar 2h mínimo; cambiar IP si es posible; regenerar pool completo |
| Nuevo despliegue / VPS nuevo | Generar pool inicial de ≥ 15 sesiones |

### 1.4 Calidad de sesión
Una sesión es válida cuando:
- El título de la primera página cargada **no** contiene "Pardon Our Interruption"
- Se extraen ≥ 1 listing en la primera página de prueba

---

## Phase 2 — Configuración del Pool

### 2.1 Rutas y constantes (definidas en `tools/scrape_cars.py`)

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `_SESSIONS_DIR` | `.tmp/sessions` | Directorio pool activo |
| `_AUTH_STATE_PATH` | `.tmp/auth_state.json` | Sesión de fallback única |
| `_DELAY_BETWEEN_PAGES` | `(6.0, 10.0)` segundos | Espera aleatoria entre páginas |
| `_DELAY_AFTER_LOAD` | `(1.0, 2.5)` segundos | Espera tras `domcontentloaded` |
| Alerta Telegram | < 10 sesiones | Umbral de aviso automático |
| `MIN_VALID_PRICE` | 500.0 € | Precio mínimo para considerar listing válido |

### 2.2 Prioridad de sesiones al arrancar
```python
pool = sorted(glob(".tmp/sessions/*.json"))
random.shuffle(pool)
if not pool and os.path.exists(".tmp/auth_state.json"):
    pool = [".tmp/auth_state.json"]  # fallback sesión única
```

El shuffle aleatorio evita que siempre se queme la misma sesión si hay bloqueos consistentes en una IP.

### 2.3 User-Agent
- **Con sesión inyectada:** `_WINDOWS_UA` fijo (Chrome 124 / Windows 10). Debe coincidir exactamente con el UA usado durante `generate_session.py` para que las cookies no sean invalidadas por fingerprint mismatch.
- **Sin sesión:** UA aleatorio de la lista `_USER_AGENTS`.

### 2.4 Parámetros de stealth (Chrome flags)
```
--disable-blink-features=AutomationControlled
--disable-dev-shm-usage
--no-sandbox
--disable-infobars
--lang=es-ES,es
```
Más `playwright_stealth` aplicado vía `Stealth().apply_stealth_async(page)` — parchea `navigator.webdriver`, `navigator.plugins`, canvas fingerprint y otras señales.

---

## Phase 3 — Detección de Bloqueos

### 3.1 Señales de bloqueo Datadome

| Señal | Código de detección | Significado |
|-------|--------------------|-|
| Título de página = `"Pardon Our Interruption"` | `if "Pardon Our Interruption" in page_title` | Bloqueo Datadome explícito |
| 0 listings extraídos | `if not page_listings` | Bloqueo silencioso o cambio de DOM |

**Ambas condiciones se tratan como bloqueo** (`blocked = True`) y disparan el mismo flujo de recuperación.

### 3.2 Lo que NO se comprueba (deliberado)
- Códigos HTTP: Datadome devuelve 200 con la página de bloqueo, no un 4xx.
- Redirecciones: Datadome no redirige, sirve la challenge inline.

---

## Phase 4 — Recuperación Automática

### 4.1 Flujo completo de recuperación

```
blocked = True
    │
    ▼
_burn(auth_state)              ← mueve sesión a .tmp/sessions/burnt/
consecutive_burns += 1
    │
    ├─ consecutive_burns < 3 → retry misma página con próxima sesión del pool
    │
    └─ consecutive_burns >= 3
            │
            ▼
        cooldowns_triggered += 1
            │
            ├─ cooldowns_triggered < 2 →
            │       print("[WARNING] IP HOT: 3 sesiones quemadas. Cooldown 15 min")
            │       asyncio.sleep(900)
            │       consecutive_burns = 0
            │       retry misma página
            │
            └─ cooldowns_triggered >= 2 →
                    print("[CRITICAL] IP bloqueada permanentemente")
                    sys.exit(1)           ← detiene todo para salvar sesiones restantes
```

### 4.2 Contadores y su significado

| Contador | Reset | Significado |
|----------|-------|-------------|
| `consecutive_burns` | Al extraer listings exitosamente | Quemas seguidas sin éxito = IP caliente |
| `cooldowns_triggered` | Al extraer listings exitosamente | Cuántos enfriamientos ya se han hecho |

**El reset de ambos en éxito es deliberado:** si se logra una extracción, la IP se considera enfriada y el contador vuelve a cero.

### 4.3 Sesiones quemadas
Las sesiones bloqueadas se mueven a `.tmp/sessions/burnt/` (nunca se eliminan). Esto permite:
- Auditar cuántas sesiones se quemaron en un burst
- Intentar recuperarlas manualmente si el bloqueo fue transitorio
- Analizar patrones de detección por timestamp

### 4.4 Alerta Telegram automática
Cuando `remaining < 10` tras quemar una sesión:
```
⚠️ Alerta Agartha: Quedan solo {N} sesiones disponibles.
```
Requiere `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env`.

---

## Phase 5 — Comportamiento en Éxito

### 5.1 Inter-page delay
Tras extraer exitosamente una página, el scraper espera entre **6 y 10 segundos** (aleatorio) antes de cargar la siguiente. Este rango imita el tiempo de lectura humano y evita patrones de timing detectables.

### 5.2 Incremental brake (modo incremental)
En modo normal (no histórico), si se detecta un `ad_id` ya conocido (`seen_ids`):
1. Se añaden los listings nuevos de esa página
2. Se detiene el scraping inmediatamente

Esto evita procesar páginas de anuncios ya guardados en la base de datos.

### 5.3 Modo histórico (`disable_brake=True`)
Desactiva el brake. Itera todas las páginas sin deduplicación. Usar para dumps iniciales o reconstrucción de histórico completo.

---

## Phase 6 — Operación y Mantenimiento

### 6.1 Checklist antes de cada run
- [ ] Verificar `ls .tmp/sessions/*.json | wc -l` → mínimo 5 sesiones activas
- [ ] Verificar que `.env` tiene `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`
- [ ] Si es primera vez en una IP nueva: generar ≥ 10 sesiones frescas

### 6.2 Diagnóstico de problemas frecuentes

| Síntoma | Causa probable | Solución |
|---------|----------------|---------|
| `sys.exit(1)` tras 2 cooldowns | IP baneada permanentemente por Datadome | Cambiar IP (VPN/proxy/nueva VPS) + regenerar pool |
| Pool a 0 en < 10 páginas | Sesiones antiguas/caducadas | Regenerar pool completo con `generate_session.py` |
| 0 listings en páginas sin "Pardon" | Cambio de DOM en el portal | Actualizar selectores en `MilanunciosScraper._extract_listings()` |
| Telegram alert no llega | `.env` incompleto o Telegram caído | Verificar token + chat_id con `tools/telegram_notifier.py` |
| Sesiones quemadas inmediatamente | UA mismatch (sesión generada con UA diferente) | Regenerar sesiones asegurando `_WINDOWS_UA` consistente |

### 6.3 Estructura de directorios del pool
```
.tmp/
├── sessions/
│   ├── session_1714567890.json    ← sesiones activas
│   ├── session_1714568100.json
│   └── burnt/
│       ├── session_1714500000.json  ← sesiones quemadas (auditoría)
│       └── ...
└── auth_state.json               ← sesión de fallback (legacy)
```

### 6.4 Cuándo usar `auth_state.json` vs pool
- **Pool (recomendado):** múltiples ficheros en `.tmp/sessions/`, permite rotación y burn sin interrumpir el scraping.
- **`auth_state.json` (fallback):** usado automáticamente solo si el directorio `sessions/` está vacío. No tiene rotación — si se quema, el scraper corre sin sesión.

---

## Parámetros de Configuración (.env)

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Sí | Token del bot para alertas de pool bajo |
| `TELEGRAM_CHAT_ID` | Sí | Chat ID donde llegan las alertas |

Los umbrales (`consecutive_burns`, `cooldowns_triggered`, delays) se modifican directamente en `tools/scrape_cars.py` en la sección de constantes.

---

## Edge Cases y Decisiones de Diseño

### ¿Por qué no reintentar con la misma sesión?
Datadome vincula el bloqueo a la combinación IP + perfil de cookies. Reintentar con la misma sesión en la misma IP garantiza otro bloqueo. Quemar la sesión y pasar a la siguiente desvincula el perfil del intento fallido.

### ¿Por qué `sys.exit(1)` en lugar de lanzar excepción?
Dos cooldowns consecutivos indican bloqueo a nivel de IP, no de sesión. Continuar quemaría las sesiones restantes sin beneficio. El exit fuerza una parada limpia preservando el pool para cuando la IP se descongele o se cambie.

### ¿Por qué shuffle aleatorio del pool al inicio?
Si múltiples runs paralelos usan el pool en orden, siempre quemarían las mismas sesiones. El shuffle distribuye el desgaste aleatoriamente entre todas las sesiones disponibles.

### ¿Por qué mover a `burnt/` en lugar de eliminar?
Permite auditoría post-mortem: si un burst quema 20 sesiones en 5 minutos, los timestamps de los ficheros en `burnt/` revelan el patrón y ayudan a ajustar delays o detectar cambios en Datadome.
