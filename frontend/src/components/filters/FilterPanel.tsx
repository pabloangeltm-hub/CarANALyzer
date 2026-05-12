import { RotateCcw, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useFilterStore } from '@/store/filters'
import type { ListingFilters } from '@/types/api'

const portals = ['', 'milanuncios', 'wallapop']
const sellerTypes = ['', 'particular', 'dealer', 'profesional']
const forensicStatuses = ['', 'clean', 'warning', 'damaged', 'unknown']

export function FilterPanel() {
  const { filters, setFilters, resetFilters } = useFilterStore()

  function updateText(key: keyof ListingFilters, value: string) {
    setFilters({ [key]: value || undefined })
  }

  function updateNumber(key: keyof ListingFilters, value: string) {
    setFilters({ [key]: value === '' ? undefined : Number(value) })
  }

  return (
    <section className="rounded-lg border bg-card p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Filtros</h2>
          <p className="text-xs text-muted-foreground">
            Sincronizados con `/listings`.
          </p>
        </div>
        <Button onClick={resetFilters} type="button" variant="outline">
          <RotateCcw className="h-4 w-4" />
          Limpiar
        </Button>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <label className="space-y-1.5 text-xs font-medium text-muted-foreground xl:col-span-2">
          <span>Busqueda</span>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Marca, modelo o ubicacion"
              value={filters.q ?? ''}
              onChange={(event) => updateText('q', event.target.value)}
            />
          </div>
        </label>

        <TextField
          label="Marca"
          value={filters.brand}
          onChange={(value) => updateText('brand', value)}
        />
        <TextField
          label="Modelo"
          value={filters.model}
          onChange={(value) => updateText('model', value)}
        />

        <SelectField
          label="Portal"
          options={portals}
          value={filters.portal}
          onChange={(value) => updateText('portal', value)}
        />
        <SelectField
          label="Vendedor"
          options={sellerTypes}
          value={filters.seller_type}
          onChange={(value) => updateText('seller_type', value)}
        />
        <SelectField
          label="Forense"
          options={forensicStatuses}
          value={filters.forensic_status}
          onChange={(value) => updateText('forensic_status', value)}
        />
        <NumberField
          label="ROI minimo"
          min={-100}
          value={filters.min_roi}
          onChange={(value) => updateNumber('min_roi', value)}
        />

        <NumberField
          label="Ano desde"
          min={1900}
          max={2099}
          value={filters.year_min}
          onChange={(value) => updateNumber('year_min', value)}
        />
        <NumberField
          label="Ano hasta"
          min={1900}
          max={2099}
          value={filters.year_max}
          onChange={(value) => updateNumber('year_max', value)}
        />
        <NumberField
          label="Precio minimo"
          min={0}
          value={filters.price_min}
          onChange={(value) => updateNumber('price_min', value)}
        />
        <NumberField
          label="Precio maximo"
          min={0}
          value={filters.price_max}
          onChange={(value) => updateNumber('price_max', value)}
        />
      </div>
    </section>
  )
}

function TextField({
  label,
  onChange,
  value,
}: {
  label: string
  onChange: (value: string) => void
  value?: string
}) {
  return (
    <label className="space-y-1.5 text-xs font-medium text-muted-foreground">
      <span>{label}</span>
      <Input value={value ?? ''} onChange={(event) => onChange(event.target.value)} />
    </label>
  )
}

function NumberField({
  label,
  max,
  min,
  onChange,
  value,
}: {
  label: string
  max?: number
  min?: number
  onChange: (value: string) => void
  value?: number
}) {
  return (
    <label className="space-y-1.5 text-xs font-medium text-muted-foreground">
      <span>{label}</span>
      <Input
        max={max}
        min={min}
        type="number"
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

function SelectField({
  label,
  onChange,
  options,
  value,
}: {
  label: string
  onChange: (value: string) => void
  options: string[]
  value?: string
}) {
  return (
    <label className="space-y-1.5 text-xs font-medium text-muted-foreground">
      <span>{label}</span>
      <select
        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option || 'all'} value={option}>
            {option || 'Todos'}
          </option>
        ))}
      </select>
    </label>
  )
}
