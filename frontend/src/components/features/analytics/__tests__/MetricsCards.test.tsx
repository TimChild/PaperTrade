import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MetricsCards } from '@/components/features/analytics/MetricsCards'
import * as analyticsApi from '@/services/api/analytics'
import { portfoliosApi } from '@/services/api/portfolios'

vi.mock('@/services/api/portfolios', () => ({
  portfoliosApi: {
    getBalance: vi.fn(),
  },
}))

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

/**
 * Build a fully-formed BalanceResponse with sensible defaults so individual
 * tests only need to override the fields they care about. Mirrors the wire
 * shape from `BalanceResponse` in `services/api/types.ts`.
 */
function balanceResponse(overrides: {
  total_value?: string
  cash_balance?: string
  holdings_value?: string
  daily_change?: string
  daily_change_percent?: string
}) {
  return {
    cash_balance: overrides.cash_balance ?? '0.00',
    holdings_value: overrides.holdings_value ?? '0.00',
    total_value: overrides.total_value ?? '0.00',
    currency: 'USD',
    as_of: '2026-05-09T15:30:00Z',
    daily_change: overrides.daily_change ?? '0.00',
    daily_change_percent: overrides.daily_change_percent ?? '0.00',
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  // Default: live balance equals last snapshot's ending_value so existing
  // tests behave the same as before the fix unless they explicitly set up
  // a divergence.
  vi.mocked(portfoliosApi.getBalance).mockResolvedValue(
    balanceResponse({ total_value: '12500.00' })
  )
})

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

  it('shows positive gains in the editorial gain tone', async () => {
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
      // Editorial muted gain tone. Was `.text-green-600` pre-revamp.
      const gainCard = screen.getByTestId('metric-total-gain-loss')
      const valueElement = gainCard.querySelector('.text-gain')
      expect(valueElement).toBeInTheDocument()
    })
  })

  it('shows negative gains in the editorial loss tone', async () => {
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
    vi.mocked(portfoliosApi.getBalance).mockResolvedValue(
      balanceResponse({ total_value: '8500.00' })
    )

    const Wrapper = createWrapper()
    render(<MetricsCards portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      // Editorial muted loss tone. Was `.text-red-600` pre-revamp.
      const gainCard = screen.getByTestId('metric-total-gain-loss')
      const valueElement = gainCard.querySelector('.text-loss')
      expect(valueElement).toBeInTheDocument()
    })

    // Should show negative sign
    await waitFor(() => {
      expect(screen.getByText('-$1,500.00')).toBeInTheDocument()
    })
  })

  it('renders error state when API call fails', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockRejectedValue(
      new Error('API Error')
    )

    const Wrapper = createWrapper()
    render(<MetricsCards portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('metrics-cards-error')).toBeInTheDocument()
      expect(
        screen.getByText(/Failed to load performance metrics/)
      ).toBeInTheDocument()
    })
  })

  it('renders empty state when metrics is null', async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [],
      metrics: null,
    })

    const Wrapper = createWrapper()
    render(<MetricsCards portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('metrics-cards-empty')).toBeInTheDocument()
      expect(
        screen.getByText(/No performance data available yet/)
      ).toBeInTheDocument()
    })
  })

  // Regression: detail card and analytics MUST agree on "current value".
  // Before this fix the analytics view rendered the last snapshot's
  // ending_value (e.g. $9,745.35), while the portfolio detail card rendered
  // the live total — which diverges when prices have moved since the most
  // recent snapshot.
  it("'Current Value' uses the live balance, not the snapshot ending_value", async () => {
    vi.spyOn(analyticsApi.analyticsApi, 'getPerformance').mockResolvedValue({
      portfolio_id: 'test-id',
      range: '1M',
      data_points: [],
      metrics: {
        starting_value: 10000,
        ending_value: 9745.35, // Last snapshot — stale
        absolute_gain: -254.65,
        percentage_gain: -2.55,
        highest_value: 10500,
        lowest_value: 9745.35,
      },
    })
    vi.mocked(portfoliosApi.getBalance).mockResolvedValue(
      balanceResponse({ total_value: '11676.69' }) // Live — what the detail card shows
    )

    const Wrapper = createWrapper()
    render(<MetricsCards portfolioId="test-id" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('metric-current-value')).toHaveTextContent(
        '$11,676.69'
      )
    })

    // Total gain/loss is recomputed from the live current value, NOT the
    // stale snapshot. 11676.69 - 10000 = 1676.69
    expect(screen.getByTestId('metric-total-gain-loss')).toHaveTextContent(
      '$1,676.69'
    )

    // Highest stretches to include the live value when it exceeds the
    // snapshot peak — keeps the row consistent with current-value.
    expect(screen.getByTestId('metric-highest-value')).toHaveTextContent(
      '$11,676.69'
    )

    // Starting value remains the snapshot baseline (period start).
    expect(screen.getByTestId('metric-starting-value')).toHaveTextContent(
      '$10,000.00'
    )
  })
})
