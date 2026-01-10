/**
 * Tests for ThemeContext
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ThemeProvider, useTheme } from '../ThemeContext'

// Test component that uses the theme context
function TestComponent() {
  const { theme, setTheme, effectiveTheme } = useTheme()
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="effective-theme">{effectiveTheme}</span>
      <button onClick={() => setTheme('dark')} data-testid="set-dark">
        Dark
      </button>
      <button onClick={() => setTheme('light')} data-testid="set-light">
        Light
      </button>
      <button onClick={() => setTheme('system')} data-testid="set-system">
        System
      </button>
    </div>
  )
}

describe('ThemeContext', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    // Clear document classes
    document.documentElement.classList.remove('light', 'dark')
    
    // Reset matchMedia mock to default (light mode)
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  it('defaults to system theme when no stored preference exists', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )
    expect(screen.getByTestId('theme')).toHaveTextContent('system')
  })

  it('loads stored theme preference from localStorage', () => {
    localStorage.setItem('theme', 'dark')
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )
    expect(screen.getByTestId('theme')).toHaveTextContent('dark')
    expect(screen.getByTestId('effective-theme')).toHaveTextContent('dark')
  })

  it('persists theme choice to localStorage', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )
    fireEvent.click(screen.getByTestId('set-dark'))
    expect(localStorage.getItem('theme')).toBe('dark')
  })

  it('applies dark class to document when dark theme is selected', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )
    fireEvent.click(screen.getByTestId('set-dark'))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })

  it('applies light class to document when light theme is selected', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )
    fireEvent.click(screen.getByTestId('set-light'))
    expect(document.documentElement.classList.contains('light')).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('switches between themes correctly', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )
    
    // Start with system
    expect(screen.getByTestId('theme')).toHaveTextContent('system')
    
    // Switch to dark
    fireEvent.click(screen.getByTestId('set-dark'))
    expect(screen.getByTestId('theme')).toHaveTextContent('dark')
    expect(screen.getByTestId('effective-theme')).toHaveTextContent('dark')
    
    // Switch to light
    fireEvent.click(screen.getByTestId('set-light'))
    expect(screen.getByTestId('theme')).toHaveTextContent('light')
    expect(screen.getByTestId('effective-theme')).toHaveTextContent('light')
    
    // Switch back to system
    fireEvent.click(screen.getByTestId('set-system'))
    expect(screen.getByTestId('theme')).toHaveTextContent('system')
  })

  it('resolves system theme based on media query', () => {
    // Mock matchMedia to return dark mode
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )
    
    // Should default to system
    expect(screen.getByTestId('theme')).toHaveTextContent('system')
    // Should resolve to dark based on media query
    expect(screen.getByTestId('effective-theme')).toHaveTextContent('dark')
  })

  it('throws error when useTheme is used outside ThemeProvider', () => {
    // Suppress console.error for this test
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    expect(() => {
      render(<TestComponent />)
    }).toThrow('useTheme must be used within ThemeProvider')
    
    consoleError.mockRestore()
  })

  it('registers listener for system preference changes', () => {
    // Create a mock to capture addEventListener calls
    const addEventListenerMock = vi.fn()
    
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: false, // Start with light
        media: query,
        addEventListener: addEventListenerMock,
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )
    
    // Should start with system/light
    expect(screen.getByTestId('theme')).toHaveTextContent('system')
    expect(screen.getByTestId('effective-theme')).toHaveTextContent('light')
    
    // Verify that we registered a listener for media query changes
    expect(addEventListenerMock).toHaveBeenCalledWith(
      'change',
      expect.any(Function)
    )
  })
})
