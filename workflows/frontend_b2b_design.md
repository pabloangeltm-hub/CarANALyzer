# Frontend B2B Design — Agartha SaaS
*Generado por Claude Code — F3-T01 (Research) + F3-T02 (Wireframes) + F3-T03 (Stack Decision)*

---

## Stack Seleccionado

### Resultado de `/find-skills` (2026-05-08)

| Dominio | Skill encontrado | Installs | Decisión |
|---------|-----------------|----------|----------|
| Component library | `giuseppe-trisciuoglio/developer-kit@shadcn-ui` | **16.9K** | ✅ Instalar |
| Dashboard patterns | `anthropics/knowledge-work-plugins@build-dashboard` | **2.7K** | ✅ Instalar |
| Charts | `antvis/chart-visualization-skills@chart-visualization` | **2.2K** | ✅ Instalar |
| Data fetching | `tanstack-skills/tanstack-skills@tanstack-query` | **1.7K** | ✅ Instalar |
| Virtual scroll | `tanstack-skills/tanstack-skills@tanstack-virtual` | 529 | ✅ Instalar |
| Charts (React) | `ansanabria/skills@recharts` | 484 | ✅ Instalar |
| Vue virtual scroll | `harlan-zw/vue-ecosystem-skills@tanstack-vue-virtual-skilld` | 61 | ❌ Vue descartado |
| React SPA generic | `nico-martin/skills@react-spa` | 14 | ❌ Muy bajo |

### Decisión Final de Stack

```
SPA Framework:      React 18 + TypeScript 5 + Vite 5
Component library:  shadcn/ui + Tailwind CSS 3
Data table:         TanStack Table v8 + TanStack Virtual v3
Data fetching:      TanStack Query v5
Charts:             Recharts 2.x
State (filtros):    Zustand 4 (sin Redux overhead)
Routing:            React Router v6
HTTP client:        Axios (interceptors JWT refresh automático)
```

### Justificación

**React + TypeScript**: ecosistema más maduro para B2B dashboards, soporte nativo en todos los skills encontrados, mejor integración con FastAPI OpenAPI schema via `openapi-typescript-codegen`.

**shadcn/ui** (16.9K installs — señal dominante): componentes headless + accesibles sobre Radix UI, totalmente customizables, basados en Tailwind. Estándar actual para paneles B2B SaaS. No añade bundle de componentes que no se usen.

**TanStack Table + Virtual** (529 installs, org oficial): mejor tabla para datasets grandes sin paginación completa en DOM. Virtual scroll permite 10K+ rows sin degradar rendimiento. Sort/filter multi-columna integrado.

**TanStack Query v5** (1.7K installs, org oficial): caché automático de respuestas API, refetch en background, estados loading/error declarativos. Reemplaza `useEffect + fetch` manual. Sincroniza filtros URL con el estado del servidor.

**Recharts**: componentes React nativos (no wrappers), responsive containers, cubre todos los gráficos necesarios (ROI bar, price trend line, ROI histogram).

**Zustand**: 2KB bundle, store reactivo para estado de filtros compartido entre FilterPanel y ListingsTable, sin boilerplate Redux.

### Skills a instalar para Codex (F3-T04)

```bash
npx skills add giuseppe-trisciuoglio/developer-kit@shadcn-ui -g -y
npx skills add tanstack-skills/tanstack-skills@tanstack-query -g -y
npx skills add tanstack-skills/tanstack-skills@tanstack-virtual -g -y
npx skills add ansanabria/skills@recharts -g -y
npx skills add anthropics/knowledge-work-plugins@build-dashboard -g -y
```

---

## Wireframes ASCII — F3-T02

### 1. Dashboard Principal (1280px desktop)

```
+--sidebar-240px--+--main-1040px----------------------------------------+
|                 |                                              [?] [👤] |
| ◉ AGARTHA B2B  |  Dashboard                                           |
|                 +------------------------------------------------------+
| ▶ Dashboard     |  ┌────────────┐  ┌────────────┐  ┌────────┐  ┌─────┐|
|   Mercado       |  │ 🚗 47      │  │ 📈 23.4%  │  │ 1,240  │  │ 12  │|
|   Alertas       |  │ Oportunid. │  │ ROI Medio  │  │Listings│  │Alert│|
|   Búsquedas     |  │ hoy        │  │ (30d)      │  │ totales│  │ hoy │|
|   ─────────     |  └────────────┘  └────────────┘  └────────┘  └─────┘|
|   ⚙️ Config     +------------------------------------------------------+
|                 |  FILTROS                                  [Limpiar ✕]|
|   [Trial]       |  [Marca ▾] [Año: 2015 ──●─── 2024]                   |
|   500 req/día   |  [€: 0 ────────●── 50,000] [ROI ≥ ___]              |
|                 |  [Forense ▾] [🔍 Buscar modelo...] [⬇ CSV]          |
|                 +------------------------------------------------------+
|                 | Marca   Modelo  Año   KM      Precio   ROI    Est.  →|
|                 | ──────────────────────────────────────────────────── |
|                 | BMW     320d    2019  85,000  €12,500  31.2%  ✅     |
|                 | Ford    Focus   2020  62,000  € 9,800  28.7%  ⚠️     |
|                 | VW      Golf    2018  95,000  €11,200  25.1%  ✅     |
|                 | Renault Clio    2021  41,000  € 7,400  22.8%  ✅     |
|                 | Toyota  Yaris   2020  55,000  € 8,900  20.3%  ❌     |
|                 | ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·|
|                 |            [← Ant.]  1 / 47  [Sig. →]               |
+-----------------+------------------------------------------------------+
```

**Notas tabla:**
- Virtual scroll: solo renderiza ~15 rows visibles, dataset completo en memoria
- Columna `→` abre el Listing Drawer lateral (480px)
- Header sticky al hacer scroll vertical
- Sort en todas las columnas clicando header (▲▼)
- `Est.` = estado forense: ✅ limpio, ⚠️ alerta leve, ❌ daño importante

---

### 2. Drawer Detalle de Listing (480px, overlay derecho)

```
+---overlay-background---+---drawer-480px--+
|                         |                 |
|                         | BMW 320d 2019 [✕]|
|                         | ─────────────── |
|                         | DATOS BÁSICOS   |
|                         | Portal: Milanun.|
|                         | Precio: €12,500 |
|                         | Km:      85,000 |
|                         | Año:     2019   |
|                         | Vendor:  Partic.|
|                         | Loc.:    Madrid |
|                         | ─────────────── |
|                         | VALORACIÓN      |
|                         | Precio mercado  |
|                         | €15,200         |
|                         | Max bid aceptable|
|                         | €13,680         |
|                         | ROI estimado    |
|                         | 31.2% ████████░ |
|                         | ─────────────── |
|                         | INFORME FORENSE |
|                         | Daño frontal    |
|                         | leve (parachoq.)|
|                         | Score: 72/100   |
|                         | Confianza: 0.88 |
|                         | ─────────────── |
|                         | HISTORIAL PRECIO|
|                         | ● 15 abr €13,000|
|                         | ● 22 abr €12,800|
|                         | ● 01 may €12,500|
|                         |   (actual) ▼    |
|                         | ─────────────── |
|                         | [Ver en portal→]|
+-+-----------------------+-----------------+
```

---

### 3. Página Mercado — Market Analysis

```
+--sidebar-240px--+--main-1040px----------------------------------------+
|                 |                                                      |
|   Mercado ◀    |  Análisis de Mercado                                 |
|                 +──────────────────────────────────────────────────── |
|                 |  TOP 10 MARCAS POR ROI MEDIO              [30d ▾]   |
|                 |  ┌────────────────────────────────────────────────┐ |
|                 |  │ BMW     ████████████████████████ 31.2%        │ |
|                 |  │ Ford    ██████████████████████   28.7%        │ |
|                 |  │ Toyota  ████████████████████     25.1%        │ |
|                 |  │ VW      ██████████████████       22.4%        │ |
|                 |  │ Seat    ████████████████         19.8%        │ |
|                 |  │ Opel    ██████████████           17.3%        │ |
|                 |  └────────────────────────────────────────────────┘ |
|                 +──────────────────────────────────────────────────── |
|                 |  TENDENCIA DE PRECIO    [Marca ▾] [Modelo ▾]       |
|                 |  ┌────────────────────────────────────────────────┐ |
|                 |  │ €                                              │ |
|                 |  │ 14k  ·                                         │ |
|                 |  │ 13k  ·──╮                                      │ |
|                 |  │ 12k      ╰─────╮   ╭──────────╮               │ |
|                 |  │ 11k            ╰───╯           ╰── ●  actual   │ |
|                 |  │ 10k                                            │ |
|                 |  │      Ene  Feb  Mar  Abr  May                   │ |
|                 |  └────────────────────────────────────────────────┘ |
|                 +──────────────────────────────────────────────────── |
|                 |  DISTRIBUCIÓN ROI (Histogram)                       |
|                 |  ┌────────────────────────────────────────────────┐ |
|                 |  │ #              ██                               │ |
|                 |  │ 120          ████ ██                           │ |
|                 |  │ 80     ██  ██████████                          │ |
|                 |  │ 40  ████████████████████ ██                    │ |
|                 |  │      5% 10% 15% 20% 25% 30% 35%               │ |
|                 |  └────────────────────────────────────────────────┘ |
+-----------------+------------------------------------------------------+
```

---

### 4. Página Alertas — Alert Center

```
+--sidebar-240px--+--main-1040px----------------------------------------+
|                 |                                                      |
|   Alertas ◀    |  Centro de Alertas                    [Marcar leídas]|
|                 +──────────────────────────────────────────────────── |
|                 |  ┌──────────────────────────────────────────────────|
|                 |  │ 🔔 NUEVA  BMW 320d 2019 — ROI 31.2%    hace 4m  |
|                 |  │    Madrid · Milanuncios · €12,500               |
|                 |  │                               [Ver listing →]    |
|                 |  ├──────────────────────────────────────────────────|
|                 |  │ ✅ LEÍDA  Ford Focus 2020 — ROI 28.7%  hace 1h  |
|                 |  │    Barcelona · Wallapop · €9,800                |
|                 |  │                               [Ver listing →]    |
|                 |  ├──────────────────────────────────────────────────|
|                 |  │ ✅ LEÍDA  VW Golf 2018 — ROI 25.1%    hace 3h  |
|                 |  │    Valencia · Milanuncios · €11,200             |
|                 |  │                               [Ver listing →]    |
|                 |  └──────────────────────────────────────────────────|
|                 |  [Cargar más alertas...]                            |
+-----------------+------------------------------------------------------+
```

---

### 5. Búsquedas Guardadas

```
+--sidebar-240px--+--main-1040px----------------------------------------+
|                 |                                                      |
|   Búsquedas ◀  |  Búsquedas Guardadas           [+ Guardar actual]   |
|                 +──────────────────────────────────────────────────── |
|                 |  ┌──────────────────────────────────────────────────|
|                 |  │ 🔍 "BMW ROI > 25%"                    [🗑][→]   |
|                 |  │    BMW · 2016-2022 · ROI≥25% · Cualquier forense|
|                 |  ├──────────────────────────────────────────────────|
|                 |  │ 🔍 "Coches baratos Valencia"           [🗑][→]   |
|                 |  │    Todos · ≤€8,000 · Valencia · Limpio          |
|                 |  ├──────────────────────────────────────────────────|
|                 |  │ 🔍 "Toyota < 80k km"                  [🗑][→]   |
|                 |  │    Toyota · ≤80,000 km · ROI≥15%               |
|                 |  └──────────────────────────────────────────────────|
+-----------------+------------------------------------------------------+
```

---

## Estructura de Archivos Propuesta (F3-T04 Scaffold)

```
frontend/
├── public/
│   └── logo.svg
├── src/
│   ├── api/              # API client layer (F3-T05)
│   │   ├── client.ts     # Axios instance + JWT interceptor
│   │   ├── listings.ts   # listingsApi
│   │   ├── market.ts     # marketApi
│   │   └── auth.ts       # authApi
│   ├── components/
│   │   ├── ui/           # shadcn/ui primitives (auto-generated)
│   │   ├── listings/     # ListingsTable, ListingDrawer
│   │   ├── market/       # ROIBarChart, PriceTrend, ROIHistogram
│   │   ├── filters/      # FilterPanel, SavedSearches
│   │   ├── alerts/       # AlertCenter, AlertCard
│   │   └── kpi/          # KPIWidgets, KPICard
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Market.tsx
│   │   ├── Alerts.tsx
│   │   ├── SavedSearches.tsx
│   │   └── Login.tsx
│   ├── store/
│   │   └── filters.ts    # Zustand store — estado global de filtros
│   ├── hooks/
│   │   ├── useListings.ts     # TanStack Query wrapper
│   │   ├── useMarketStats.ts
│   │   └── useAuth.ts
│   ├── types/
│   │   └── api.ts        # Tipos generados desde FastAPI OpenAPI schema
│   ├── lib/
│   │   └── utils.ts      # cn(), formatCurrency(), formatROI()
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## Dependencias package.json

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "@tanstack/react-query": "^5.40.0",
    "@tanstack/react-table": "^8.17.0",
    "@tanstack/react-virtual": "^3.8.0",
    "recharts": "^2.12.0",
    "zustand": "^4.5.0",
    "axios": "^1.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0",
    "class-variance-authority": "^0.7.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-select": "^2.1.0",
    "@radix-ui/react-slider": "^1.2.0",
    "@radix-ui/react-dropdown-menu": "^2.1.0",
    "lucide-react": "^0.390.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "vite": "^5.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0"
  }
}
```

---

## Mapa Componente → Tarea Codex

| Componente | Tarea | Datos origen |
|-----------|-------|-------------|
| KPIWidgets | F3-T12 | GET /market/stats |
| FilterPanel | F3-T08 | Zustand store |
| ListingsTable | F3-T07 | GET /listings (TanStack Query) |
| ListingDrawer | F3-T11 | GET /listings/{id} |
| ROIBarChart | F3-T09 | GET /market/by-brand |
| PriceTrend | F3-T10 | GET /market/trends?slug= |
| AlertCenter | F3-T15 | TBD — alerts endpoint |
| SavedSearches | F3-T16 | POST/GET/DELETE /searches |
| ExportButton | F3-T17 | GET /listings?format=csv |

---

*Próximo paso para Codex: F3-T04 — scaffold con `npm create vite@latest frontend -- --template react-ts`, instalar dependencias del package.json arriba, configurar Tailwind + shadcn/ui según skill instalada.*
