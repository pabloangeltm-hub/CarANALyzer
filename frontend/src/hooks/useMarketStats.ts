import { useQuery } from '@tanstack/react-query'

import {
  getBrandMetrics,
  getMarketStats,
  getPriceTrend,
  getRoiHistogram,
} from '@/api/market'

export function useMarketStats() {
  return useQuery({
    queryKey: ['market', 'stats'],
    queryFn: getMarketStats,
  })
}

export function useBrandMetrics(limit = 20) {
  return useQuery({
    queryKey: ['market', 'by-brand', limit],
    queryFn: () => getBrandMetrics(limit),
  })
}

export function useRoiHistogram(bucketSize = 10) {
  return useQuery({
    queryKey: ['market', 'roi-histogram', bucketSize],
    queryFn: () => getRoiHistogram(bucketSize),
  })
}

export function usePriceTrend(filters: {
  brand?: string
  model?: string
  year?: number
}) {
  return useQuery({
    queryKey: ['market', 'trends', filters],
    queryFn: () => getPriceTrend(filters),
  })
}
