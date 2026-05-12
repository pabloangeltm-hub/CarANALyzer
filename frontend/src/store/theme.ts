import { create } from 'zustand'

type Theme = 'light' | 'dark'

interface ThemeState {
  theme: Theme
  toggleTheme: () => void
}

const themeKey = 'agartha.theme'

function readTheme(): Theme {
  const stored = globalThis.localStorage?.getItem(themeKey)
  return stored === 'dark' ? 'dark' : 'light'
}

function applyTheme(theme: Theme) {
  globalThis.document?.documentElement.classList.toggle('dark', theme === 'dark')
  globalThis.localStorage?.setItem(themeKey, theme)
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: readTheme(),
  toggleTheme: () => {
    const nextTheme = get().theme === 'dark' ? 'light' : 'dark'
    applyTheme(nextTheme)
    set({ theme: nextTheme })
  },
}))

if (typeof window !== 'undefined') {
  applyTheme(readTheme())
}
