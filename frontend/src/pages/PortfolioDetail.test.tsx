import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { PortfolioDetail } from './PortfolioDetail'

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
function renderWithProviders(
  ui: React.ReactElement,
  { route = '/portfolio/1' } = {}
) {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/portfolio/:portfolioId" element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('PortfolioDetail', () => {
  describe('Accessibility', () => {
    it('should have no accessibility violations', async () => {
      const { axe } = await import('jest-axe')
      const { container } = renderWithProviders(<PortfolioDetail />)

      // Wait a bit for any async rendering
      await new Promise((resolve) => setTimeout(resolve, 100))

      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })
})
