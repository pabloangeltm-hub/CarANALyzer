import {
  Bell,
  Bookmark,
  Car,
  ChevronLeft,
  ChevronRight,
  Command,
  LineChart,
  LogOut,
  Menu,
  X,
  Zap,
} from 'lucide-react'
import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/layout/ThemeToggle'
import { useLogout } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

const SIDEBAR_KEY = 'agartha:sidebar-collapsed'

const navItems = [
  { href: '/', label: 'Dashboard', icon: Car, exact: true },
  { href: '/market', label: 'Mercado', icon: LineChart, exact: false },
  { href: '/alerts', label: 'Alertas', icon: Bell, exact: false },
  { href: '/saved-searches', label: 'Búsquedas', icon: Bookmark, exact: false },
]

function readCollapsed() {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === 'true'
  } catch {
    return false
  }
}

export function AppLayout({
  children,
  subtitle,
  title,
}: {
  children: ReactNode
  subtitle?: string
  title: string
}) {
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const [mobileOpen, setMobileOpen] = useState(false)
  const logoutMutation = useLogout()
  const navigate = useNavigate()
  const mainRef = useRef<HTMLElement>(null)

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev
      try { localStorage.setItem(SIDEBAR_KEY, String(next)) } catch {}
      return next
    })
  }, [])

  /* Close mobile drawer on route change */
  useEffect(() => {
    setMobileOpen(false)
  }, [title])

  /* Page entrance animation */
  useEffect(() => {
    const el = mainRef.current
    if (!el) return
    el.classList.remove('page-enter')
    void el.offsetWidth
    el.classList.add('page-enter')
  }, [title])

  async function handleLogout() {
    await logoutMutation.mutateAsync()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">

      {/* ── Desktop sidebar ─────────────────────────────────────────────── */}
      <aside
        className={cn(
          'hidden lg:flex flex-col flex-shrink-0 border-r border-border bg-surface',
          'transition-[width] duration-250 ease-in-out overflow-hidden',
        )}
        style={{ width: collapsed ? 64 : 240 }}
      >
        {/* Brand */}
        <div
          className={cn(
            'flex items-center h-14 px-4 border-b border-border flex-shrink-0',
            collapsed ? 'justify-center' : 'gap-3',
          )}
        >
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary">
            <Zap className="h-4 w-4 text-primary-foreground" strokeWidth={2.5} />
          </div>
          {!collapsed && (
            <div className="min-w-0 overflow-hidden">
              <p className="text-[13px] font-semibold text-foreground truncate">Agartha</p>
              <p className="text-[11px] text-muted-foreground truncate">Dealer Intelligence</p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto overflow-x-hidden">
          {navItems.map((item) => (
            <SidebarItem key={item.href} item={item} collapsed={collapsed} />
          ))}
        </nav>

        {/* Collapse toggle */}
        <div className={cn('p-2 border-t border-border', collapsed ? 'flex justify-center' : '')}>
          <button
            aria-label={collapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
            className={cn(
              'flex items-center gap-2 rounded-md px-2 py-2 text-muted-foreground',
              'hover:bg-muted hover:text-foreground transition-colors duration-150',
              'text-caption w-full',
              collapsed ? 'justify-center' : '',
            )}
            onClick={toggleCollapsed}
            type="button"
          >
            {collapsed
              ? <ChevronRight className="h-4 w-4 flex-shrink-0" />
              : (
                <>
                  <ChevronLeft className="h-4 w-4 flex-shrink-0" />
                  <span className="truncate">Colapsar</span>
                </>
              )
            }
          </button>
        </div>
      </aside>

      {/* ── Mobile drawer ────────────────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-50 flex lg:hidden"
          onClick={() => setMobileOpen(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm animate-fade-in" />

          {/* Panel */}
          <aside
            className="relative z-10 flex flex-col w-[240px] h-full bg-surface border-r border-border animate-slide-down"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Brand */}
            <div className="flex items-center justify-between h-14 px-4 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                  <Zap className="h-4 w-4 text-primary-foreground" strokeWidth={2.5} />
                </div>
                <div>
                  <p className="text-[13px] font-semibold">Agartha</p>
                  <p className="text-[11px] text-muted-foreground">Dealer Intelligence</p>
                </div>
              </div>
              <button
                aria-label="Cerrar menú"
                className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                onClick={() => setMobileOpen(false)}
                type="button"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Nav */}
            <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto">
              {navItems.map((item) => (
                <SidebarItem
                  key={item.href}
                  item={item}
                  collapsed={false}
                  onNavigate={() => setMobileOpen(false)}
                />
              ))}
            </nav>
          </aside>
        </div>
      )}

      {/* ── Main area ────────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">

        {/* Top bar */}
        <header className="flex h-14 flex-shrink-0 items-center gap-3 border-b border-border bg-surface px-4">

          {/* Mobile burger */}
          <button
            aria-label="Abrir menú"
            className={cn(
              'lg:hidden rounded-md p-1.5 text-muted-foreground',
              'hover:bg-muted hover:text-foreground transition-colors duration-150',
            )}
            onClick={() => setMobileOpen(true)}
            type="button"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Page title */}
          <div className="flex-1 min-w-0">
            <h1 className="truncate text-[15px] font-semibold text-foreground">{title}</h1>
            {subtitle && (
              <p className="truncate text-caption text-muted-foreground">{subtitle}</p>
            )}
          </div>

          {/* Global search hint */}
          <button
            aria-label="Buscar (⌘K)"
            className={cn(
              'hidden sm:flex items-center gap-2 rounded-md border border-border bg-muted/50',
              'px-3 py-1.5 text-caption text-muted-foreground',
              'hover:border-primary/40 hover:text-foreground transition-all duration-150',
              'min-w-[140px]',
            )}
            type="button"
          >
            <Command className="h-3 w-3 flex-shrink-0" />
            <span className="flex-1 text-left">Buscar...</span>
            <kbd className="text-[10px] font-medium opacity-60 flex-shrink-0">⌘K</kbd>
          </button>

          {/* Notifications */}
          <button
            aria-label="Notificaciones"
            className="relative rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors duration-150"
            type="button"
          >
            <Bell className="h-5 w-5" />
            {/* Unread dot */}
            <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-accent" />
          </button>

          {/* Theme toggle */}
          <ThemeToggle />

          {/* Logout */}
          <Button
            aria-label="Cerrar sesión"
            disabled={logoutMutation.isPending}
            onClick={handleLogout}
            size="icon"
            type="button"
            variant="ghost"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </header>

        {/* Page content */}
        <main
          ref={mainRef}
          className="flex-1 overflow-y-auto overflow-x-hidden"
        >
          <div className="p-4 sm:p-6 space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

/* ── Sidebar nav item ─────────────────────────────────────────────────────── */
function SidebarItem({
  collapsed,
  item,
  onNavigate,
}: {
  collapsed: boolean
  item: (typeof navItems)[number]
  onNavigate?: () => void
}) {
  const Icon = item.icon
  return (
    <NavLink
      end={item.exact}
      to={item.href}
      onClick={onNavigate}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2.5 rounded-md transition-colors duration-150',
          'text-[13px] font-medium text-muted-foreground',
          'hover:bg-muted hover:text-foreground',
          isActive && 'bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary',
          collapsed ? 'px-0 py-2.5 justify-center' : 'px-3 py-2',
        )
      }
    >
      <Icon className="h-[18px] w-[18px] flex-shrink-0" strokeWidth={1.75} />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  )
}
