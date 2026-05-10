import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { LightweightPriceChart } from './LightweightPriceChart'
import { ThemeProvider } from '@/contexts/ThemeContext'
import * as pricesApi from '@/services/api/prices'
import {
  PRICE_CHART_DEFAULT_TIMEFRAME,
  usePriceChartStore,
} from '@/stores/priceChartStore'
import type { PriceHistory } from '@/types/price'

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
    // Reset the shared timeframe store so persisted state from one test
    // doesn't leak into the next.
    localStorage.clear()
    usePriceChartStore.setState({
      selectedTimeframe: PRICE_CHART_DEFAULT_TIMEFRAME,
    })
  })

  it('renders loading state initially', () => {
    // Mock a never-resolving fetch so the query stays in the loading state
    vi.spyOn(pricesApi, 'getPriceHistory').mockReturnValue(
      new Promise(() => {})
    )

    const Wrapper = createWrapper()
    render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

    expect(screen.getByText('AAPL')).toBeInTheDocument()
    // The loading skeleton should be shown — not the empty / error UI
    expect(screen.getByTestId('price-chart-loading')).toBeInTheDocument()
    expect(screen.queryByTestId('price-chart-empty')).not.toBeInTheDocument()
    expect(screen.queryByTestId('price-chart-error')).not.toBeInTheDocument()
  })

  it('does not flash empty state while a fetch is in flight', async () => {
    // Simulate a slow upstream: keep the promise pending so React Query
    // exposes `isFetching=true` with no data.
    const slowHistory = {
      ticker: 'AAPL',
      prices: [
        {
          ticker: { symbol: 'AAPL' },
          price: { amount: 200, currency: 'USD' },
          timestamp: '2024-01-02T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'alpha_vantage',
      cached: false,
    }

    let resolveFn: (value: typeof slowHistory) => void = () => {}
    vi.spyOn(pricesApi, 'getPriceHistory').mockImplementation(
      () =>
        new Promise<typeof slowHistory>((resolve) => {
          resolveFn = resolve
        })
    )

    const Wrapper = createWrapper()
    render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

    // While the fetch is pending we must show the loading skeleton, never
    // the empty / error UI — this is the regression guard for the 1Y flash.
    expect(screen.getByTestId('price-chart-loading')).toBeInTheDocument()
    expect(
      screen.queryByText(/No price data available/i)
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/No data found/i)).not.toBeInTheDocument()

    // Resolve the fetch and verify the chart eventually renders the price.
    resolveFn(slowHistory)
    await waitFor(() => {
      expect(screen.getByText('$200.00')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('price-chart-loading')).not.toBeInTheDocument()
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

  describe('shared timeframe via priceChartStore', () => {
    const baseHistory = (
      ticker: string,
      values: [number, number]
    ): PriceHistory => ({
      ticker,
      prices: [
        {
          ticker: { symbol: ticker },
          price: { amount: values[0], currency: 'USD' },
          timestamp: '2024-01-01T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
        {
          ticker: { symbol: ticker },
          price: { amount: values[1], currency: 'USD' },
          timestamp: '2024-01-02T00:00:00Z',
          source: 'cache' as const,
          interval: '1day' as const,
        },
      ],
      source: 'mock',
      cached: false,
    })

    it('clicking the timeframe on one chart updates every other instance', async () => {
      vi.spyOn(pricesApi, 'getPriceHistory').mockImplementation(
        async (ticker: string) => baseHistory(ticker, [100, 110])
      )

      const Wrapper = createWrapper()
      render(
        <>
          <LightweightPriceChart ticker="AAPL" />
          <LightweightPriceChart ticker="MSFT" />
        </>,
        { wrapper: Wrapper }
      )

      // Both charts render the default 1M as pressed.
      await waitFor(() => {
        expect(screen.getAllByLabelText('Show 1M price history')).toHaveLength(
          2
        )
      })

      const initial1MButtons = screen.getAllByLabelText('Show 1M price history')
      for (const btn of initial1MButtons) {
        expect(btn).toHaveAttribute('aria-pressed', 'true')
      }

      // Click 1Y on the *first* chart's selector.
      const oneYearButtons = screen.getAllByLabelText('Show 1Y price history')
      expect(oneYearButtons).toHaveLength(2)
      await userEvent.click(oneYearButtons[0]!)

      // Both charts should now reflect 1Y as pressed — the store is shared.
      await waitFor(() => {
        const pressed = screen
          .getAllByLabelText('Show 1Y price history')
          .map((b) => b.getAttribute('aria-pressed'))
        expect(pressed).toEqual(['true', 'true'])
      })

      // The store itself should also hold the new value.
      expect(usePriceChartStore.getState().selectedTimeframe).toBe('1Y')
    })
  })

  describe('loading-state flash regression', () => {
    it('keeps the chart visible during a refetch (no skeleton flash)', async () => {
      const initialHistory = {
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
      } satisfies PriceHistory

      // First call: resolve immediately. Subsequent call: leave pending so we
      // can inspect the in-flight render. We'll never resolve the second
      // call — the test just asserts that the prior chart stays on screen.
      let callCount = 0
      vi.spyOn(pricesApi, 'getPriceHistory').mockImplementation(
        () =>
          new Promise<typeof initialHistory>((resolve) => {
            if (callCount === 0) {
              callCount += 1
              resolve(initialHistory)
            } else {
              callCount += 1
              // pending forever
            }
          })
      )

      const Wrapper = createWrapper()
      render(<LightweightPriceChart ticker="AAPL" />, { wrapper: Wrapper })

      // Wait for the first fetch to resolve — chart is now showing.
      await waitFor(() => {
        expect(screen.getByText('$110.00')).toBeInTheDocument()
      })

      // Trigger a timeframe change → second fetch → stays pending.
      await userEvent.click(screen.getByLabelText('Show 1Y price history'))

      // While the refetch is in flight:
      // - The price stats from the prior fetch must still be on screen.
      // - The full skeleton must NOT appear (this is the regression guard).
      // - The inline "Updating…" indicator should appear instead.
      await waitFor(() => {
        expect(screen.getByTestId('price-chart-updating')).toBeInTheDocument()
      })
      expect(screen.getByText('$110.00')).toBeInTheDocument()
      expect(
        screen.queryByTestId('price-chart-loading')
      ).not.toBeInTheDocument()
    })
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
