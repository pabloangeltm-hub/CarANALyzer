import { Activity, Bell, Car, TrendingUp } from 'lucide-react'
import { type ReactNode, useEffect, useRef, useState } from 'react'

import { Skeleton } from '@/components/ui/skeleton'
import { formatROI } from '@/lib/utils'
import type { MarketStats } from '@/types/api'
import { cn } from '@/lib/utils'

/* ── useCountUp ───────────────────────────────────────────────────────────── */

function useCountUp(target: number, duration = 800) {
  const [current, setCurrent] = useState(0)
  const raf = useRef<number | undefined>(undefined)
  const startTime = useRef<number | undefined>(undefined)
  const startVal = useRef(0)

  useEffect(() => {
    if (target === current) return
    startVal.current = current
    startTime.current = undefined

    function step(now: number) {
      if (!startTime.current) startTime.current = now
      const elapsed = now - startTime.current
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
      setCurrent(Math.round(startVal.current + (target - startVal.current) * eased))
      if (progress < 1) {
        raf.current = requestAnimationFrame(step)
      }
    }

    raf.current = requestAnimationFrame(step)
    return () => { if (raf.current) cancelAnimationFrame(raf.current) }
  }, [target, duration])

  return current
}

/* ── KPIStat ──────────────────────────────────────────────────────────────── */

interface KPIStatProps {
  icon: ReactNode
  label: string
  value: string
  delta?: string
  deltaPositive?: boolean
  isLoading?: boolean
  accentClass?: string
}

function KPIStat({ icon, label, value, delta, deltaPositive, isLoading, accentClass }: KPIStatProps) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-border bg-surface px-5 py-4">
      <div className={cn('flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg', accentClass ?? 'bg-primary/10 text-primary')}>
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-caption text-muted-foreground mb-0.5 truncate">{label}</p>
        {isLoading ? (
          <Skeleton className="h-6 w-20 rounded" />
        ) : (
          <p className="text-subheading font-bold text-foreground leading-none">{value}</p>
        )}
        {delta && !isLoading && (
          <p className={cn('text-caption mt-0.5', deltaPositive ? 'text-accent' : 'text-muted-foreground')}>
            {delta}
          </p>
        )}
      </div>
    </div>
  )
}

/* ── KPIBar ───────────────────────────────────────────────────────────────── */

export function KPIBar({
  isLoading,
  stats,
  alertsActive = 0,
}: {
  isLoading?: boolean
  stats?: MarketStats
  alertsActive?: number
}) {
  const totalListings    = useCountUp(stats?.total_listings ?? 0)
  const totalOpp         = useCountUp(stats?.total_opportunities ?? 0)
  const alertsCount      = useCountUp(alertsActive)

  return (
    <section
      aria-label="Métricas principales"
      className="grid gap-3 grid-cols-2 lg:grid-cols-4"
    >
      <KPIStat
        icon={<Car className="h-5 w-5" />}
        label="Listings hoy"
        value={isLoading ? '—' : totalListings.toLocaleString('es-ES')}
        isLoading={isLoading}
        accentClass="bg-primary/10 text-primary"
      />
      <KPIStat
        icon={<Activity className="h-5 w-5" />}
        label="Oportunidades"
        value={isLoading ? '—' : totalOpp.toLocaleString('es-ES')}
        delta={!isLoading && stats ? `de ${totalListings.toLocaleString('es-ES')} listings` : undefined}
        isLoading={isLoading}
        accentClass="bg-accent/10 text-accent"
      />
      <KPIStat
        icon={<TrendingUp className="h-5 w-5" />}
        label="ROI promedio"
        value={isLoading ? '—' : (stats?.avg_roi_neto != null ? `+${formatROI(stats.avg_roi_neto)}` : '—')}
        isLoading={isLoading}
        accentClass="bg-warning/10 text-warning"
        deltaPositive
      />
      <KPIStat
        icon={<Bell className="h-5 w-5" />}
        label="Alertas activas"
        value={isLoading ? '—' : alertsCount.toLocaleString('es-ES')}
        isLoading={isLoading}
        accentClass="bg-primary/10 text-primary"
      />
    </section>
  )
}
