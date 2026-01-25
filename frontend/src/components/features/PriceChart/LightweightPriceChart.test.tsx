import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { LightweightPriceChart } from './LightweightPriceChart'
import { ThemeProvider } from '@/contexts/ThemeContext'
import * as pricesApi from '@/services/api/prices'

// Mock lightweight-charts to avoid JSDOM issues
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({
      setData: vi.fn(),
    })),
    applyOptions: vi.fn(),
    remove: vi.fn(),
    timeScale: vi.fn(() => ({
      fitContent: vi.fn(),
    })),
  })),
  createSeriesMarkers: vi.fn(() => ({
    setMarkers: vi.fn(),
  })),
  ColorType: { Solid: 0 },
  LineStyle: { Dashed: 0 },
  LineSeries: 'LineSeries',
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
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  )
}

describe('LightweightPriceChart', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', () => {
    const Wrapper = createWrapper()
    render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

    expect(screen.getByText('AAPL')).toBeInTheDocument()
  })

  it('renders chart with price data', async () => {
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
    render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

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
    render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

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
    render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(
        screen.getByText(/No price data available for this time range/i)
      ).toBeInTheDocument()
    })
  })

  it('calculates price change correctly', async () => {
    const mockHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 100, currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 110, currency: 'USD' },
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
    render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

    await waitFor(() => {
      // 10% increase
      expect(screen.getByText('+10.00%')).toBeInTheDocument()
      expect(screen.getByText('+$10.00')).toBeInTheDocument()
    })
  })

  it('shows development warning when using mock data', async () => {
    // Save original env
    const originalEnv = import.meta.env.DEV

    // Set to development mode
    import.meta.env.DEV = true

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
      error: {
        type: 'rate_limit' as const,
        message: 'API rate limit exceeded',
        status: 429,
      },
    }

    vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)

    const Wrapper = createWrapper()
    render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('dev-warning-banner')).toBeInTheDocument()
    })

    // Restore env
    import.meta.env.DEV = originalEnv
  })
})
