import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MetricsCards } from '@/components/features/analytics/MetricsCards'
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

describe('MetricsCards', () => {
  it('renders loading state', () => {
    const Wrapper = createWrapper()
    render(<MetricsCards portfolioId="test-id" />, { wrapper: Wrapper })

    expect(screen.getByTestId('metrics-cards-loading')).toBeInTheDocument()
  })

  it('renders all metric cards with positive gains', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [
        {
          date: '2026-01-01',
          total_value: 10000,
          cash_balance: 10000,
          holdings_value: 0,
        },
      ],
      metrics: {
        starting_value: 10000,
        ending_value: 12500,
        absolute_gain: 2500,
        percentage_gain: 25.0,
        highest_value: 12750,
        lowest_value: 9800,
      },
    })

    const Wrapper = createWrapper()
    render(<MetricsCards portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('metrics-cards')).toBeInTheDocument()
    })

    // Check all metrics are displayed
    expect(screen.getByTestId('metric-total-gain-loss')).toBeInTheDocument()
    expect(screen.getByTestId('metric-return')).toBeInTheDocument()
    expect(screen.getByTestId('metric-starting-value')).toBeInTheDocument()
    expect(screen.getByTestId('metric-current-value')).toBeInTheDocument()
    expect(screen.getByTestId('metric-highest-value')).toBeInTheDocument()
    expect(screen.getByTestId('metric-lowest-value')).toBeInTheDocument()

    // Check values
    expect(screen.getByText('$2,500.00')).toBeInTheDocument()
    expect(screen.getByText('$10,000.00')).toBeInTheDocument()
    expect(screen.getByText('$12,500.00')).toBeInTheDocument()
    expect(screen.getByText('$12,750.00')).toBeInTheDocument()
    expect(screen.getByText('$9,800.00')).toBeInTheDocument()
  })

  it('shows positive gains in green', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [],
      metrics: {
        starting_value: 10000,
        ending_value: 12500,
        absolute_gain: 2500,
        percentage_gain: 25.0,
        highest_value: 12750,
        lowest_value: 9800,
      },
    })

    const Wrapper = createWrapper()
    render(<MetricsCards portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      const gainCard = screen.getByTestId('metric-total-gain-loss')
      const valueElement = gainCard.querySelector('.text-green-600')
      expect(valueElement).toBeInTheDocument()
    })
  })

  it('shows negative gains in red', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [],
      metrics: {
        starting_value: 10000,
        ending_value: 8500,
        absolute_gain: -1500,
        percentage_gain: -15.0,
        highest_value: 10000,
        lowest_value: 8500,
      },
    })

    const Wrapper = createWrapper()
    render(<MetricsCards portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      const gainCard = screen.getByTestId('metric-total-gain-loss')
      const valueElement = gainCard.querySelector('.text-red-600')
      expect(valueElement).toBeInTheDocument()
    })

    // Should show negative sign
    await waitFor(() => {
      expect(screen.getByText('-$1,500.00')).toBeInTheDocument()
    })
  })
})
