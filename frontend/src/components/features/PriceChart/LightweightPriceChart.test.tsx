import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { LightweightPriceChart } from './LightweightPriceChart'
import { ThemeProvider } from '@/contexts/ThemeContext'
import * as pricesApi from '@/services/api/prices'

// Capture click handler registered via subscribeClick so tests can invoke it
let capturedClickHandler: ((param: unknown) => void) | undefined
// Capture the mock series so tests can populate seriesData with a matching key
let capturedSeries: { setData: ReturnType<typeof vi.fn> } | undefined

// Mock lightweight-charts to avoid JSDOM issues
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => {
      capturedSeries = { setData: vi.fn() }
      return capturedSeries
    }),
    applyOptions: vi.fn(),
    remove: vi.fn(),
    timeScale: vi.fn(() => ({
      fitContent: vi.fn(),
    })),
    subscribeClick: vi.fn((handler: (param: unknown) => void) => {
      capturedClickHandler = handler
    }),
    unsubscribeClick: vi.fn(),
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
    capturedClickHandler = undefined
    capturedSeries = undefined
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

  describe('onChartClick callback', () => {
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

    it('extracts price from seriesData when the series has data at the click point', async () => {
      vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)

      const onChartClick = vi.fn()
      const Wrapper = createWrapper()
      render(
        <LightweightPriceChart ticker="AAPL" onChartClick={onChartClick} />,
        { wrapper: Wrapper }
      )

      await waitFor(() => {
        expect(capturedClickHandler).toBeDefined()
        expect(capturedSeries).toBeDefined()
      })

      // Populate seriesData with the captured series reference to simulate a data-point click
      const seriesData = new Map()
      seriesData.set(capturedSeries, { time: '2024-01-02', value: 155 })

      capturedClickHandler!({ time: '2024-01-02', seriesData })

      expect(onChartClick).toHaveBeenCalledWith({
        ticker: 'AAPL',
        date: '2024-01-02',
        price: 155,
      })
    })

    it('calls onChartClick with ticker, date and price when chart is clicked', async () => {
      vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)

      const onChartClick = vi.fn()
      const Wrapper = createWrapper()
      render(
        <LightweightPriceChart ticker="AAPL" onChartClick={onChartClick} />,
        { wrapper: Wrapper }
      )

      // Wait for chart to render with data (subscribeClick is called after init)
      await waitFor(() => {
        expect(capturedClickHandler).toBeDefined()
      })

      // Simulate a click on a data point
      capturedClickHandler!({
        time: '2024-01-02',
        seriesData: new Map(),
      })

      expect(onChartClick).toHaveBeenCalledWith({
        ticker: 'AAPL',
        date: '2024-01-02',
        price: undefined,
      })
    })

    it('does not call onChartClick when clicked outside data range (no time)', async () => {
      vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)

      const onChartClick = vi.fn()
      const Wrapper = createWrapper()
      render(
        <LightweightPriceChart ticker="AAPL" onChartClick={onChartClick} />,
        { wrapper: Wrapper }
      )

      await waitFor(() => {
        expect(capturedClickHandler).toBeDefined()
      })

      // Simulate a click with no time (outside data range)
      capturedClickHandler!({ time: undefined, seriesData: new Map() })

      expect(onChartClick).not.toHaveBeenCalled()
    })

    it('does not throw when onChartClick is not provided', async () => {
      vi.spyOn(pricesApi, 'getPriceHistory').mockResolvedValue(mockHistory)

      const Wrapper = createWrapper()
      render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

      await waitFor(() => {
        expect(capturedClickHandler).toBeDefined()
      })

      // Should not throw when callback is absent
      expect(() => {
        capturedClickHandler!({ time: '2024-01-02', seriesData: new Map() })
      }).not.toThrow()
    })
  })
})
