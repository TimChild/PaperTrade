/**
 * Price chart component for displaying historical stock prices
 * Uses Recharts for rendering and TanStack Query for data fetching
 */
import { useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { usePriceHistory } from '@/hooks/usePriceHistory'
import { TimeRangeSelector } from './TimeRangeSelector'
import { PriceStats } from './PriceStats'
import { ChartSkeleton } from './ChartSkeleton'
import { ChartError } from './ChartError'
import type { TimeRange } from '@/types/price'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

interface PriceChartProps {
  ticker: string
  initialTimeRange?: TimeRange
}

interface ChartDataPoint {
  time: string
  price: number
  fullDate: string
}

export function PriceChart({
  ticker,
  initialTimeRange = '1M',
}: PriceChartProps): React.JSX.Element {
  const [timeRange, setTimeRange] = useState<TimeRange>(initialTimeRange)
  const { data, isLoading, error, refetch } = usePriceHistory(ticker, timeRange)

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-heading-md">{ticker}</CardTitle>
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
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-heading-md">{ticker}</CardTitle>
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
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-heading-md">{ticker}</CardTitle>
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

  // Format data for chart
  const chartData: ChartDataPoint[] = data.prices.map((point) => ({
    time: formatDateForAxis(point.timestamp, timeRange),
    price: point.price.amount,
    fullDate: new Date(point.timestamp).toLocaleString(),
  }))

  // Calculate price change
  // Safe to access [0] and [length-1] because we already checked for empty array above
  const firstPrice = data.prices[0]!.price.amount
  const lastPrice = data.prices[data.prices.length - 1]!.price.amount

  // Validate prices are numbers
  if (!Number.isFinite(firstPrice) || !Number.isFinite(lastPrice)) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-heading-md">{ticker}</CardTitle>
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
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-heading-md">{ticker}</CardTitle>
        <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
      </CardHeader>

      <CardContent>
        {/* Price Statistics */}
        <PriceStats
          currentPrice={lastPrice}
          change={change}
          changePercent={changePercent}
        />

        {/* Chart */}
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--foreground) / 0.1)"
            />
            <XAxis
              dataKey="time"
              stroke="hsl(var(--foreground) / 0.5)"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              domain={['dataMin - 5', 'dataMax + 5']}
              stroke="hsl(var(--foreground) / 0.5)"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `$${value.toFixed(0)}`}
            />
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
          </LineChart>
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
