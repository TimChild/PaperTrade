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
      <div className="price-chart">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{ticker}</h3>
          <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
        </div>
        <ChartSkeleton />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="price-chart">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{ticker}</h3>
          <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
        </div>
        <ChartError onRetry={() => refetch()} />
      </div>
    )
  }

  // No data state
  if (!data || data.prices.length === 0) {
    return (
      <div className="price-chart">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{ticker}</h3>
          <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
        </div>
        <div className="flex h-64 items-center justify-center rounded-lg border border-gray-300 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
          <p className="text-gray-600 dark:text-gray-400">No price data available</p>
        </div>
      </div>
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
      <div className="price-chart">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{ticker}</h3>
          <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
        </div>
        <div className="flex h-64 items-center justify-center rounded-lg border border-gray-300 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
          <p className="text-gray-600 dark:text-gray-400">Invalid price data</p>
        </div>
      </div>
    )
  }

  const change = lastPrice - firstPrice
  const changePercent = firstPrice !== 0 ? (change / firstPrice) * 100 : 0
  const isPositive = change >= 0

  return (
    <div className="price-chart">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{ticker}</h3>
        <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
      </div>

      {/* Price Statistics */}
      <PriceStats
        currentPrice={lastPrice}
        change={change}
        changePercent={changePercent}
      />

      {/* Chart */}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="time"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            domain={['dataMin - 5', 'dataMax + 5']}
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1f2937',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
            }}
            formatter={(value: number | undefined) =>
              value !== undefined ? [`$${value.toFixed(2)}`, 'Price'] : ['N/A', 'Price']
            }
            labelFormatter={(label, payload) =>
              payload?.[0]?.payload.fullDate || label
            }
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke={isPositive ? '#10b981' : '#ef4444'}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
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
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }
}
