import { Bell } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { AppLayout } from '@/components/layout/AppLayout'
import { useListings } from '@/hooks/useListings'
import { formatCurrency, formatROI } from '@/lib/utils'

export function Alerts() {
  const alertsQuery = useListings({ min_roi: 20, page: 1, size: 20 })
  const alerts = alertsQuery.data?.items ?? []

  return (
    <AppLayout
      subtitle="Alertas derivadas de oportunidades con ROI alto."
      title="Centro de Alertas"
    >
      <div className="space-y-3">
        {alertsQuery.isLoading ? (
          <AlertShell text="Cargando alertas..." />
        ) : null}
        {alertsQuery.isError ? (
          <AlertShell text="No se pudo cargar `/listings` para alertas." />
        ) : null}
        {!alertsQuery.isLoading && !alertsQuery.isError && alerts.length === 0 ? (
          <AlertShell text="Sin alertas activas." />
        ) : null}
        {alerts.map((listing) => (
          <Card key={`${listing.portal}-${listing.ad_id}`}>
            <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <div className="mb-1 flex items-center gap-2">
                  <Bell className="h-4 w-4 text-primary" />
                  <Badge variant="secondary">Nueva</Badge>
                  <span className="truncate text-sm font-semibold">
                    {[listing.brand, listing.model, listing.year].filter(Boolean).join(' ')}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {listing.location ?? '-'} | {listing.portal} |{' '}
                  {formatCurrency(listing.price)} | ROI {formatROI(listing.roi_neto)}
                </p>
              </div>
              {listing.url ? (
                <Button asChild variant="outline">
                  <a href={listing.url} rel="noreferrer" target="_blank">
                    Ver listing
                  </a>
                </Button>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>
    </AppLayout>
  )
}

function AlertShell({ text }: { text: string }) {
  return (
    <Card>
      <CardContent className="p-8 text-center text-sm text-muted-foreground">
        {text}
      </CardContent>
    </Card>
  )
}
