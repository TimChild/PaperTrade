import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
import { CompositionOverTimeChart } from '@/components/features/analytics/CompositionOverTimeChart'
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

describe('CompositionOverTimeChart', () => {
  it('renders loading state', () => {
    const Wrapper = createWrapper()
    render(<CompositionOverTimeChart portfolioId="test-id" />, {
      wrapper: Wrapper,
    })

    expect(
      screen.getByTestId('composition-over-time-chart-loading')
    ).toBeInTheDocument()
  })

  it('renders error state', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockRejectedValue(
      new Error('Failed to fetch')
    )

    const Wrapper = createWrapper()
    render(<CompositionOverTimeChart portfolioId="test-id" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(
        screen.getByTestId('composition-over-time-chart-error')
      ).toBeInTheDocument()
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
    render(<CompositionOverTimeChart portfolioId="test-id" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(
        screen.getByTestId('composition-over-time-chart-empty')
      ).toBeInTheDocument()
    })
  })

  it('renders stacked area chart with full breakdown data', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [
        {
          date: '2026-01-20',
          total_value: 10500,
          cash_balance: 2000,
          holdings_value: 8500,
          holdings_breakdown: [
            { ticker: 'AAPL', quantity: 10, price_per_share: 250, value: 2500 },
            {
              ticker: 'MSFT',
              quantity: 15,
              price_per_share: 400,
              value: 6000,
            },
          ],
        },
        {
          date: '2026-01-21',
          total_value: 11000,
          cash_balance: 1500,
          holdings_value: 9500,
          holdings_breakdown: [
            { ticker: 'AAPL', quantity: 10, price_per_share: 260, value: 2600 },
            {
              ticker: 'MSFT',
              quantity: 15,
              price_per_share: 460,
              value: 6900,
            },
          ],
        },
      ],
      metrics: null,
    })

    const Wrapper = createWrapper()
    render(<CompositionOverTimeChart portfolioId="test-id" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(
        screen.getByTestId('composition-over-time-chart')
      ).toBeInTheDocument()
    })
  })

  it('renders chart with empty breakdown (fallback to aggregate holdings)', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [
        {
          date: '2026-01-20',
          total_value: 10500,
          cash_balance: 2000,
          holdings_value: 8500,
          holdings_breakdown: [],
        },
        {
          date: '2026-01-21',
          total_value: 11000,
          cash_balance: 1500,
          holdings_value: 9500,
          holdings_breakdown: [],
        },
      ],
      metrics: null,
    })

    const Wrapper = createWrapper()
    render(<CompositionOverTimeChart portfolioId="test-id" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(
        screen.getByTestId('composition-over-time-chart')
      ).toBeInTheDocument()
    })
  })

  it('displays all time range buttons', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [
        {
          date: '2026-01-20',
          total_value: 10500,
          cash_balance: 2000,
          holdings_value: 8500,
          holdings_breakdown: [],
        },
      ],
      metrics: null,
    })

    const Wrapper = createWrapper()
    render(<CompositionOverTimeChart portfolioId="test-id" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(screen.getByTestId('composition-range-1W')).toBeInTheDocument()
      expect(screen.getByTestId('composition-range-1M')).toBeInTheDocument()
      expect(screen.getByTestId('composition-range-3M')).toBeInTheDocument()
      expect(screen.getByTestId('composition-range-1Y')).toBeInTheDocument()
      expect(screen.getByTestId('composition-range-ALL')).toBeInTheDocument()
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
            date: '2026-01-20',
            total_value: 10500,
            cash_balance: 2000,
            holdings_value: 8500,
            holdings_breakdown: [],
          },
        ],
        metrics: null,
      })

    const Wrapper = createWrapper()
    const user = userEvent.setup()
    render(<CompositionOverTimeChart portfolioId="test-id" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(screen.getByTestId('composition-range-1W')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('composition-range-1W'))

    await waitFor(() => {
      expect(mockGetPerformance).toHaveBeenCalledWith('test-id', '1W')
    })
  })

  it('handles tickers that appear and disappear over time', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [
        {
          date: '2026-01-20',
          total_value: 10500,
          cash_balance: 2000,
          holdings_value: 8500,
          holdings_breakdown: [
            { ticker: 'AAPL', quantity: 10, price_per_share: 250, value: 2500 },
            {
              ticker: 'MSFT',
              quantity: 15,
              price_per_share: 400,
              value: 6000,
            },
          ],
        },
        {
          // MSFT was sold
          date: '2026-01-21',
          total_value: 8000,
          cash_balance: 5500,
          holdings_value: 2500,
          holdings_breakdown: [
            { ticker: 'AAPL', quantity: 10, price_per_share: 250, value: 2500 },
          ],
        },
      ],
      metrics: null,
    })

    const Wrapper = createWrapper()
    render(<CompositionOverTimeChart portfolioId="test-id" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(
        screen.getByTestId('composition-over-time-chart')
      ).toBeInTheDocument()
    })
  })
})
