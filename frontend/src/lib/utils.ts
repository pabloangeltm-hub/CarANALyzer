import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const currencyFormatter = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 0,
})

export function formatCurrency(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '-'
  }
  return currencyFormatter.format(value)
}

export function formatROI(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '-'
  }
  return `${value.toFixed(1)}%`
}

export function formatInteger(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '-'
  }
  return new Intl.NumberFormat('es-ES', {
    maximumFractionDigits: 0,
  }).format(value)
}
