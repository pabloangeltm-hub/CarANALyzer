import { Download } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { formatCurrency, formatROI } from '@/lib/utils'
import type { Listing } from '@/types/api'

export function ExportButton({ listings }: { listings: Listing[] }) {
  function exportCsv() {
    const headers = [
      'portal',
      'ad_id',
      'brand',
      'model',
      'year',
      'mileage',
      'price',
      'market_price',
      'roi_neto',
      'forensic_status',
      'url',
    ]
    const rows = listings.map((listing) => [
      listing.portal,
      listing.ad_id,
      listing.brand ?? '',
      listing.model ?? '',
      listing.year ?? '',
      listing.mileage ?? '',
      formatCurrency(listing.price),
      formatCurrency(listing.market_price),
      formatROI(listing.roi_neto),
      listing.forensic_status ?? '',
      listing.url ?? '',
    ])
    const csv = [headers, ...rows]
      .map((row) => row.map((value) => `"${String(value).split('"').join('""')}"`).join(','))
      .join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'agartha-listings.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Button disabled={listings.length === 0} onClick={exportCsv} type="button" variant="outline">
      <Download className="h-4 w-4" />
      CSV
    </Button>
  )
}
