import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CompositionChart } from '@/components/features/analytics/CompositionChart'
import * as analyticsApi from '@/services/api/analytics'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('CompositionChart', () => {
  it('renders loading state', () => {
    const Wrapper = createWrapper()
    render(<CompositionChart portfolioId="test-id" />, { wrapper: Wrapper })

    expect(screen.getByTestId('composition-chart-loading')).toBeInTheDocument()
  })

  it('renders error state', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getComposition').mockRejectedValue(
      new Error('Failed to fetch')
    )

    const Wrapper = createWrapper()
    render(<CompositionChart portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('composition-chart-error')).toBeInTheDocument()
    })
  })

  it('renders empty state when no holdings', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getComposition').mockResolvedValue({
      portfolio_id: 'test-id',
      total_value: 0,
      composition: [],
    })

    const Wrapper = createWrapper()
    render(<CompositionChart portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('composition-chart-empty')).toBeInTheDocument()
    })
  })

  it('renders pie chart with holdings data', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getComposition').mockResolvedValue({
      portfolio_id: 'test-id',
      total_value: 12500,
      composition: [
        {
          ticker: 'IBM',
          value: 5500,
          percentage: 44.0,
          quantity: 30,
        },
        {
          ticker: 'AAPL',
          value: 4000,
          percentage: 32.0,
          quantity: 20,
        },
        {
          ticker: 'CASH',
          value: 3000,
          percentage: 24.0,
          quantity: null,
        },
      ],
    })

    const Wrapper = createWrapper()
    render(<CompositionChart portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('composition-chart')).toBeInTheDocument()
    })
  })
})
