import { AlertCircle, ArrowRight, BarChart3, Car, Loader2, Shield, TrendingUp, Zap } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useLogin } from '@/hooks/useAuth'
import { useAuthStore } from '@/store/auth'
import { cn } from '@/lib/utils'

interface LocationState {
  from?: { pathname?: string }
}

const features = [
  {
    icon: <TrendingUp className="h-5 w-5" />,
    title: 'Arbitraje de ROI real',
    description: 'Detecta oportunidades con hasta +40% de ROI neto automáticamente.',
  },
  {
    icon: <Car className="h-5 w-5" />,
    title: 'Multi-portal en tiempo real',
    description: 'Milanuncios, Wallapop, Coches.net y AutoScout24 en un solo dashboard.',
  },
  {
    icon: <BarChart3 className="h-5 w-5" />,
    title: 'Análisis forense con IA',
    description: 'Estimación automática de reparaciones y daños por Deepseek R1.',
  },
  {
    icon: <Shield className="h-5 w-5" />,
    title: 'Alertas instantáneas',
    description: 'Telegram en tiempo real cuando aparece una oportunidad en tu criterio.',
  },
]

export function Login() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const loginMutation = useLogin()
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as LocationState | null
  const nextPath = state?.from?.pathname ?? '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  if (isAuthenticated) {
    return <Navigate to={nextPath} replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await loginMutation.mutateAsync({ email, password })
    navigate(nextPath, { replace: true })
  }

  return (
    <div className="flex min-h-screen bg-background">

      {/* ── Left: value proposition ─────────────────────────────────────── */}
      <div className="hidden lg:flex flex-col justify-between w-[55%] bg-surface border-r border-border p-12">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
            <Zap className="h-5 w-5 text-primary-foreground" strokeWidth={2.5} />
          </div>
          <div>
            <p className="text-[15px] font-bold text-foreground">Agartha</p>
            <p className="text-caption text-muted-foreground">Dealer Intelligence</p>
          </div>
        </div>

        {/* Hero */}
        <div className="space-y-8">
          <div className="space-y-4">
            <h1 className="text-display text-foreground leading-tight">
              Encuentra las mejores<br />
              oportunidades <span className="text-primary">antes</span><br />
              que la competencia.
            </h1>
            <p className="text-body text-muted-foreground max-w-md leading-relaxed">
              Agartha analiza miles de anuncios de coches de segunda mano en tiempo real,
              calcula el ROI real y te alerta cuando aparece una oportunidad de arbitraje.
            </p>
          </div>

          {/* Features list */}
          <div className="space-y-4">
            {features.map((f) => (
              <div key={f.title} className="flex items-start gap-3.5">
                <div className="flex-shrink-0 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  {f.icon}
                </div>
                <div>
                  <p className="text-body font-semibold text-foreground">{f.title}</p>
                  <p className="text-caption text-muted-foreground mt-0.5">{f.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Testimonial / stat strip */}
        <div className="flex items-center gap-8">
          {[
            { value: '+40%', label: 'ROI máx detectado' },
            { value: '24/7', label: 'Scraping activo' },
            { value: '<15s', label: 'Alerta Telegram' },
          ].map((stat) => (
            <div key={stat.label}>
              <p className="text-heading font-bold text-primary">{stat.value}</p>
              <p className="text-caption text-muted-foreground">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right: login form ────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        {/* Mobile brand */}
        <div className="flex lg:hidden items-center gap-2.5 mb-10">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Zap className="h-4 w-4 text-primary-foreground" strokeWidth={2.5} />
          </div>
          <p className="text-[15px] font-bold">Agartha</p>
        </div>

        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-heading font-bold text-foreground">Acceso dealer</h2>
            <p className="text-body text-muted-foreground mt-1">
              Introduce tus credenciales para continuar.
            </p>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            {/* Email */}
            <div className="space-y-1.5">
              <label className="text-caption font-semibold text-foreground" htmlFor="email">
                Email
              </label>
              <Input
                autoComplete="email"
                id="email"
                inputMode="email"
                minLength={3}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="dealer@empresa.com"
                required
                type="email"
                value={email}
                className="h-10 bg-surface-elevated border-border focus:border-primary/50 focus:ring-primary/20"
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="text-caption font-semibold text-foreground" htmlFor="password">
                Contraseña
              </label>
              <Input
                autoComplete="current-password"
                id="password"
                minLength={8}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                type="password"
                value={password}
                className="h-10 bg-surface-elevated border-border focus:border-primary/50 focus:ring-primary/20"
              />
            </div>

            {/* Error */}
            {loginMutation.isError && (
              <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-caption text-destructive">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
                <span>Credenciales inválidas o API no disponible.</span>
              </div>
            )}

            {/* Submit */}
            <Button
              className={cn(
                'w-full h-10 font-semibold gap-2',
                'bg-primary text-primary-foreground hover:bg-primary/90',
                'transition-all duration-150',
              )}
              disabled={loginMutation.isPending}
              type="submit"
            >
              {loginMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  Entrar
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          <p className="mt-6 text-center text-caption text-muted-foreground">
            ¿No tienes cuenta?{' '}
            <a
              className="text-primary hover:text-primary/80 font-medium transition-colors"
              href="/pricing"
            >
              Ver planes
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
