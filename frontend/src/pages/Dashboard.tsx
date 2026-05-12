import { LayoutGrid, List } from 'lucide-react'
import { useState } from 'react'

import { FilterPanel } from '@/components/filters/FilterPanel'
import { KPIBar } from '@/components/kpi/KPIBar'
import { AppLayout } from '@/components/layout/AppLayout'
import { ListingCard, ListingCardGrid, ListingCardSkeleton } from '@/components/listings/ListingCard'
import { ListingDrawer } from '@/components/listings/ListingDrawer'
import { ListingsTable } from '@/components/listings/ListingsTable'
import { ROIBarChart } from '@/components/market/ROIBarChart'
import { PriceTrendChart } from '@/components/market/PriceTrendChart'
import { cn } from '@/lib/utils'
import { useListings } from '@/hooks/useListings'
import { useMarketStats } from '@/hooks/useMarketStats'
import { useFilterStore } from '@/store/filters'
import type { Listing } from '@/types/api'

type ViewMode = 'table' | 'grid'

export function Dashboard() {
  const [selectedListingId, setSelectedListingId] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const { filters, setFilters } = useFilterStore()
  const listingsQuery = useListings(filters)
  const marketQuery = useMarketStats()

  function handleSelectListing(listing: Listing) {
    setSelectedListingId(listing.id)
  }

  const listings = listingsQuery.data?.items ?? []
  const isLoading = listingsQuery.isLoading

  return (
    <AppLayout
      subtitle="Oportunidades detectadas en tiempo real"
      title="Dashboard"
    >
      {/* KPI bar */}
      <KPIBar
        isLoading={marketQuery.isLoading}
        stats={marketQuery.data}
        alertsActive={marketQuery.data?.total_opportunities ?? 0}
      />

      {/* Charts */}
      <section className="grid gap-4 xl:grid-cols-2">
        <ROIBarChart />
        <PriceTrendChart brand={filters.brand} model={filters.model} />
      </section>

      {/* Listings section */}
      <section>
        {/* Section header with view toggle */}
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-subheading font-semibold text-foreground">Listings recientes</h2>
            <p className="text-caption text-muted-foreground mt-0.5">
              {isLoading
                ? 'Cargando...'
                : `${(listingsQuery.data?.total ?? 0).toLocaleString('es-ES')} resultados`}
            </p>
          </div>

          {/* View mode toggle */}
          <div className="flex items-center gap-1 rounded-lg border border-border bg-surface p-1">
            <ViewToggleButton
              active={viewMode === 'grid'}
              icon={<LayoutGrid className="h-3.5 w-3.5" />}
              label="Vista tarjetas"
              onClick={() => setViewMode('grid')}
            />
            <ViewToggleButton
              active={viewMode === 'table'}
              icon={<List className="h-3.5 w-3.5" />}
              label="Vista tabla"
              onClick={() => setViewMode('table')}
            />
          </div>
        </div>

        <FilterPanel />

        {/* Grid view */}
        {viewMode === 'grid' && (
          <div className="mt-4">
            {isLoading ? (
              <ListingCardGrid>
                {Array.from({ length: 8 }).map((_, i) => (
                  <ListingCardSkeleton key={i} />
                ))}
              </ListingCardGrid>
            ) : listings.length === 0 ? (
              <EmptyListings />
            ) : (
              <>
                <ListingCardGrid>
                  {listings.map((listing) => (
                    <ListingCard
                      key={listing.id ?? listing.ad_id}
                      listing={listing}
                      onClick={() => handleSelectListing(listing)}
                    />
                  ))}
                </ListingCardGrid>

                {/* Pagination */}
                <Pagination
                  data={listingsQuery.data}
                  isLoading={isLoading}
                  onPageChange={(page) => setFilters({ page })}
                />
              </>
            )}
          </div>
        )}

        {/* Table view */}
        {viewMode === 'table' && (
          <div className="mt-4">
            <ListingsTable
              data={listingsQuery.data}
              isError={listingsQuery.isError}
              isLoading={isLoading}
              onPageChange={(page) => setFilters({ page })}
              onSelectListing={handleSelectListing}
            />
          </div>
        )}
      </section>

      <ListingDrawer
        listingId={selectedListingId}
        onOpenChange={(open) => {
          if (!open) setSelectedListingId(null)
        }}
      />
    </AppLayout>
  )
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function ViewToggleButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean
  icon: React.ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <button
      aria-label={label}
      aria-pressed={active}
      className={cn(
        'flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-caption font-medium transition-all duration-150',
        active
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted',
      )}
      onClick={onClick}
      type="button"
    >
      {icon}
    </button>
  )
}

function EmptyListings() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-surface py-16 text-center">
      <p className="text-body font-medium text-foreground mb-1">Sin resultados</p>
      <p className="text-caption text-muted-foreground">Ajusta los filtros o arranca el pipeline de scraping.</p>
    </div>
  )
}

function Pagination({
  data,
  isLoading,
  onPageChange,
}: {
  data: { page: number; size: number; total: number } | undefined
  isLoading: boolean
  onPageChange: (page: number) => void
}) {
  if (!data) return null
  const { page, size, total } = data
  const totalPages = Math.max(1, Math.ceil(total / size))

  return (
    <div className="flex items-center justify-center gap-3 mt-6">
      <button
        className="rounded-md border border-border bg-surface px-3 py-1.5 text-caption text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-40 disabled:pointer-events-none"
        disabled={page <= 1 || isLoading}
        onClick={() => onPageChange(page - 1)}
        type="button"
      >
        Anterior
      </button>
      <span className="text-caption text-muted-foreground">
        {page} de {totalPages}
      </span>
      <button
        className="rounded-md border border-border bg-surface px-3 py-1.5 text-caption text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-40 disabled:pointer-events-none"
        disabled={page >= totalPages || isLoading}
        onClick={() => onPageChange(page + 1)}
        type="button"
      >
        Siguiente
      </button>
    </div>
  )
}
