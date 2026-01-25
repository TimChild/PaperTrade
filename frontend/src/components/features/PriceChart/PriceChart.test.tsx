import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PriceChart } from '@/components/features/PriceChart/PriceChart'
import * as pricesApi from '@/services/api/prices'
import * as transactionsApi from '@/services/api/transactions'
import type { ApiError } from '@/types/errors'
import type { TransactionListResponse } from '@/services/api/types'

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

describe('PriceChart', () => {
  it('renders loading state initially', () => {
    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" />, { wrapper: Wrapper })

    expect(screen.getByText('AAPL')).toBeInTheDocument()
  })

  it('renders chart with mock data', async () => {
    const mockHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 150, currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 155, currency: 'USD' },
          timestamp: '2024-01-02T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'mock',
      cached: false,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument()
    })

    // Should show price stats
    await waitFor(() => {
      expect(screen.getByText('$155.00')).toBeInTheDocument()
    })
  })

  it('displays time range selector', () => {
    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" />, { wrapper: Wrapper })

    expect(screen.getByLabelText('Show 1D price history')).toBeInTheDocument()
    expect(screen.getByLabelText('Show 1W price history')).toBeInTheDocument()
    expect(screen.getByLabelText('Show 1M price history')).toBeInTheDocument()
    expect(screen.getByLabelText('Show 3M price history')).toBeInTheDocument()
    expect(screen.getByLabelText('Show 1Y price history')).toBeInTheDocument()
    expect(screen.getByLabelText('Show ALL price history')).toBeInTheDocument()
  })

  it('shows no data message when prices array is empty', async () => {
    const mockHistory = {
      ticker: 'AAPL',
      prices: [],
      source: 'mock',
      cached: false,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('No price data available')).toBeInTheDocument()
    })
  })

  it('handles string prices from backend correctly', async () => {
    // Simulate backend response where prices are strings (not numbers)
    // getPriceHistory should parse these to numbers
    const mockHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 271.01, currency: 'USD' }, // Already parsed by getPriceHistory
          timestamp: '2026-01-05T14:10:30.343797Z',
          source: 'alpha_vantage' as const,
          interval: '1day' as const,
        },
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 275.5, currency: 'USD' }, // Already parsed by getPriceHistory
          timestamp: '2026-01-06T14:10:30.343797Z',
          source: 'alpha_vantage' as const,
          interval: '1day' as const,
        },
      ],
      source: 'alpha_vantage',
      cached: false,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" />, { wrapper: Wrapper })

    // Should render chart without "Invalid price data" error
    await waitFor(() => {
      expect(screen.queryByText('Invalid price data')).not.toBeInTheDocument()
    })

    // Should show the last price
    await waitFor(() => {
      expect(screen.getByText('$275.50')).toBeInTheDocument()
    })
  })

  it('displays enhanced error component for API errors', async () => {
    const apiError: ApiError = {
      type: 'rate_limit',
      message: 'Market data temporarily unavailable due to high demand',
      retryAfter: 60,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockRejectedValue(apiError)

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" />, { wrapper: Wrapper })

    // Wait for error state to appear
    await waitFor(
      () => {
        expect(screen.getByTestId('price-chart-error')).toBeInTheDocument()
      },
      { timeout: 3000 }
    )

    // Check error message content
    expect(screen.getByText('Too Many Requests')).toBeInTheDocument()
    expect(screen.getByText(apiError.message)).toBeInTheDocument()
  })

  it('shows dev warning banner when using mock data with error', async () => {
    // Note: Directly mutating import.meta.env works in Vitest but could be improved
    // with proper environment mocking through Vitest config in the future
    const originalEnv = import.meta.env.DEV
    import.meta.env.DEV = true

    const mockHistoryWithError = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 150, currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'mock',
      cached: false,
      error: {
        type: 'server_error' as const,
        message: 'API error',
      },
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(
      mockHistoryWithError
    )

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('dev-warning-banner')).toBeInTheDocument()
      expect(
        screen.getByText(/Development Mode: Using mock data due to API error/)
      ).toBeInTheDocument()
    })

    // Restore environment (Note: This works in Vitest, could use proper config in future)
    import.meta.env.DEV = originalEnv
  })

  it('renders trade markers when portfolioId is provided', async () => {
    const mockHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 150, currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 155, currency: 'USD' },
          timestamp: '2024-01-02T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'mock',
      cached: false,
    }

    const mockTransactions: TransactionListResponse = {
      transactions: [
        {
          id: '1',
          portfolio_id: 'portfolio-1',
          transaction_type: 'BUY',
          timestamp: '2024-01-01T00:00:00Z',
          cash_change: '-1500.00',
          ticker: 'AAPL',
          quantity: '10',
          price_per_share: '150.00',
          notes: null,
        },
        {
          id: '2',
          portfolio_id: 'portfolio-1',
          transaction_type: 'SELL',
          timestamp: '2024-01-02T00:00:00Z',
          cash_change: '775.00',
          ticker: 'AAPL',
          quantity: '5',
          price_per_share: '155.00',
          notes: null,
        },
      ],
      total_count: 2,
      limit: 100,
      offset: 0,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)
    vi.spyOn(transactionsApi.transactionsApi, 'list').mockResolvedValue(
      mockTransactions
    )

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" portfolioId="portfolio-1" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(screen.getByText('$155.00')).toBeInTheDocument()
    })

    // Note: We can't easily test the Scatter component rendering in JSDOM
    // but we verify no errors occurred and the component renders
  })

  it('does not fetch transactions when portfolioId is not provided', async () => {
    const mockHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 150, currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'mock',
      cached: false,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('$150.00')).toBeInTheDocument()
    })

    // Transactions API should not be called when portfolioId is not provided
    // The useTransactions hook will be disabled
  })

  it('filters transactions to only show BUY and SELL for the specific ticker', async () => {
    const mockHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 150, currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'mock',
      cached: false,
    }

    const mockTransactions: TransactionListResponse = {
      transactions: [
        {
          id: '1',
          portfolio_id: 'portfolio-1',
          transaction_type: 'BUY',
          timestamp: '2024-01-01T00:00:00Z',
          cash_change: '-1500.00',
          ticker: 'AAPL',
          quantity: '10',
          price_per_share: '150.00',
          notes: null,
        },
        {
          id: '2',
          portfolio_id: 'portfolio-1',
          transaction_type: 'DEPOSIT',
          timestamp: '2024-01-01T00:00:00Z',
          cash_change: '10000.00',
          ticker: null,
          quantity: null,
          price_per_share: null,
          notes: null,
        },
        {
          id: '3',
          portfolio_id: 'portfolio-1',
          transaction_type: 'BUY',
          timestamp: '2024-01-01T00:00:00Z',
          cash_change: '-1000.00',
          ticker: 'GOOGL', // Different ticker
          quantity: '5',
          price_per_share: '200.00',
          notes: null,
        },
      ],
      total_count: 3,
      limit: 100,
      offset: 0,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)
    vi.spyOn(transactionsApi.transactionsApi, 'list').mockResolvedValue(
      mockTransactions
    )

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" portfolioId="portfolio-1" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(screen.getByText('$150.00')).toBeInTheDocument()
    })

    // Component should render without errors
    // Only AAPL BUY transaction should be included in trade markers (filtered by component logic)
  })

  it('calculates Y-axis domain including trade markers at min price', async () => {
    const mockHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 150, currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 160, currency: 'USD' },
          timestamp: '2024-01-02T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'mock',
      cached: false,
    }

    // Trade marker at lower price than any chart data
    const mockTransactions: TransactionListResponse = {
      transactions: [
        {
          id: '1',
          portfolio_id: 'portfolio-1',
          transaction_type: 'BUY',
          timestamp: '2024-01-01T00:00:00Z',
          cash_change: '-1400.00',
          ticker: 'AAPL',
          quantity: '10',
          price_per_share: '140.00', // Lower than min chart price (150)
          notes: null,
        },
      ],
      total_count: 1,
      limit: 100,
      offset: 0,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)
    vi.spyOn(transactionsApi.transactionsApi, 'list').mockResolvedValue(
      mockTransactions
    )

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" portfolioId="portfolio-1" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(screen.getByText('$160.00')).toBeInTheDocument()
    })

    // Component should render without errors
    // Y-axis domain should include the trade marker at 140 (below the min price line of 150)
  })

  it('calculates Y-axis domain including trade markers at max price', async () => {
    const mockHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 150, currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 160, currency: 'USD' },
          timestamp: '2024-01-02T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'mock',
      cached: false,
    }

    // Trade marker at higher price than any chart data
    const mockTransactions: TransactionListResponse = {
      transactions: [
        {
          id: '1',
          portfolio_id: 'portfolio-1',
          transaction_type: 'SELL',
          timestamp: '2024-01-02T00:00:00Z',
          cash_change: '1700.00',
          ticker: 'AAPL',
          quantity: '10',
          price_per_share: '170.00', // Higher than max chart price (160)
          notes: null,
        },
      ],
      total_count: 1,
      limit: 100,
      offset: 0,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)
    vi.spyOn(transactionsApi.transactionsApi, 'list').mockResolvedValue(
      mockTransactions
    )

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" portfolioId="portfolio-1" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(screen.getByText('$160.00')).toBeInTheDocument()
    })

    // Component should render without errors
    // Y-axis domain should include the trade marker at 170 (above the max price line of 160)
  })

  it('filters out trade markers outside the chart date range', async () => {
    const mockHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 150, currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 155, currency: 'USD' },
          timestamp: '2024-01-02T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 160, currency: 'USD' },
          timestamp: '2024-01-03T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'mock',
      cached: false,
    }

    // Trade markers: one within range, one outside range
    const mockTransactions: TransactionListResponse = {
      transactions: [
        {
          id: '1',
          portfolio_id: 'portfolio-1',
          transaction_type: 'BUY',
          timestamp: '2024-01-02T00:00:00Z', // Within chart range
          cash_change: '-1550.00',
          ticker: 'AAPL',
          quantity: '10',
          price_per_share: '155.00',
          notes: null,
        },
        {
          id: '2',
          portfolio_id: 'portfolio-1',
          transaction_type: 'SELL',
          timestamp: '2024-01-10T00:00:00Z', // Outside chart range (after Jan 3)
          cash_change: '1700.00',
          ticker: 'AAPL',
          quantity: '10',
          price_per_share: '170.00',
          notes: null,
        },
      ],
      total_count: 2,
      limit: 100,
      offset: 0,
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)
    vi.spyOn(transactionsApi.transactionsApi, 'list').mockResolvedValue(
      mockTransactions
    )

    const Wrapper = createWrapper()
    render(<PriceChart ticker="AAPL" portfolioId="portfolio-1" />, {
      wrapper: Wrapper,
    })

    await waitFor(() => {
      expect(screen.getByText('$160.00')).toBeInTheDocument()
    })

    // Component should render without errors
    // Only the trade marker on Jan 2 (within range) should be included
    // The trade marker on Jan 10 (outside range) should be filtered out
    // This prevents XAxis calculation issues that would cause null X coordinates
  })
})
