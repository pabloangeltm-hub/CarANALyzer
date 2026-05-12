import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'

export function LoadingState({
  className,
  text = 'Cargando...',
}: {
  className?: string
  text?: string
}) {
  return (
    <div
      className={cn(
        'flex min-h-40 items-center justify-center gap-2 text-sm text-muted-foreground',
        className,
      )}
    >
      <Loader2 className="h-4 w-4 animate-spin" />
      {text}
    </div>
  )
}
