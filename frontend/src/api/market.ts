import { apiClient } from '@/api/client'
import type {
  BrandMetrics,
  MarketStats,
  PriceTrend,
  ROIHistogram,
} from '@/types/api'

export async function getMarketStats() {
  const { data } = await apiClient.get<MarketStats>('/market/stats')
  return data
}

export async function getBrandMetrics(limit = 20) {
  const { data } = await apiClient.get<BrandMetrics[]>('/market/by-brand', {
    params: { limit },
  })
  return data
}

export async function getRoiHistogram(bucketSize = 10) {
  const { data } = await apiClient.get<ROIHistogram>('/market/roi-histogram', {
    params: { bucket_size: bucketSize },
  })
  return data
}

export async function getPriceTrend(params: {
  brand?: string
  model?: string
  year?: number
} = {}) {
  const { data } = await apiClient.get<PriceTrend>('/market/trends', { params })
  return data
}
