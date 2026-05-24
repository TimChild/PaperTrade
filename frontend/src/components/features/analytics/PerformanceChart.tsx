/**
 * Editorial performance chart — single-line value-over-time, hairline
 * gridlines, cool slate-teal stroke. Sits flush in its parent (no card
 * chrome) so the page composition can wrap it intentionally.
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
import { Button } from '@/components/ui/button'

interface PerformanceChartProps {
  portfolioId: string
  /**
   * When provided (backtest context), the chart will prepend a flat
   * initial-cash segment from this date to the first real data point
   * whenever the 'ALL' range is selected and the data starts later
   * than the backtest itself.
   */
  backtestStartDate?: string
  /** Initial cash value in USD (numeric). Paired with backtestStartDate. */
  initialCash?: number
}

const TIME_RANGES: TimeRange[] = ['1W', '1M', '3M', '1Y', 'ALL']

export function PerformanceChart({
  portfolioId,
  backtestStartDate,
  initialCash,
}: PerformanceChartProps): React.JSX.Element {
  const [range, setRange] = useState<TimeRange>('1M')
  const { data, isLoading, error } = usePerformance(portfolioId, range)

  if (isLoading) {
    return (
      <div
        data-testid="performance-chart-loading"
        className="flex h-[400px] items-center justify-center text-body-sm text-ink-muted"
      >
        Loading chart...
      </div>
    )
  }

  if (error) {
    return (
      <div
        data-testid="performance-chart-error"
        className="rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-body-sm text-ink"
      >
        Failed to load performance data
      </div>
    )
  }

  if (!data || data.data_points.length === 0) {
    return (
      <div
        data-testid="performance-chart-empty"
        className="flex h-[300px] flex-col items-center justify-center gap-2 rounded-editorial border border-hairline bg-canvas-raised/40 p-6"
      >
        <p className="text-body-sm text-ink">
          No performance data available yet.
        </p>
        <p className="text-body-sm text-ink-muted">
          Performance charts update daily after market close. Check back
          tomorrow.
        </p>
      </div>
    )
  }

  const rawChartData = data.data_points.map((point) => ({
    date: point.date,
    value: point.total_value,
  }))

  // For the ALL range in a backtest context, prepend a flat initial-cash
  // segment from the backtest start date to the first real data point.
  // This ensures the X-axis spans the full requested range rather than
  // only the data-coverage period.
  const chartData: Array<{ date: string; value: number }> = (() => {
    if (
      range === 'ALL' &&
      backtestStartDate !== undefined &&
      initialCash !== undefined &&
      rawChartData.length > 0 &&
      rawChartData[0].date > backtestStartDate
    ) {
      return [{ date: backtestStartDate, value: initialCash }, ...rawChartData]
    }
    return rawChartData
  })()

  const startValue = data.metrics?.starting_value ?? chartData[0]?.value

  return (
    <div data-testid="performance-chart">
      {/* Time Range Selector */}
      <div className="mb-5 flex flex-wrap gap-2">
        {TIME_RANGES.map((r) => (
          <Button
            key={r}
            data-testid={`range-${r}`}
            variant={range === r ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setRange(r)}
          >
            {r}
          </Button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData}>
          <CartesianGrid
            strokeDasharray="2 4"
            stroke="hsl(var(--chart-grid))"
          />
          <XAxis
            dataKey="date"
            tickFormatter={(date) => formatDate(date, 'short')}
            stroke="hsl(var(--chart-axis))"
            style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}
          />
          <YAxis
            domain={['auto', 'auto']}
            tickFormatter={(value) => formatCurrency(value, 'USD', 'compact')}
            stroke="hsl(var(--chart-axis))"
            style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--canvas-raised))',
              border: '1px solid hsl(var(--hairline))',
              borderRadius: '0.25rem',
              color: 'hsl(var(--ink))',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
            }}
            cursor={{ stroke: 'hsl(var(--chart-crosshair))', strokeWidth: 1 }}
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
              stroke="hsl(var(--ink-faint))"
              strokeDasharray="2 4"
              label={{
                value: 'Start',
                position: 'left',
                fill: 'hsl(var(--ink-subtle))',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke="hsl(var(--chart-line-1))"
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
