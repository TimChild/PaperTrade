/**
 * Price chart component for displaying historical stock prices
 * Uses Recharts for rendering and TanStack Query for data fetching
 */
import { useState } from 'react'
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Scatter,
  ComposedChart,
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
  time: string
  price: number
  action: 'BUY' | 'SELL'
  quantity: number
  fullDate: string
}

export function PriceChart({
  ticker,
  initialTimeRange = '1M',
  portfolioId,
}: PriceChartProps): React.JSX.Element {
  const [timeRange, setTimeRange] = useState<TimeRange>(initialTimeRange)
  const { data, isLoading, error, refetch } = usePriceHistory(ticker, timeRange)

  // Fetch transactions only if portfolioId is provided
  const { data: transactionsData } = useTransactions(portfolioId || '')

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

  // Filter and format trade markers for this ticker
  const tradeMarkers: TradeMarker[] = []
  if (transactionsData?.transactions) {
    for (const transaction of transactionsData.transactions) {
      // Only include BUY/SELL transactions for this ticker
      if (
        transaction.ticker === ticker &&
        (transaction.transaction_type === 'BUY' ||
          transaction.transaction_type === 'SELL')
      ) {
        const price = transaction.price_per_share
          ? parseFloat(transaction.price_per_share)
          : 0
        const quantity = transaction.quantity
          ? parseFloat(transaction.quantity)
          : 0

        // Only add marker if we have valid price data
        if (price > 0 && quantity > 0) {
          tradeMarkers.push({
            time: formatDateForAxis(transaction.timestamp, timeRange),
            price,
            action: transaction.transaction_type as 'BUY' | 'SELL',
            quantity,
            fullDate: new Date(transaction.timestamp).toLocaleString(),
          })
        }
      }
    }
  }

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
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--foreground) / 0.2)',
                borderRadius: '8px',
                color: 'hsl(var(--foreground))',
              }}
              formatter={(value: number | undefined) => {
                return value !== undefined
                  ? [`$${value.toFixed(2)}`, 'Price']
                  : ['N/A', 'Price']
              }}
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
            {/* Trade markers */}
            {tradeMarkers.length > 0 && (
              <Scatter
                name="Trades"
                data={tradeMarkers}
                fill="#10b981"
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                shape={(props: any) => {
                  // Recharts ScatterCustomizedShape has complex internal types.
                  // Using 'any' here is acceptable as the props structure is well-defined
                  // by Recharts and validated at runtime. The shape function must return
                  // a React.Element, so we use an empty fragment for invalid cases.
                  const { cx, cy, payload } = props
                  if (cx === undefined || cy === undefined || !payload) {
                    return <></>
                  }

                  const isBuy = payload.action === 'BUY'
                  const color = isBuy ? '#10b981' : '#ef4444'
                  const size = 8

                  if (isBuy) {
                    // Circle for BUY
                    return (
                      <circle
                        cx={cx}
                        cy={cy}
                        r={size}
                        fill={color}
                        stroke="#fff"
                        strokeWidth={2}
                        data-testid={`trade-marker-buy-${payload.fullDate}`}
                      />
                    )
                  } else {
                    // Triangle for SELL
                    const points = `${cx},${cy - size} ${cx + size},${cy + size} ${cx - size},${cy + size}`
                    return (
                      <polygon
                        points={points}
                        fill={color}
                        stroke="#fff"
                        strokeWidth={2}
                        data-testid={`trade-marker-sell-${payload.fullDate}`}
                      />
                    )
                  }
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
