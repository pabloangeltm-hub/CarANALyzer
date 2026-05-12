import { Play, Save, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { AppLayout } from '@/components/layout/AppLayout'
import { useFilterStore } from '@/store/filters'
import type { ListingFilters } from '@/types/api'

interface SavedSearch {
  id: string
  name: string
  filters: ListingFilters
}

const storageKey = 'agartha.savedSearches'

export function SavedSearches() {
  const [name, setName] = useState('')
  const [searches, setSearches] = useState<SavedSearch[]>(() => readSearches())
  const { filters, setFilters } = useFilterStore()
  const navigate = useNavigate()

  function saveCurrent() {
    const nextSearch: SavedSearch = {
      id: crypto.randomUUID(),
      name: name.trim() || `Busqueda ${searches.length + 1}`,
      filters,
    }
    const nextSearches = [nextSearch, ...searches]
    writeSearches(nextSearches)
    setSearches(nextSearches)
    setName('')
  }

  function removeSearch(id: string) {
    const nextSearches = searches.filter((search) => search.id !== id)
    writeSearches(nextSearches)
    setSearches(nextSearches)
  }

  function runSearch(search: SavedSearch) {
    setFilters(search.filters)
    navigate('/')
  }

  return (
    <AppLayout
      subtitle="Persistencia local hasta que exista endpoint `/searches`."
      title="Busquedas Guardadas"
    >
      <section className="rounded-lg border bg-card p-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <Input
            placeholder="Nombre de la busqueda actual"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <Button onClick={saveCurrent} type="button">
            <Save className="h-4 w-4" />
            Guardar actual
          </Button>
        </div>
      </section>

      <div className="space-y-3">
        {searches.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center text-sm text-muted-foreground">
              Aun no hay busquedas guardadas.
            </CardContent>
          </Card>
        ) : null}
        {searches.map((search) => (
          <Card key={search.id}>
            <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium">{search.name}</p>
                <p className="text-sm text-muted-foreground">
                  {describeFilters(search.filters)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button onClick={() => runSearch(search)} type="button" variant="outline">
                  <Play className="h-4 w-4" />
                  Aplicar
                </Button>
                <Button
                  aria-label="Eliminar busqueda"
                  onClick={() => removeSearch(search.id)}
                  size="icon"
                  type="button"
                  variant="ghost"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </AppLayout>
  )
}

function readSearches(): SavedSearch[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey) ?? '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeSearches(searches: SavedSearch[]) {
  localStorage.setItem(storageKey, JSON.stringify(searches))
}

function describeFilters(filters: ListingFilters) {
  const parts = [
    filters.brand,
    filters.model,
    filters.portal,
    filters.min_roi != null ? `ROI >= ${filters.min_roi}%` : null,
    filters.price_max != null ? `<= ${filters.price_max} EUR` : null,
  ].filter(Boolean)
  return parts.length > 0 ? parts.join(' | ') : 'Sin filtros especificos'
}
