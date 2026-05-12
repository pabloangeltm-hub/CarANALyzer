import type { ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ToastContainer } from '@/components/ui/toast'
import { Alerts } from '@/pages/Alerts'
import { Dashboard } from '@/pages/Dashboard'
import { Login } from '@/pages/Login'
import { Market } from '@/pages/Market'
import { Pricing } from '@/pages/Pricing'
import { SavedSearches } from '@/pages/SavedSearches'
import { useAuthStore } from '@/store/auth'

export default function App() {
  return (
    <ErrorBoundary>
      <ToastContainer />
      <Routes>
        <Route
          path="/"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/market"
          element={
            <RequireAuth>
              <Market />
            </RequireAuth>
          }
        />
        <Route
          path="/alerts"
          element={
            <RequireAuth>
              <Alerts />
            </RequireAuth>
          }
        />
        <Route
          path="/saved-searches"
          element={
            <RequireAuth>
              <SavedSearches />
            </RequireAuth>
          }
        />
        <Route path="/login" element={<Login />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ErrorBoundary>
  )
}

function RequireAuth({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}
