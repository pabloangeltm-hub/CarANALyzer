import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ExportButton } from '@/components/listings/ExportButton'
import { formatCurrency, formatInteger, formatROI } from '@/lib/utils'
import type { Listing, PaginatedListings } from '@/types/api'

interface ListingsTableProps {
  data?: PaginatedListings
  isError?: boolean
  isLoading?: boolean
  onPageChange: (page: number) => void
  onSelectListing?: (listing: Listing) => void
}

export function ListingsTable({
  data,
  isError = false,
  isLoading = false,
  onPageChange,
  onSelectListing,
}: ListingsTableProps) {
  const [sorting, setSorting] = useState<SortingState>([])
  const parentRef = useRef<HTMLDivElement>(null)
  const rows = data?.items ?? []
  const page = data?.page ?? 1
  const size = data?.size ?? 25
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / size))

  const columns = useMemo<ColumnDef<Listing>[]>(
    () => [
      {
        accessorKey: 'brand',
        header: 'Coche',
        cell: ({ row }) => {
          const listing = row.original
          return (
            <div className="min-w-0">
              <div className="truncate font-medium">
                {[listing.brand, listing.model].filter(Boolean).join(' ') ||
                  'Sin modelo'}
              </div>
              <div className="truncate text-xs text-muted-foreground">
                {listing.year ?? '-'} | {formatInteger(listing.mileage)} km |{' '}
                {listing.location ?? '-'}
              </div>
            </div>
          )
        },
      },
      {
        accessorKey: 'portal',
        header: 'Portal',
        cell: ({ getValue }) => (
          <span className="text-muted-foreground">{String(getValue() ?? '-')}</span>
        ),
      },
      {
        accessorKey: 'price',
        header: 'Precio',
        cell: ({ getValue }) => (
          <div className="text-right">{formatCurrency(getValue<number | null>())}</div>
        ),
      },
      {
        accessorKey: 'market_price',
        header: 'Mercado',
        cell: ({ getValue }) => (
          <div className="text-right">{formatCurrency(getValue<number | null>())}</div>
        ),
      },
      {
        accessorKey: 'roi_neto',
        header: 'ROI',
        cell: ({ getValue }) => (
          <div className="text-right font-medium">
            {formatROI(getValue<number | null>())}
          </div>
        ),
      },
      {
        accessorKey: 'forensic_status',
        header: 'Estado',
        cell: ({ getValue }) => (
          <Badge variant="outline">{String(getValue() ?? 'pendiente')}</Badge>
        ),
      },
    ],
    [],
  )

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  const tableRows = table.getRowModel().rows
  const rowVirtualizer = useVirtualizer({
    count: tableRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64,
    overscan: 6,
  })

  return (
    <section className="overflow-hidden rounded-lg border bg-card">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">Listings recientes</h2>
          <p className="text-xs text-muted-foreground">
            {isLoading ? 'Cargando...' : `${formatInteger(total)} resultados`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ExportButton listings={rows} />
          <Button
            disabled={page <= 1 || isLoading}
            onClick={() => onPageChange(page - 1)}
            size="icon"
            type="button"
            variant="outline"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="min-w-16 text-center text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <Button
            disabled={page >= totalPages || isLoading}
            onClick={() => onPageChange(page + 1)}
            size="icon"
            type="button"
            variant="outline"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-[860px]">
          <div className="grid grid-cols-[minmax(260px,1.8fr)_120px_140px_140px_110px_140px] bg-muted text-xs uppercase text-muted-foreground">
            {table.getHeaderGroups().map((headerGroup) =>
              headerGroup.headers.map((header) => (
                <button
                  className="flex h-11 items-center gap-1 px-4 text-left font-medium disabled:cursor-default"
                  disabled={!header.column.getCanSort()}
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  type="button"
                >
                  <span className={header.id.includes('price') || header.id.includes('roi') ? 'ml-auto' : ''}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </span>
                  <SortIcon direction={header.column.getIsSorted()} />
                </button>
              )),
            )}
          </div>

          <div ref={parentRef} className="relative h-[520px] overflow-auto">
            {isError ? (
              <EmptyState text="No se pudo cargar la API de listings." />
            ) : null}
            {!isError && !isLoading && tableRows.length === 0 ? (
              <EmptyState text="Sin datos todavia. Arranca la API o ajusta filtros." />
            ) : null}
            {isLoading && tableRows.length === 0 ? (
              <EmptyState text="Cargando listings..." />
            ) : null}

            <div
              className="relative"
              style={{ height: `${rowVirtualizer.getTotalSize()}px` }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const row = tableRows[virtualRow.index]
                return (
                  <div
                    className="absolute left-0 grid w-full cursor-pointer grid-cols-[minmax(260px,1.8fr)_120px_140px_140px_110px_140px] border-t text-sm hover:bg-muted/45"
                    key={row.id}
                    onClick={() => onSelectListing?.(row.original)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        onSelectListing?.(row.original)
                      }
                    }}
                    role="button"
                    style={{
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    tabIndex={0}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <div
                        className="flex items-center px-4"
                        key={cell.id}
                      >
                        <div className="w-full min-w-0">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </div>
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function SortIcon({ direction }: { direction: false | 'asc' | 'desc' }) {
  if (direction === 'asc') {
    return <ArrowUp className="h-3.5 w-3.5" />
  }
  if (direction === 'desc') {
    return <ArrowDown className="h-3.5 w-3.5" />
  }
  return <ArrowUpDown className="h-3.5 w-3.5 opacity-40" />
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center px-4 text-center text-sm text-muted-foreground">
      {text}
    </div>
  )
}
