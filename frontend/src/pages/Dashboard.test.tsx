import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { Dashboard } from './Dashboard'

// Create a test query client
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
}

// Helper to render with all required providers
function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('Dashboard', () => {
  describe('Accessibility', () => {
    it('should have no accessibility violations', async () => {
      const { axe } = await import('jest-axe')
      const { container } = renderWithProviders(<Dashboard />)
      
      // Wait a bit for any async rendering
      await new Promise((resolve) => setTimeout(resolve, 100))
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })
})
