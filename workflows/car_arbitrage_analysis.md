# Workflow: Car Arbitrage Analysis

## Objective
Detectar diariamente vehículos de segunda mano listados por debajo de su valor real de mercado en los portales Coches.net, Milanuncios y AutoScout24, calcular el ROI potencial de reventa, y entregar las oportunidades al usuario mediante alerta Telegram (oportunidades de alto ROI) y registro en Google Sheets (histórico completo).

## Triggers
Activar cuando:
- El sistema ejecuta su ciclo diario automatizado
- El usuario solicita manualmente: "analiza el mercado", "busca oportunidades", "ejecuta el arbitraje"

## Required Inputs
- Credenciales de scraping configuradas para Coches.net, Milanuncios y AutoScout24
- `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env`
- Google Sheets configurado con las columnas definidas en la sección de Outputs
- `GOOGLE_SHEETS_ID` en `.env`

## Optional Inputs
- Filtros de búsqueda: marcas concretas, rango de años, precio máximo de compra
- Umbral de ROI personalizado (por defecto: 15%)

---

## Phase 1 — Scraping

### 1.1 Fuentes
Extraer diariamente de los tres portales:
- **Coches.net**
- **Milanuncios**
- **AutoScout24**

### 1.2 Campos a capturar por anuncio
| Campo | Requerido |
|---|---|
| Marca | ✅ |
| Modelo | ✅ |
| Año | ✅ |
| Kilometraje | ✅ |
| Precio de lista | ✅ |
| URL del anuncio | ✅ |
| Combustible | Recomendado |
| Transmisión | Recomendado |
| Provincia/Ubicación | Recomendado |
| Fecha de extracción | ✅ (añadida por el sistema) |

### 1.3 Deduplicación entre portales
Antes de procesar, eliminar duplicados cruzados usando la combinación `Marca + Modelo + Año + Precio + Kilometraje` como clave de unicidad aproximada.

---

## Phase 2 — Cálculo del Valor de Mercado

### 2.1 Agrupación
Agrupar todos los anuncios scrapeados por: **Marca + Modelo + Año**.

### 2.2 Umbral mínimo de muestra
**Regla crítica:** Si un grupo tiene **menos de 8 anuncios**, el sistema NO calcula ROI para ningún coche de ese grupo.
- Registrar en Google Sheets con `Estado = "Sin datos suficientes"`
- No disparar alerta Telegram

### 2.3 Eliminación de outliers
Para grupos con 8 o más anuncios:
1. Ordenar los anuncios del grupo por precio (ascendente)
2. Descartar el **10% más barato** y el **10% más caro**
3. Trabajar con la muestra central resultante

### 2.4 Precio base de mercado
Calcular la **mediana** de los precios de la muestra central recortada.
> No usar la media aritmética — es susceptible a anuncios trampa (1€, precios inflados).

### 2.5 Ajuste por kilometraje
```
km_desviacion = km_del_coche - km_media_del_grupo
factor_km = km_desviacion / km_media_del_grupo

# Factor de ajuste: cada 10% de desviación de km = ~2% de ajuste de precio
ajuste_precio = precio_base * (-0.02 * (factor_km / 0.10))
precio_mercado_ajustado = precio_base + ajuste_precio
```
- Coche con **menos km que la media** → precio ajustado **sube**
- Coche con **más km que la media** → precio ajustado **baja**

> El coeficiente de ajuste (0.02 por 10% de desviación) es un punto de partida. Calibrar con datos reales una vez el sistema esté operativo.

### 2.6 Cálculo del ROI
```
margen_bruto = precio_mercado_ajustado - precio_lista
roi_bruto = (margen_bruto / precio_lista) * 100

# Estimación de costes operativos (ajustar según experiencia real)
coste_operativo_estimado = precio_lista * 0.05  # 5% por defecto: ITV, gestoría, traslado, pequeñas reparaciones
margen_neto = margen_bruto - coste_operativo_estimado
roi_neto = (margen_neto / precio_lista) * 100
```

---

## Phase 3 — Filtrado y Alertas

### 3.1 Umbral de alerta
Disparar alerta Telegram **solo si `roi_neto >= 15%`**.

### 3.2 Contenido de la alerta Telegram
```
🚗 OPORTUNIDAD DE ARBITRAJE

Vehículo: [Marca] [Modelo] ([Año]) — [Km] km
Precio lista:    [Precio lista] €
Precio mercado:  [Precio mercado ajustado] €
Margen neto:     [Margen neto] € ([ROI neto]%)

🔗 [Link directo al anuncio]
```

### 3.3 Anti-spam
No volver a alertar por el mismo anuncio (misma URL) si ya fue notificado en las últimas 48 horas.

---

## Phase 4 — Registro en Google Sheets

### 4.1 Política de registro
**Todos** los anuncios analizados se registran en Sheets, independientemente de si superan el umbral de ROI.

### 4.2 Estructura de columnas
| Columna | Descripción |
|---|---|
| Fecha | Fecha de extracción |
| Portal | Coches.net / Milanuncios / AutoScout24 |
| Marca | — |
| Modelo | — |
| Año | — |
| Km | Kilometraje anunciado |
| Precio Lista | Precio del anuncio (€) |
| Precio Mercado | Precio de mercado ajustado calculado (€) |
| Margen Bruto (€) | Precio Mercado − Precio Lista |
| Coste Operativo Est. (€) | 5% del precio de lista |
| Margen Neto (€) | Margen Bruto − Coste Operativo |
| ROI Neto (%) | — |
| Tamaño Muestra | Nº de anuncios usados para calcular el precio de mercado |
| Estado | `Pendiente` / `Contactado` / `Descartado` / `Comprado` / `Sin datos suficientes` |
| Link | URL directa al anuncio |
| Notas | Campo libre para uso manual |

### 4.3 Valor por defecto del campo Estado
`Pendiente` — el usuario lo actualiza manualmente según avance la gestión de cada oportunidad.

---

## Edge Cases

| Situación | Comportamiento |
|---|---|
| Anuncio sin kilometraje | Descartar del cálculo de ajuste; usar precio base sin ajuste km. Registrar en Sheets con nota "Sin km" |
| Anuncio sin año | Descartar completamente — no se puede agrupar |
| Grupo con < 8 anuncios | No calcular ROI. Estado = "Sin datos suficientes". Sin alerta |
| Precio de lista = 0 o < 500€ | Clasificar como anuncio trampa y descartar |
| Portal caído / timeout | Loguear el error, continuar con los otros portales. No abortar el ciclo completo |
| Anuncio ya notificado (< 48h) | Registrar en Sheets si es nuevo ciclo, pero no re-alertar por Telegram |
| Fallo en Google Sheets API | Guardar resultados en `.tmp/arbitrage_YYYY-MM-DD.csv` como fallback |

---

## Expected Output
- Registro completo en Google Sheets de todos los anuncios analizados
- Alertas Telegram enviadas solo para oportunidades con ROI neto ≥ 15%
- Log de ejecución en `.tmp/arbitrage_log_YYYY-MM-DD.txt` (errores, portales caídos, estadísticas del ciclo)

## Tools Requeridas
- `tools/scrape_website.py` — adaptar para los tres portales de coches
- `tools/google_sheets.py` — registro de resultados
- `tools/telegram_notify.py` — **a crear**: envío de alertas push (requiere `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env`)
- `tools/car_valuation.py` — **a crear**: lógica de agrupación, recorte, mediana y ajuste por km

## v2 — Mejoras futuras (no implementar hasta validar v1)
- Integrar API de valoración externa (Eurotax / AutoUncle) para aumentar precisión del precio de mercado
- Añadir combustible y transmisión como variables de agrupación adicionales
- Calibrar el coeficiente de ajuste por km con datos reales acumulados
- Dashboard web con histórico de oportunidades y tasa de conversión
