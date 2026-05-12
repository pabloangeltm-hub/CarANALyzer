import { create } from 'zustand'

import type { ListingFilters } from '@/types/api'

interface FilterState {
  filters: ListingFilters
  setFilters: (filters: Partial<ListingFilters>) => void
  resetFilters: () => void
}

const defaultFilters: ListingFilters = {
  page: 1,
  size: 25,
  min_roi: 0,
}

function withCleanValues(filters: ListingFilters): ListingFilters {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== '' && value != null),
  )
}

export const useFilterStore = create<FilterState>((set) => ({
  filters: defaultFilters,
  setFilters: (filters) =>
    set((state) => ({
      filters: withCleanValues({
        ...state.filters,
        ...filters,
        page: filters.page ?? 1,
      }),
    })),
  resetFilters: () => set({ filters: defaultFilters }),
}))
