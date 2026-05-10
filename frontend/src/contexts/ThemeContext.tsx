import { createContext, useContext, useEffect, useState } from 'react'

type Theme = 'light' | 'dark' | 'system'

type ThemeContextType = {
  theme: Theme
  setTheme: (theme: Theme) => void
  effectiveTheme: 'light' | 'dark' // Resolved theme (system → light/dark)
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

// Helper to get system preference
function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export function ThemeProvider({
  children,
}: {
  children: React.ReactNode
}): React.JSX.Element {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Zebu is dark-only by design (Tim, 2026-05-09). We still respect a
    // pre-existing localStorage value (someone may have explicitly chosen
    // 'system' or 'light' previously) but default new users to 'dark'.
    const stored = localStorage.getItem('theme') as Theme | null
    return stored || 'dark'
  })

  // Track system preference separately
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(
    getSystemTheme
  )

  // Derive effective theme from theme and systemTheme
  const effectiveTheme = theme === 'system' ? systemTheme : theme

  useEffect(() => {
    // Only listen to system theme changes when theme is 'system'
    if (theme !== 'system') {
      return
    }

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const updateSystemTheme = () => {
      setSystemTheme(mediaQuery.matches ? 'dark' : 'light')
    }

    // Listen for system theme changes
    mediaQuery.addEventListener('change', updateSystemTheme)
    return () => mediaQuery.removeEventListener('change', updateSystemTheme)
  }, [theme])

  useEffect(() => {
    // Apply theme to document
    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(effectiveTheme)
  }, [effectiveTheme])

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem('theme', newTheme)
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme, effectiveTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}
