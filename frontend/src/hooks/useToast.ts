import { useCallback, useEffect, useRef, useState } from 'react'

export type ToastVariant = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  variant: ToastVariant
  title: string
  description?: string
  duration?: number
}

type ToastInput = Omit<Toast, 'id'>

/* ── Singleton event bus ──────────────────────────────────────────────────── */

type Listener = (toast: Toast) => void
const listeners: Set<Listener> = new Set()
let counter = 0

function emit(toast: Toast) {
  listeners.forEach((fn) => fn(toast))
}

export function toast(input: ToastInput) {
  emit({ ...input, id: String(++counter) })
}

toast.success = (title: string, description?: string) =>
  toast({ variant: 'success', title, description })

toast.error = (title: string, description?: string) =>
  toast({ variant: 'error', title, description })

toast.warning = (title: string, description?: string) =>
  toast({ variant: 'warning', title, description })

toast.info = (title: string, description?: string) =>
  toast({ variant: 'info', title, description })

/* ── useToastStore — used by ToastContainer ───────────────────────────────── */

export function useToastStore() {
  const [toasts, setToasts] = useState<Toast[]>([])
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  useEffect(() => {
    function onToast(t: Toast) {
      setToasts((prev) => [...prev, t])
      const duration = t.duration ?? 4000
      const timer = setTimeout(() => dismiss(t.id), duration)
      timers.current.set(t.id, timer)
    }
    listeners.add(onToast)
    return () => { listeners.delete(onToast) }
  }, [dismiss])

  /* cleanup timers on unmount */
  useEffect(() => {
    return () => { timers.current.forEach(clearTimeout) }
  }, [])

  return { toasts, dismiss }
}
