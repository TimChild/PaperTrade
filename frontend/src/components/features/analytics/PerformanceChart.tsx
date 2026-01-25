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
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

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
    return (
      <Card>
        <CardContent className="pt-6">
          <div data-testid="performance-chart-loading">Loading chart...</div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div data-testid="performance-chart-error" className="text-negative">
            Failed to load performance data
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.data_points.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div
            data-testid="performance-chart-empty"
            className="flex flex-col items-center gap-3"
          >
            <p className="text-foreground-secondary text-center">
              No performance data available yet.
            </p>
            <p className="text-sm text-foreground-tertiary text-center">
              Performance charts update daily after market close. Check back
              tomorrow!
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const chartData = data.data_points.map((point) => ({
    date: point.date,
    value: point.total_value,
  }))

  const startValue = data.metrics?.starting_value ?? chartData[0]?.value

  return (
    <Card data-testid="performance-chart">
      <CardHeader>
        <CardTitle className="text-heading-md">Performance</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Time Range Selector */}
        <div className="mb-4 flex gap-2">
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

        {/* Chart */}
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--foreground) / 0.1)"
            />
            <XAxis
              dataKey="date"
              tickFormatter={(date) => formatDate(date, 'short')}
              stroke="hsl(var(--foreground) / 0.5)"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              tickFormatter={(value) => formatCurrency(value, 'USD', 'compact')}
              stroke="hsl(var(--foreground) / 0.5)"
              style={{ fontSize: '12px' }}
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
                  ? [formatCurrency(value), 'Value']
                  : ['---', 'Value']
              }
              labelFormatter={(label) => formatDate(label, 'long')}
            />
            {startValue && (
              <ReferenceLine
                y={startValue}
                stroke="hsl(var(--foreground) / 0.3)"
                strokeDasharray="3 3"
                label="Start"
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
