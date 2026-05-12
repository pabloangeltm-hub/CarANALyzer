import { Activity, Car, Gauge, Search } from 'lucide-react'
import type { ReactNode } from 'react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency, formatROI } from '@/lib/utils'
import type { MarketStats } from '@/types/api'

export function KPIWidgets({
  isLoading,
  stats,
}: {
  isLoading?: boolean
  stats?: MarketStats
}) {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KpiCard
        icon={<Car className="h-5 w-5" />}
        label="Listings"
        muted={isLoading}
        value={stats?.total_listings ?? 0}
      />
      <KpiCard
        icon={<Activity className="h-5 w-5" />}
        label="Oportunidades"
        muted={isLoading}
        value={stats?.total_opportunities ?? 0}
      />
      <KpiCard
        icon={<Gauge className="h-5 w-5" />}
        label="ROI medio"
        muted={isLoading}
        value={formatROI(stats?.avg_roi_neto)}
      />
      <KpiCard
        icon={<Search className="h-5 w-5" />}
        label="Precio medio"
        muted={isLoading}
        value={formatCurrency(stats?.avg_price)}
      />
    </section>
  )
}

function KpiCard({
  icon,
  label,
  muted,
  value,
}: {
  icon: ReactNode
  label: string
  muted?: boolean
  value: number | string
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-muted-foreground">{label}</CardTitle>
        <div className="text-primary">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-normal">
          {muted ? '...' : value}
        </div>
      </CardContent>
    </Card>
  )
}
