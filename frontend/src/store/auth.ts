import { create } from 'zustand'

import { AUTH_CHANGED_EVENT, hasAuthTokens } from '@/api/client'

interface AuthState {
  isAuthenticated: boolean
  markAuthenticated: () => void
  markAnonymous: () => void
  syncFromStorage: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: hasAuthTokens(),
  markAuthenticated: () => set({ isAuthenticated: true }),
  markAnonymous: () => set({ isAuthenticated: false }),
  syncFromStorage: () => set({ isAuthenticated: hasAuthTokens() }),
}))

if (typeof window !== 'undefined') {
  window.addEventListener(AUTH_CHANGED_EVENT, () => {
    useAuthStore.getState().syncFromStorage()
  })
}
