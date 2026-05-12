import { apiClient } from '@/api/client'
import type { Listing, ListingFilters, PaginatedListings } from '@/types/api'

function cleanParams(filters: ListingFilters) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== ''),
  )
}

export async function getListings(filters: ListingFilters = {}) {
  const { data } = await apiClient.get<PaginatedListings>('/listings', {
    params: cleanParams(filters),
  })
  return data
}

export async function getListing(listingId: number) {
  const { data } = await apiClient.get<Listing>(`/listings/${listingId}`)
  return data
}
