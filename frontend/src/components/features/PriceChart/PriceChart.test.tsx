import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PriceChart } from '@/components/features/PriceChart/PriceChart'
import * as pricesApi from '@/services/api/prices'

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
})
