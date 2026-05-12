import { Check, Minus, Zap } from 'lucide-react'
import { useState } from 'react'

import { cn } from '@/lib/utils'

/* ── Plan data ────────────────────────────────────────────────────────────── */

interface PlanFeature {
  label: string
  free: boolean | string
  starter: boolean | string
  pro: boolean | string
  elite: boolean | string
}

const plans = [
  {
    id: 'free',
    name: 'Free',
    price: { monthly: 0, annual: 0 },
    roi: '≤ 5% ROI visible',
    description: 'Para explorar la plataforma.',
    cta: 'Empezar gratis',
    ctaHref: '/register',
    highlighted: false,
  },
  {
    id: 'starter',
    name: 'Starter',
    price: { monthly: 49, annual: 39 },
    roi: '≤ 12% ROI visible',
    description: 'Para dealers que empiezan con el arbitraje.',
    cta: 'Empezar con Starter',
    ctaHref: '/checkout?plan=starter',
    highlighted: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    price: { monthly: 99, annual: 79 },
    roi: '≤ 20% ROI visible',
    description: 'Para dealers activos que necesitan velocidad.',
    cta: 'Empezar con Pro',
    ctaHref: '/checkout?plan=pro',
    highlighted: true,
  },
  {
    id: 'elite',
    name: 'Elite',
    price: { monthly: 199, annual: 159 },
    roi: 'ROI ilimitado (>20%)',
    description: 'Para operaciones de alto volumen.',
    cta: 'Hablar con ventas',
    ctaHref: 'mailto:sales@agartha.io',
    highlighted: false,
  },
]

const features: PlanFeature[] = [
  { label: 'ROI máximo visible',        free: '≤ 5%',        starter: '≤ 12%',       pro: '≤ 20%',        elite: 'Ilimitado' },
  { label: 'Búsquedas por día',         free: '10',          starter: '100',          pro: 'Ilimitadas',   elite: 'Ilimitadas' },
  { label: 'Portales cubiertos',        free: '2',           starter: '4',            pro: '4+',           elite: '4+' },
  { label: 'Alertas Telegram',          free: false,         starter: 'Básicas',      pro: 'Avanzadas',    elite: 'Instantáneas' },
  { label: 'Intervalo de alerta',       free: '-',           starter: '1 hora',       pro: '15 minutos',   elite: '5 minutos' },
  { label: 'Historial de precios',      free: false,         starter: '7 días',       pro: '30 días',      elite: '90 días' },
  { label: 'API key (integración CRM)', free: false,         starter: false,          pro: true,           elite: true },
  { label: 'ForensicAgent IA completo', free: false,         starter: false,          pro: false,          elite: true },
  { label: 'Exportar CSV / Excel',      free: false,         starter: false,          pro: false,          elite: true },
  { label: 'Saved Searches',            free: '1',           starter: '5',            pro: '20',           elite: 'Ilimitadas' },
  { label: 'Comparador de anuncios',    free: false,         starter: false,          pro: true,           elite: true },
  { label: 'Notas privadas',            free: false,         starter: false,          pro: true,           elite: true },
  { label: 'Soporte',                   free: 'Comunidad',   starter: 'Email',        pro: 'Email + chat', elite: 'SLA 24h' },
]

/* ── FeatureCell ──────────────────────────────────────────────────────────── */

function FeatureCell({ value }: { value: boolean | string }) {
  if (value === true)  return <Check className="h-4 w-4 text-accent mx-auto" />
  if (value === false) return <Minus className="h-4 w-4 text-border mx-auto" />
  return <span className="text-caption text-muted-foreground">{value}</span>
}

/* ── Pricing page ─────────────────────────────────────────────────────────── */

export function Pricing() {
  const [annual, setAnnual] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <header className="flex items-center justify-between h-14 px-6 border-b border-border bg-surface">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Zap className="h-4 w-4 text-primary-foreground" strokeWidth={2.5} />
          </div>
          <span className="text-[15px] font-bold text-foreground">Agartha</span>
        </div>
        <a
          className="text-caption font-medium text-muted-foreground hover:text-foreground transition-colors"
          href="/login"
        >
          Acceder →
        </a>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-16 space-y-16">

        {/* Hero */}
        <div className="text-center space-y-4">
          <h1 className="text-display font-bold text-foreground">
            Precios por ROI real,<br />no por llamadas de API.
          </h1>
          <p className="text-body text-muted-foreground max-w-xl mx-auto">
            Paga por lo que descubres. Cuanto mejor es el plan, mayores oportunidades de arbitraje puedes ver.
          </p>

          {/* Toggle */}
          <div className="flex items-center justify-center gap-3 mt-6">
            <span className={cn('text-caption font-medium', !annual ? 'text-foreground' : 'text-muted-foreground')}>
              Mensual
            </span>
            <button
              aria-label="Cambiar a facturación anual"
              className={cn(
                'relative h-6 w-11 rounded-full border transition-colors duration-200',
                annual ? 'bg-primary border-primary' : 'bg-muted border-border',
              )}
              onClick={() => setAnnual((v) => !v)}
              role="switch"
              aria-checked={annual}
              type="button"
            >
              <span className={cn(
                'absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform duration-200',
                annual ? 'translate-x-5' : 'translate-x-0.5',
              )} />
            </button>
            <span className={cn('text-caption font-medium', annual ? 'text-foreground' : 'text-muted-foreground')}>
              Anual
              <span className="ml-1.5 rounded-full bg-accent/15 text-accent px-1.5 py-0.5 text-[10px] font-bold">−20%</span>
            </span>
          </div>
        </div>

        {/* Plan cards */}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={cn(
                'relative flex flex-col rounded-2xl border p-6 transition-all duration-200',
                plan.highlighted
                  ? 'border-primary bg-primary/5 shadow-glow-primary'
                  : 'border-border bg-surface hover:border-primary/30',
              )}
            >
              {plan.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="rounded-full bg-primary px-3 py-1 text-[11px] font-bold text-primary-foreground whitespace-nowrap">
                    Más popular
                  </span>
                </div>
              )}

              <div className="mb-4">
                <h2 className="text-body font-bold text-foreground">{plan.name}</h2>
                <p className="text-caption text-muted-foreground mt-0.5">{plan.description}</p>
              </div>

              <div className="mb-4">
                {plan.price.monthly === 0 ? (
                  <p className="text-display font-bold text-foreground">Gratis</p>
                ) : (
                  <div>
                    <span className="text-display font-bold text-foreground">
                      €{annual ? plan.price.annual : plan.price.monthly}
                    </span>
                    <span className="text-caption text-muted-foreground">/mes</span>
                    {annual && (
                      <p className="text-caption text-muted-foreground mt-0.5">
                        €{plan.price.annual * 12}/año · ahorra €{(plan.price.monthly - plan.price.annual) * 12}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* ROI badge */}
              <div className="mb-6 rounded-lg bg-muted/60 px-3 py-2">
                <p className="text-caption font-semibold text-foreground">{plan.roi}</p>
              </div>

              <a
                className={cn(
                  'mt-auto flex items-center justify-center rounded-lg px-4 py-2.5 text-caption font-semibold transition-all duration-150',
                  plan.highlighted
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'border border-border bg-transparent text-foreground hover:bg-muted',
                )}
                href={plan.ctaHref}
              >
                {plan.cta}
              </a>
            </div>
          ))}
        </div>

        {/* Feature comparison table */}
        <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
          <table className="w-full min-w-[640px] border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="py-4 px-5 text-left text-caption font-semibold text-muted-foreground w-[35%]">
                  Característica
                </th>
                {plans.map((p) => (
                  <th
                    key={p.id}
                    className={cn(
                      'py-4 px-4 text-center text-caption font-bold',
                      p.highlighted ? 'text-primary' : 'text-foreground',
                    )}
                  >
                    {p.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {features.map((feature, i) => (
                <tr
                  key={feature.label}
                  className={cn(
                    'border-b border-border/50 last:border-0',
                    i % 2 === 0 ? 'bg-transparent' : 'bg-muted/20',
                  )}
                >
                  <td className="py-3.5 px-5 text-caption text-foreground">{feature.label}</td>
                  <td className="py-3.5 px-4 text-center"><FeatureCell value={feature.free} /></td>
                  <td className="py-3.5 px-4 text-center"><FeatureCell value={feature.starter} /></td>
                  <td className={cn('py-3.5 px-4 text-center', 'bg-primary/5')}>
                    <FeatureCell value={feature.pro} />
                  </td>
                  <td className="py-3.5 px-4 text-center"><FeatureCell value={feature.elite} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* FAQ / CTA */}
        <div className="text-center space-y-4 pb-8">
          <h2 className="text-heading font-bold text-foreground">¿Dudas?</h2>
          <p className="text-body text-muted-foreground">
            Escríbenos a{' '}
            <a className="text-primary hover:underline" href="mailto:sales@agartha.io">
              sales@agartha.io
            </a>
            {' '}y te ayudamos a elegir el plan correcto.
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <a
              className="rounded-lg bg-primary px-6 py-2.5 text-body font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
              href="/register"
            >
              Empezar gratis
            </a>
            <a
              className="rounded-lg border border-border px-6 py-2.5 text-body font-semibold text-foreground hover:bg-muted transition-colors"
              href="/login"
            >
              Ya tengo cuenta
            </a>
          </div>
        </div>
      </main>
    </div>
  )
}
