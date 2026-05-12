import { AlertCircle, CheckCircle2, Info, X, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { type ToastVariant, useToastStore } from '@/hooks/useToast'
import { cn } from '@/lib/utils'

const variantConfig: Record<ToastVariant, {
  icon: ReactNode
  containerClass: string
  iconClass: string
}> = {
  success: {
    icon: <CheckCircle2 className="h-4 w-4" />,
    containerClass: 'border-accent/30 bg-surface',
    iconClass: 'text-accent',
  },
  error: {
    icon: <XCircle className="h-4 w-4" />,
    containerClass: 'border-destructive/30 bg-surface',
    iconClass: 'text-destructive',
  },
  warning: {
    icon: <AlertCircle className="h-4 w-4" />,
    containerClass: 'border-warning/30 bg-surface',
    iconClass: 'text-warning',
  },
  info: {
    icon: <Info className="h-4 w-4" />,
    containerClass: 'border-primary/30 bg-surface',
    iconClass: 'text-primary',
  },
}

export function ToastContainer() {
  const { toasts, dismiss } = useToastStore()

  return createPortal(
    <div
      aria-live="polite"
      aria-atomic="false"
      className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 w-[360px] max-w-[calc(100vw-2rem)]"
    >
      {toasts.map((t) => {
        const cfg = variantConfig[t.variant]
        return (
          <div
            key={t.id}
            className={cn(
              'relative flex items-start gap-3 rounded-xl border px-4 py-3.5 shadow-modal',
              'animate-slide-up',
              cfg.containerClass,
            )}
            role="alert"
          >
            <span className={cn('mt-0.5 flex-shrink-0', cfg.iconClass)}>
              {cfg.icon}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-body font-semibold text-foreground leading-tight">{t.title}</p>
              {t.description && (
                <p className="text-caption text-muted-foreground mt-0.5">{t.description}</p>
              )}
            </div>
            <button
              aria-label="Cerrar notificación"
              className="flex-shrink-0 mt-0.5 rounded p-0.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              onClick={() => dismiss(t.id)}
              type="button"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )
      })}
    </div>,
    document.body,
  )
}
