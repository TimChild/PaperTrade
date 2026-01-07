/**
 * Performance chart component displaying portfolio value over time
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
  ReferenceLine,
} from 'recharts'
import { usePerformance } from '@/hooks/useAnalytics'
import { formatCurrency, formatDate } from '@/utils/formatters'
import type { TimeRange } from '@/services/api/analytics'

interface PerformanceChartProps {
  portfolioId: string
}

const TIME_RANGES: TimeRange[] = ['1W', '1M', '3M', '1Y', 'ALL']

export function PerformanceChart({
  portfolioId,
}: PerformanceChartProps): React.JSX.Element {
  const [range, setRange] = useState<TimeRange>('1M')
  const { data, isLoading, error } = usePerformance(portfolioId, range)

  if (isLoading) {
    return <div data-testid="performance-chart-loading">Loading chart...</div>
  }

  if (error) {
    return (
      <div data-testid="performance-chart-error" className="text-red-500">
        Failed to load performance data
      </div>
    )
  }

  if (!data || data.data_points.length === 0) {
    return (
      <div data-testid="performance-chart-empty">
        No performance data available. Snapshots will be generated daily.
      </div>
    )
  }

  const chartData = data.data_points.map((point) => ({
    date: point.date,
    value: point.total_value,
  }))

  const startValue = data.metrics?.starting_value ?? chartData[0]?.value

  return (
    <div data-testid="performance-chart">
      {/* Time Range Selector */}
      <div className="mb-4 flex gap-2">
        {TIME_RANGES.map((r) => (
          <button
            key={r}
            data-testid={`range-${r}`}
            className={`rounded px-3 py-1 ${
              range === r
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            onClick={() => setRange(r)}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tickFormatter={(date) => formatDate(date, 'short')}
          />
          <YAxis
            tickFormatter={(value) => formatCurrency(value, 'USD', 'compact')}
          />
          <Tooltip
            formatter={(value: number | undefined) =>
              value !== undefined
                ? [formatCurrency(value), 'Value']
                : ['---', 'Value']
            }
            labelFormatter={(label) => formatDate(label, 'long')}
          />
          {startValue && (
            <ReferenceLine
              y={startValue}
              stroke="gray"
              strokeDasharray="3 3"
              label="Start"
            />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
