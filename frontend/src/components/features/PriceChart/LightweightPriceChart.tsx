/**
 * Price chart component using TradingView Lightweight Charts
 * Alternative implementation to Recharts-based PriceChart
 */
import { useState, useMemo, useEffect, useRef } from 'react'
import {
  createChart,
  createSeriesMarkers,
  ColorType,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type SeriesMarker,
  type Time,
  type ISeriesMarkersPluginApi,
  LineSeries,
} from 'lightweight-charts'
import { usePriceHistory } from '@/hooks/usePriceHistory'
import { useTransactions } from '@/hooks/useTransactions'
import { useTheme } from '@/contexts/ThemeContext'
import { TimeRangeSelector } from './TimeRangeSelector'
import { PriceStats } from './PriceStats'
import { ChartSkeleton } from './ChartSkeleton'
import { ChartError } from './ChartError'
import { PriceChartError } from './PriceChartError'
import type { TimeRange } from '@/types/price'
import type { ApiError } from '@/types/errors'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { isApiError } from '@/utils/priceErrors'

// Trade marker colors
const TRADE_COLORS = {
  BUY: '#10b981', // green-500
  SELL: '#ef4444', // red-500
} as const

interface LightweightPriceChartProps {
  ticker: string
  initialTimeRange?: TimeRange
  portfolioId?: string
}

interface TradeMarker {
  timestamp: string
  price: number
  action: 'BUY' | 'SELL'
  quantity: string
  fullDate: string
}

export function LightweightPriceChart({
  ticker,
  initialTimeRange = '1M',
  portfolioId,
}: LightweightPriceChartProps): React.JSX.Element {
  const [timeRange, setTimeRange] = useState<TimeRange>(initialTimeRange)
  const { data, isLoading, error, refetch } = usePriceHistory(ticker, timeRange)
  const { effectiveTheme } = useTheme()

  // Fetch transactions if portfolioId is provided
  const { data: transactionsData } = useTransactions(
    portfolioId || '',
    undefined
  )

  // Container ref for chart mounting
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)

  // Filter and map transactions to trade markers
  const tradeMarkers = useMemo(() => {
    if (!transactionsData || !portfolioId) return []

    return transactionsData.transactions
      .filter(
        (t) =>
          t.ticker === ticker &&
          (t.transaction_type === 'BUY' || t.transaction_type === 'SELL') &&
          t.price_per_share !== null &&
          t.price_per_share !== undefined
      )
      .map(
        (t): TradeMarker => ({
          timestamp: t.timestamp,
          price: parseFloat(t.price_per_share!),
          action: t.transaction_type as 'BUY' | 'SELL',
          quantity: t.quantity || '0',
          fullDate: new Date(t.timestamp).toLocaleString(),
        })
      )
  }, [transactionsData, portfolioId, ticker])

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!data || data.prices.length === 0) return null

    const lineData: LineData[] = data.prices.map((point) => ({
      time: point.timestamp.split('T')[0] as Time, // Convert to YYYY-MM-DD format
      value: point.price.amount,
    }))

    // Sort by time (lightweight-charts requires sorted data)
    lineData.sort((a, b) => {
      const timeA = new Date(a.time as string).getTime()
      const timeB = new Date(b.time as string).getTime()
      return timeA - timeB
    })

    return lineData
  }, [data])

  // Prepare trade markers for lightweight-charts
  const chartMarkers = useMemo((): SeriesMarker<Time>[] => {
    if (!chartData || tradeMarkers.length === 0) return []

    return tradeMarkers.map((marker) => ({
      time: marker.timestamp.split('T')[0] as Time,
      position: marker.action === 'BUY' ? 'belowBar' : 'aboveBar',
      color: TRADE_COLORS[marker.action],
      shape: marker.action === 'BUY' ? 'arrowUp' : 'arrowDown',
      text: `${marker.action} ${marker.quantity} @ $${marker.price.toFixed(2)}`,
    }))
  }, [chartData, tradeMarkers])

  // Calculate price change stats
  const priceStats = useMemo(() => {
    if (!data || data.prices.length === 0) return null

    const firstPrice = data.prices[0]!.price.amount
    const lastPrice = data.prices[data.prices.length - 1]!.price.amount

    if (!Number.isFinite(firstPrice) || !Number.isFinite(lastPrice)) {
      return null
    }

    const change = lastPrice - firstPrice
    const changePercent = firstPrice !== 0 ? (change / firstPrice) * 100 : 0
    const isPositive = change >= 0

    return { lastPrice, change, changePercent, isPositive }
  }, [data])

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return

    const isDark = effectiveTheme === 'dark'

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 250,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: isDark ? '#999999' : '#666666',
        attributionLogo: true, // TradingView attribution requirement
      },
      grid: {
        vertLines: {
          color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
          style: LineStyle.Dashed,
        },
        horzLines: {
          color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
          style: LineStyle.Dashed,
        },
      },
      timeScale: {
        timeVisible: true,
        borderColor: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.2)',
      },
      rightPriceScale: {
        borderColor: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.2)',
      },
      crosshair: {
        mode: 1, // Normal mode
      },
    })

    chartRef.current = chart

    // Add line series
    const lineSeries = chart.addSeries(LineSeries, {
      color: priceStats?.isPositive
        ? isDark
          ? '#10b981'
          : '#059669' // green
        : isDark
          ? '#ef4444'
          : '#dc2626', // red
      lineWidth: 2,
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      },
    })

    seriesRef.current = lineSeries

    // Create markers plugin
    const seriesMarkers = createSeriesMarkers(lineSeries, [])
    markersRef.current = seriesMarkers

    // Cleanup
    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
      markersRef.current = null
    }
  }, [effectiveTheme, priceStats?.isPositive])

  // Update chart data when it changes
  useEffect(() => {
    if (!seriesRef.current || !chartData) return

    seriesRef.current.setData(chartData)
  }, [chartData])

  // Update trade markers when they change
  useEffect(() => {
    if (!markersRef.current) return

    markersRef.current.setMarkers(chartMarkers)
  }, [chartMarkers])

  // Handle responsive resize
  useEffect(() => {
    if (!chartRef.current || !chartContainerRef.current) return

    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    const resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(chartContainerRef.current)

    return () => {
      resizeObserver.disconnect()
    }
  }, [])

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
          <CardTitle className="text-lg sm:text-xl lg:text-heading-md">
            {ticker}
          </CardTitle>
          <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
        </CardHeader>
        <CardContent>
          <ChartSkeleton />
        </CardContent>
      </Card>
    )
  }

  // Error state
  if (error) {
    // Use enhanced error component if it's an ApiError
    if (isApiError(error)) {
      return (
        <Card>
          <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
            <CardTitle className="text-lg sm:text-xl lg:text-heading-md">
              {ticker}
            </CardTitle>
            <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
          </CardHeader>
          <CardContent>
            <PriceChartError
              error={error as ApiError}
              onRetry={() => refetch()}
            />
          </CardContent>
        </Card>
      )
    }

    // Fallback to old error component for non-API errors
    return (
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
          <CardTitle className="text-lg sm:text-xl lg:text-heading-md">
            {ticker}
          </CardTitle>
          <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
        </CardHeader>
        <CardContent>
          <ChartError onRetry={() => refetch()} />
        </CardContent>
      </Card>
    )
  }

  // No data state
  if (!data || data.prices.length === 0) {
    return (
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
          <CardTitle className="text-lg sm:text-xl lg:text-heading-md">
            {ticker}
          </CardTitle>
          <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center">
            <p className="text-foreground-secondary">No price data available</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Invalid price data
  if (!priceStats) {
    return (
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
          <CardTitle className="text-lg sm:text-xl lg:text-heading-md">
            {ticker}
          </CardTitle>
          <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center">
            <p className="text-foreground-secondary">Invalid price data</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Development mode: Show warning banner if using mock data due to API error
  const showDevWarning = import.meta.env.DEV && data.error

  return (
    <Card>
      {/* Header */}
      <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0">
        <CardTitle className="text-lg sm:text-xl lg:text-heading-md">
          {ticker}
        </CardTitle>
        <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
      </CardHeader>

      <CardContent>
        {/* Development Mode Warning Banner */}
        {showDevWarning && (
          <div
            className="mb-4 rounded-lg border border-yellow-400 bg-yellow-100 px-4 py-2 text-sm text-yellow-800 dark:border-yellow-600 dark:bg-yellow-950 dark:text-yellow-200"
            data-testid="dev-warning-banner"
          >
            ⚠️ Development Mode: Using mock data due to API error
          </div>
        )}

        {/* Price Statistics */}
        <PriceStats
          currentPrice={priceStats.lastPrice}
          change={priceStats.change}
          changePercent={priceStats.changePercent}
        />

        {/* Chart Container */}
        <div ref={chartContainerRef} className="w-full" />
      </CardContent>
    </Card>
  )
}
