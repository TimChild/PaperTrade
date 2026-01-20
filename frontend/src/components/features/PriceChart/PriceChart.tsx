/**
 * Price chart component for displaying historical stock prices
 * Uses Recharts for rendering and TanStack Query for data fetching
 */
import { useState, useMemo } from 'react'
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Scatter,
  ZAxis,
} from 'recharts'
import { usePriceHistory } from '@/hooks/usePriceHistory'
import { useTransactions } from '@/hooks/useTransactions'
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

// Scatter plot configuration
const SCATTER_Z_AXIS_SIZE = 64 // Recharts ZAxis range for scatter plot
const TRADE_MARKER_RADIUS = 8 // Visual radius of trade marker circles (px)

interface PriceChartProps {
  ticker: string
  initialTimeRange?: TimeRange
  portfolioId?: string
}

interface ChartDataPoint {
  time: string
  price: number
  fullDate: string
}

interface TradeMarker {
  timestamp: string
  price: number
  action: 'BUY' | 'SELL'
  quantity: string
  fullDate: string
}

interface ScatterShapeProps {
  cx: number
  cy: number
  payload: {
    time: string
    price: number
    action: 'BUY' | 'SELL'
    quantity: string
    fullDate: string
  }
}

export function PriceChart({
  ticker,
  initialTimeRange = '1M',
  portfolioId,
}: PriceChartProps): React.JSX.Element {
  const [timeRange, setTimeRange] = useState<TimeRange>(initialTimeRange)
  const { data, isLoading, error, refetch } = usePriceHistory(ticker, timeRange)

  // Fetch transactions if portfolioId is provided
  const { data: transactionsData } = useTransactions(
    portfolioId || '',
    undefined
  )

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

  // Development mode: Show warning banner if using mock data due to API error
  const showDevWarning = import.meta.env.DEV && data.error

  // Format data for chart
  const chartData: ChartDataPoint[] = data.prices.map((point) => ({
    time: formatDateForAxis(point.timestamp, timeRange),
    price: point.price.amount,
    fullDate: new Date(point.timestamp).toLocaleString(),
  }))

  // Format trade markers to match chart time format
  const formattedTradeMarkers = tradeMarkers.map((marker) => ({
    time: formatDateForAxis(marker.timestamp, timeRange),
    price: marker.price,
    action: marker.action,
    quantity: marker.quantity,
    fullDate: marker.fullDate,
  }))

  // Calculate price change
  // Safe to access [0] and [length-1] because we already checked for empty array above
  const firstPrice = data.prices[0]!.price.amount
  const lastPrice = data.prices[data.prices.length - 1]!.price.amount

  // Validate prices are numbers
  if (!Number.isFinite(firstPrice) || !Number.isFinite(lastPrice)) {
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

  const change = lastPrice - firstPrice
  const changePercent = firstPrice !== 0 ? (change / firstPrice) * 100 : 0
  const isPositive = change >= 0

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
          currentPrice={lastPrice}
          change={change}
          changePercent={changePercent}
        />

        {/* Chart */}
        <ResponsiveContainer width="100%" height={250}>
          <ComposedChart data={chartData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--foreground) / 0.1)"
            />
            <XAxis
              dataKey="time"
              stroke="hsl(var(--foreground) / 0.5)"
              style={{ fontSize: '10px' }}
              className="sm:text-xs"
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis
              domain={['dataMin - 5', 'dataMax + 5']}
              stroke="hsl(var(--foreground) / 0.5)"
              style={{ fontSize: '10px' }}
              className="sm:text-xs"
              tickFormatter={(value) => `$${value.toFixed(0)}`}
            />
            <ZAxis range={[SCATTER_Z_AXIS_SIZE, SCATTER_Z_AXIS_SIZE]} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--foreground) / 0.2)',
                borderRadius: '8px',
                color: 'hsl(var(--foreground))',
              }}
              formatter={(value: number | undefined) =>
                value !== undefined
                  ? [`$${value.toFixed(2)}`, 'Price']
                  : ['N/A', 'Price']
              }
              labelFormatter={(label, payload) =>
                payload?.[0]?.payload.fullDate || label
              }
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke={
                isPositive ? 'hsl(var(--positive))' : 'hsl(var(--negative))'
              }
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
            />
            {/* Trade markers - only show if portfolioId is provided */}
            {portfolioId && formattedTradeMarkers.length > 0 && (
              <Scatter
                name="Trades"
                data={formattedTradeMarkers}
                fill={TRADE_COLORS.BUY}
                shape={(props: unknown) => {
                  // Recharts passes unknown props, so we need to cast
                  // Safe because we control the data structure
                  const { cx, cy, payload } = props as ScatterShapeProps
                  const isBuy = payload.action === 'BUY'
                  const color = isBuy ? TRADE_COLORS.BUY : TRADE_COLORS.SELL

                  return (
                    <g>
                      <circle
                        cx={cx}
                        cy={cy}
                        r={TRADE_MARKER_RADIUS}
                        fill={color}
                        stroke="#fff"
                        strokeWidth={2}
                      />
                    </g>
                  )
                }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

/**
 * Format date for chart X-axis based on time range
 */
function formatDateForAxis(timestamp: string, range: TimeRange): string {
  const date = new Date(timestamp)

  switch (range) {
    case '1D':
      return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
      })
    case '1W':
    case '1M':
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      })
    case '3M':
    case '1Y':
    case 'ALL':
      return date.toLocaleDateString('en-US', {
        month: 'short',
        year: '2-digit',
      })
    default:
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      })
  }
}
