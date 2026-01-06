import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
import { PerformanceChart } from '@/components/features/analytics/PerformanceChart'
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

describe('PerformanceChart', () => {
  it('renders loading state', () => {
    const Wrapper = createWrapper()
    render(<PerformanceChart portfolioId="test-id" />, { wrapper: Wrapper })

    expect(screen.getByTestId('performance-chart-loading')).toBeInTheDocument()
  })

  it('renders error state', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockRejectedValue(
      new Error('Failed to fetch')
    )

    const Wrapper = createWrapper()
    render(<PerformanceChart portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('performance-chart-error')).toBeInTheDocument()
    })
  })

  it('renders empty state when no data points', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [],
      metrics: null,
    })

    const Wrapper = createWrapper()
    render(<PerformanceChart portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('performance-chart-empty')).toBeInTheDocument()
    })
  })

  it('renders chart with data', async () => {
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
        {
          date: '2026-01-02',
          total_value: 10500,
          cash_balance: 5000,
          holdings_value: 5500,
        },
      ],
      metrics: {
        starting_value: 10000,
        ending_value: 10500,
        absolute_gain: 500,
        percentage_gain: 5.0,
        highest_value: 10500,
        lowest_value: 10000,
      },
    })

    const Wrapper = createWrapper()
    render(<PerformanceChart portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('performance-chart')).toBeInTheDocument()
    })
  })

  it('displays all time range buttons', async () => {
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
      metrics: null,
    })

    const Wrapper = createWrapper()
    render(<PerformanceChart portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('range-1W')).toBeInTheDocument()
      expect(screen.getByTestId('range-1M')).toBeInTheDocument()
      expect(screen.getByTestId('range-3M')).toBeInTheDocument()
      expect(screen.getByTestId('range-1Y')).toBeInTheDocument()
      expect(screen.getByTestId('range-ALL')).toBeInTheDocument()
    })
  })

  it('changes time range when button clicked', async () => {
    const mockGetPerformance = vi
      .spyOn(analyticsApi.analyticsApi, 'getPerformance')
      .mockResolvedValue({
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
        metrics: null,
      })

    const Wrapper = createWrapper()
    const user = userEvent.setup()
    render(<PerformanceChart portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('range-1W')).toBeInTheDocument()
    })

    // Click 1W button
    await user.click(screen.getByTestId('range-1W'))

    // Should call API with new range
    await waitFor(() => {
      expect(mockGetPerformance).toHaveBeenCalledWith('test-id', '1W')
    })
  })
})
