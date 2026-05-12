import { ArrowRight, Car, ExternalLink, Lock, TrendingUp } from 'lucide-react'

import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency, formatInteger, formatROI } from '@/lib/utils'
import type { Listing } from '@/types/api'
import { cn } from '@/lib/utils'

/* ── ROI tier helpers ─────────────────────────────────────────────────────── */

type ROITier = 'high' | 'mid' | 'low' | 'redacted'

function roiTier(roi: number | null, redacted?: boolean): ROITier {
  if (redacted) return 'redacted'
  if (roi == null) return 'low'
  if (roi > 15) return 'high'
  if (roi > 5)  return 'mid'
  return 'low'
}

const tierStyles: Record<ROITier, string> = {
  high:     'bg-accent/15 text-accent border-accent/30',
  mid:      'bg-warning/15 text-warning border-warning/30',
  low:      'bg-muted text-muted-foreground border-transparent',
  redacted: 'bg-muted text-muted-foreground border-transparent',
}

/* ── Time-ago helper ──────────────────────────────────────────────────────── */

function timeAgo(isoDate: string | null): string {
  if (!isoDate) return ''
  const diff = (Date.now() - new Date(isoDate).getTime()) / 1000
  if (diff < 3600)   return `hace ${Math.round(diff / 60)} min`
  if (diff < 86400)  return `hace ${Math.round(diff / 3600)} h`
  return `hace ${Math.round(diff / 86400)} d`
}

/* ── Portal badge colour ──────────────────────────────────────────────────── */

const portalColor: Record<string, string> = {
  milanuncios: 'text-[#ef4444]',
  wallapop:    'text-[#14a05e]',
  cochesnet:   'text-[#3b82f6]',
  autoscout24: 'text-[#f97316]',
  motor:       'text-[#8b5cf6]',
}

/* ── ListingCard ──────────────────────────────────────────────────────────── */

interface ListingCardProps {
  listing: Listing & { roi_redacted?: boolean }
  onClick?: () => void
  className?: string
}

export function ListingCard({ listing, onClick, className }: ListingCardProps) {
  const carName = [listing.brand, listing.model].filter(Boolean).join(' ') || 'Sin modelo'
  const portalClass = portalColor[listing.portal?.toLowerCase() ?? ''] ?? 'text-muted-foreground'

  return (
    <article
      className={cn(
        'group relative flex flex-col rounded-xl border border-border bg-surface',
        'transition-all duration-200 cursor-pointer overflow-hidden',
        'hover:border-primary/40 hover:shadow-card-hover hover:-translate-y-0.5',
        onClick && 'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background',
        className,
      )}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === 'Enter') onClick?.() }}
      role={onClick ? 'button' : 'article'}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Photo strip */}
      <div className="relative h-32 bg-muted overflow-hidden flex-shrink-0">
        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-surface/80 to-transparent z-10" />

        {/* Car icon placeholder */}
        <div className="absolute inset-0 flex items-center justify-center text-border">
          <Car className="h-12 w-12" strokeWidth={1} />
        </div>

        {/* Image count badge */}
        {(listing.images_count ?? 0) > 0 && (
          <span className="absolute bottom-2 right-2 z-20 text-caption text-muted-foreground bg-background/60 px-1.5 py-0.5 rounded">
            {listing.images_count} fotos
          </span>
        )}

        {/* ROI badge (top right) */}
        <div className="absolute top-2 right-2 z-20">
          <ROIBadge roi={listing.roi_neto} redacted={listing.roi_redacted} />
        </div>

        {/* Portal tag (top left) */}
        <span className={cn('absolute top-2 left-2 z-20 text-caption font-semibold', portalClass)}>
          {listing.portal ?? 'portal'}
        </span>
      </div>

      {/* Body */}
      <div className="flex flex-col gap-3 p-4 flex-1">
        {/* Title row */}
        <div className="min-w-0">
          <p className="text-body font-semibold text-foreground truncate">{carName}</p>
          <p className="text-caption text-muted-foreground">
            {[
              listing.year,
              listing.mileage != null ? `${formatInteger(listing.mileage)} km` : null,
              listing.seller_type,
            ].filter(Boolean).join(' · ')}
          </p>
        </div>

        {/* Divider */}
        <div className="h-px bg-border" />

        {/* Price row */}
        <div className="grid grid-cols-3 gap-1 items-end">
          <div>
            <p className="text-caption text-muted-foreground mb-0.5">Pedido</p>
            <p className="text-body font-semibold text-foreground">
              {formatCurrency(listing.price)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-caption text-muted-foreground mb-0.5">Mercado</p>
            <p className="text-body font-medium text-foreground">
              {formatCurrency(listing.market_price)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-caption text-muted-foreground mb-0.5">ROI neto</p>
            <ROIValue roi={listing.roi_neto} redacted={listing.roi_redacted} />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-auto">
          <span className="text-caption text-muted-foreground">
            {timeAgo(listing.scraped_at)}
          </span>
          <div className="flex items-center gap-1.5">
            {listing.url && (
              <a
                className="text-caption text-muted-foreground hover:text-foreground transition-colors p-1 rounded"
                href={listing.url}
                onClick={(e) => e.stopPropagation()}
                rel="noopener noreferrer"
                target="_blank"
                title="Ver anuncio original"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
            <span className={cn(
              'flex items-center gap-1 text-caption font-medium',
              'text-muted-foreground group-hover:text-primary transition-colors duration-150',
            )}>
              Ver
              <ArrowRight className="h-3 w-3 transition-transform duration-150 group-hover:translate-x-0.5" />
            </span>
          </div>
        </div>
      </div>
    </article>
  )
}

/* ── ROI Badge ────────────────────────────────────────────────────────────── */

function ROIBadge({ roi, redacted }: { roi: number | null; redacted?: boolean }) {
  const tier = roiTier(roi, redacted)

  if (tier === 'redacted') {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-caption font-semibold bg-surface-elevated border-border text-muted-foreground">
        <Lock className="h-2.5 w-2.5" />
        Upgrade
      </span>
    )
  }

  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-caption font-semibold',
      tierStyles[tier],
    )}>
      {tier !== 'low' && <TrendingUp className="h-2.5 w-2.5" />}
      {roi != null ? `+${formatROI(roi)}` : '-'}
    </span>
  )
}

/* ── ROI Value (in price row) ─────────────────────────────────────────────── */

function ROIValue({ roi, redacted }: { roi: number | null; redacted?: boolean }) {
  const tier = roiTier(roi, redacted)

  if (tier === 'redacted') {
    return (
      <p className="text-body font-semibold text-muted-foreground flex items-center justify-end gap-1">
        <Lock className="h-3 w-3" />
        —
      </p>
    )
  }

  const colorClass =
    tier === 'high' ? 'text-accent' :
    tier === 'mid'  ? 'text-warning' :
    'text-muted-foreground'

  return (
    <p className={cn('text-body font-bold', colorClass)}>
      {roi != null ? `+${formatROI(roi)}` : '-'}
    </p>
  )
}

/* ── ListingCardSkeleton ──────────────────────────────────────────────────── */

export function ListingCardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('rounded-xl border border-border bg-surface overflow-hidden', className)}>
      {/* Photo strip */}
      <Skeleton className="h-32 rounded-none" />

      {/* Body */}
      <div className="p-4 flex flex-col gap-3">
        <div className="space-y-1.5">
          <Skeleton className="h-4 w-3/4 rounded" />
          <Skeleton className="h-3 w-1/2 rounded" />
        </div>
        <div className="h-px bg-border" />
        <div className="grid grid-cols-3 gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-1">
              <Skeleton className="h-2.5 w-full rounded" />
              <Skeleton className="h-4 w-4/5 rounded" />
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <Skeleton className="h-3 w-16 rounded" />
          <Skeleton className="h-3 w-12 rounded" />
        </div>
      </div>
    </div>
  )
}

/* ── ListingCardGrid ──────────────────────────────────────────────────────── */

export function ListingCardGrid({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn(
      'grid gap-4',
      'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
      className,
    )}>
      {children}
    </div>
  )
}
