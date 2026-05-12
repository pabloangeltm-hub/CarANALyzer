export interface PriceHistoryPoint {
  price: number
  scraped_at: string
}

export interface Listing {
  id: number | null
  portal: string
  ad_id: string
  brand: string | null
  model: string | null
  year: number | null
  mileage: number | null
  price: number | null
  market_price: number | null
  roi_bruto: number | null
  roi_neto: number | null
  repair_cost: number | null
  condition_score: number | null
  images_count: number | null
  seller_type: string | null
  location: string | null
  price_history: PriceHistoryPoint[]
  forensic_status: string | null
  forensic_summary: string | null
  url: string | null
  scraped_at: string | null
}

export interface ListingFilters {
  q?: string
  brand?: string
  model?: string
  portal?: string
  seller_type?: string
  forensic_status?: string
  year_min?: number
  year_max?: number
  price_min?: number
  price_max?: number
  roi_min?: number
  min_roi?: number
  page?: number
  size?: number
}

export interface PaginatedListings {
  items: Listing[]
  total: number
  page: number
  size: number
}

export interface BrandMetrics {
  brand: string
  listings_count: number
  avg_price: number | null
  avg_market_price: number | null
  avg_roi_neto: number | null
  opportunities_count: number
}

export interface ROIHistogramBucket {
  min_roi: number
  max_roi: number
  count: number
}

export interface ROIHistogram {
  buckets: ROIHistogramBucket[]
  total_count: number
}

export interface PriceTrendPoint {
  date: string
  avg_price: number
  listings_count: number
}

export interface PriceTrend {
  brand: string | null
  model: string | null
  year: number | null
  points: PriceTrendPoint[]
}

export interface MarketStats {
  total_listings: number
  total_opportunities: number
  avg_roi_neto: number | null
  avg_price: number | null
  avg_market_price: number | null
  by_brand: BrandMetrics[]
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string | null
  token_type: 'bearer'
  expires_in: number
}

export interface APIKeyCreate {
  name: string
  expires_at?: string | null
}

export interface APIKeyResponse {
  id: number | null
  name: string
  prefix: string
  api_key: string | null
  created_at: string | null
  expires_at: string | null
  last_used_at: string | null
  active: boolean
}
