import * as Dialog from '@radix-ui/react-dialog'
import { ExternalLink, X } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { useListing } from '@/hooks/useListings'
import { formatCurrency, formatInteger, formatROI } from '@/lib/utils'

export function ListingDrawer({
  listingId,
  onOpenChange,
}: {
  listingId: number | null
  onOpenChange: (open: boolean) => void
}) {
  const listingQuery = useListing(listingId)
  const listing = listingQuery.data
  const priceHistory = listing?.price_history ?? []

  return (
    <Dialog.Root open={listingId != null} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-background/75 backdrop-blur-sm" />
        <Dialog.Content className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l bg-card shadow-xl">
          <div className="flex items-center justify-between border-b px-5 py-4">
            <div>
              <Dialog.Title className="text-base font-semibold tracking-normal">
                {listing
                  ? [listing.brand, listing.model, listing.year].filter(Boolean).join(' ')
                  : 'Listing'}
              </Dialog.Title>
              <Dialog.Description className="text-sm text-muted-foreground">
                {listing?.portal ?? 'Cargando detalle'}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <Button aria-label="Cerrar detalle" size="icon" type="button" variant="ghost">
                <X className="h-4 w-4" />
              </Button>
            </Dialog.Close>
          </div>

          <div className="flex-1 space-y-5 overflow-y-auto p-5">
            {listingQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Cargando detalle...</p>
            ) : null}
            {listingQuery.isError ? (
              <p className="text-sm text-destructive">No se pudo cargar el listing.</p>
            ) : null}
            {listing ? (
              <>
                <Section title="Datos basicos">
                  <Metric label="Precio" value={formatCurrency(listing.price)} />
                  <Metric label="Kilometros" value={`${formatInteger(listing.mileage)} km`} />
                  <Metric label="Vendedor" value={listing.seller_type ?? '-'} />
                  <Metric label="Ubicacion" value={listing.location ?? '-'} />
                </Section>
                <Section title="Valoracion">
                  <Metric label="Precio mercado" value={formatCurrency(listing.market_price)} />
                  <Metric label="ROI bruto" value={formatROI(listing.roi_bruto)} />
                  <Metric label="ROI neto" value={formatROI(listing.roi_neto)} />
                  <Metric label="Coste reparacion" value={formatCurrency(listing.repair_cost)} />
                </Section>
                <Section title="Informe forense">
                  <Metric label="Estado" value={listing.forensic_status ?? 'pendiente'} />
                  <Metric label="Score" value={formatROI(listing.condition_score)} />
                  <p className="text-sm text-muted-foreground">
                    {listing.forensic_summary ?? 'Sin resumen forense.'}
                  </p>
                </Section>
                <Section title="Historial de precio">
                  <div className="space-y-2">
                    {priceHistory.length > 0 ? (
                      priceHistory.map((point, index) => (
                        <div
                          className="flex items-center justify-between rounded-md bg-muted px-3 py-2 text-sm"
                          key={`${point.scraped_at}-${index}`}
                        >
                          <span>{String(point.scraped_at).slice(0, 10)}</span>
                          <span className="font-medium">{formatCurrency(point.price)}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">Sin historial.</p>
                    )}
                  </div>
                </Section>
              </>
            ) : null}
          </div>

          {listing?.url ? (
            <div className="border-t p-5">
              <Button asChild className="w-full">
                <a href={listing.url} rel="noreferrer" target="_blank">
                  <ExternalLink className="h-4 w-4" />
                  Ver en portal
                </a>
              </Button>
            </div>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="space-y-3">
      <h3 className="text-xs font-semibold uppercase text-muted-foreground">{title}</h3>
      {children}
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  )
}
