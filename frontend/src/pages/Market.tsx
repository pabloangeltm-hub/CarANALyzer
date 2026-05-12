import { Filter, LayoutGrid, List, SlidersHorizontal, X } from 'lucide-react'
import { useState } from 'react'

import { FilterPanel } from '@/components/filters/FilterPanel'
import { ListingCard, ListingCardGrid, ListingCardSkeleton } from '@/components/listings/ListingCard'
import { ListingDrawer } from '@/components/listings/ListingDrawer'
import { ListingsTable } from '@/components/listings/ListingsTable'
import { AppLayout } from '@/components/layout/AppLayout'
import { ROIBarChart } from '@/components/market/ROIBarChart'
import { ROIHistogramChart } from '@/components/market/ROIHistogramChart'
import { PriceTrendChart } from '@/components/market/PriceTrendChart'
import { cn } from '@/lib/utils'
import { useListings } from '@/hooks/useListings'
import { useFilterStore } from '@/store/filters'
import type { Listing } from '@/types/api'

type ViewMode = 'grid' | 'table'

export function Market() {
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [selectedListingId, setSelectedListingId] = useState<number | null>(null)
  const { filters, setFilters } = useFilterStore()
  const listingsQuery = useListings(filters)

  const listings = listingsQuery.data?.items ?? []
  const isLoading = listingsQuery.isLoading
  const total = listingsQuery.data?.total ?? 0

  function handleSelectListing(listing: Listing) {
    setSelectedListingId(listing.id)
  }

  return (
    <AppLayout
      subtitle="Análisis agregado de mercado y exploración de listings"
      title="Mercado"
    >
      {/* Charts row */}
      <section className="grid gap-4 xl:grid-cols-2">
        <ROIBarChart />
        <PriceTrendChart />
      </section>
      <ROIHistogramChart />

      {/* Listings section */}
      <section>
        {/* Section header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 min-w-0">
            <h2 className="text-subheading font-semibold text-foreground">Explorar listings</h2>
            <p className="text-caption text-muted-foreground mt-0.5">
              {isLoading ? 'Cargando...' : `${total.toLocaleString('es-ES')} resultados`}
            </p>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2">
            {/* Filter toggle */}
            <button
              aria-pressed={filtersOpen}
              className={cn(
                'flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-caption font-medium transition-all duration-150',
                filtersOpen
                  ? 'border-primary/40 bg-primary/10 text-primary'
                  : 'border-border bg-surface text-muted-foreground hover:text-foreground hover:bg-muted',
              )}
              onClick={() => setFiltersOpen((v) => !v)}
              type="button"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Filtros
              {filtersOpen && <X className="h-3 w-3 ml-0.5 opacity-70" />}
            </button>

            {/* View toggle */}
            <div className="flex items-center gap-1 rounded-lg border border-border bg-surface p-1">
              <ViewBtn
                active={viewMode === 'grid'}
                icon={<LayoutGrid className="h-3.5 w-3.5" />}
                label="Tarjetas"
                onClick={() => setViewMode('grid')}
              />
              <ViewBtn
                active={viewMode === 'table'}
                icon={<List className="h-3.5 w-3.5" />}
                label="Tabla"
                onClick={() => setViewMode('table')}
              />
            </div>
          </div>
        </div>

        {/* Collapsible filter panel */}
        {filtersOpen && (
          <div className="mb-4 rounded-xl border border-border bg-surface p-4 animate-slide-down">
            <FilterPanel />
          </div>
        )}

        {/* Grid view */}
        {viewMode === 'grid' && (
          <>
            {isLoading ? (
              <ListingCardGrid>
                {Array.from({ length: 12 }).map((_, i) => <ListingCardSkeleton key={i} />)}
              </ListingCardGrid>
            ) : listings.length === 0 ? (
              <EmptyState />
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
                <MarketPagination
                  data={listingsQuery.data}
                  isLoading={isLoading}
                  onPageChange={(page) => setFilters({ page })}
                />
              </>
            )}
          </>
        )}

        {/* Table view */}
        {viewMode === 'table' && (
          <ListingsTable
            data={listingsQuery.data}
            isError={listingsQuery.isError}
            isLoading={isLoading}
            onPageChange={(page) => setFilters({ page })}
            onSelectListing={handleSelectListing}
          />
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

function ViewBtn({ active, icon, label, onClick }: {
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

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-surface py-16 text-center">
      <Filter className="h-8 w-8 text-muted-foreground/40 mb-3" />
      <p className="text-body font-medium text-foreground mb-1">Sin resultados</p>
      <p className="text-caption text-muted-foreground">Ajusta los filtros para encontrar listings.</p>
    </div>
  )
}

function MarketPagination({
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
      <span className="text-caption text-muted-foreground">{page} de {totalPages}</span>
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
