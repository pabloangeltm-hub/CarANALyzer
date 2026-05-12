import { useQuery } from '@tanstack/react-query'

import { getListing, getListings } from '@/api/listings'
import type { ListingFilters } from '@/types/api'

export function listingsQueryKey(filters: ListingFilters) {
  return ['listings', filters] as const
}

export function useListings(filters: ListingFilters) {
  return useQuery({
    queryKey: listingsQueryKey(filters),
    queryFn: () => getListings(filters),
    placeholderData: (previousData) => previousData,
  })
}

export function useListing(listingId: number | null) {
  return useQuery({
    queryKey: ['listing', listingId],
    queryFn: () => getListing(listingId as number),
    enabled: listingId != null,
  })
}
