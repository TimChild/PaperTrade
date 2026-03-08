/**
 * Stacked area chart showing portfolio composition over time
 */
import { useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { usePerformance } from '@/hooks/useAnalytics'
import { formatCurrency, formatDate } from '@/utils/formatters'
import type { TimeRange } from '@/services/api/analytics'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface CompositionOverTimeChartProps {
  portfolioId: string
}

const TIME_RANGES: TimeRange[] = ['1W', '1M', '3M', '1Y', 'ALL']

const TICKER_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
]
const CASH_COLOR = '#6b7280' // gray

function getTickerColor(index: number): string {
  return TICKER_COLORS[index % TICKER_COLORS.length]
}

type ChartRow = Record<string, string | number>

function buildChartData(
  dataPoints: {
    date: string
    cash_balance: number
    holdings_value: number
    holdings_breakdown: { ticker: string; value: number }[]
  }[]
): { rows: ChartRow[]; keys: string[] } {
  // Collect all unique ticker/segment keys across all data points
  const tickerSet = new Set<string>()
  let hasAnyBreakdown = false

  for (const point of dataPoints) {
    if (point.holdings_breakdown && point.holdings_breakdown.length > 0) {
      hasAnyBreakdown = true
      for (const item of point.holdings_breakdown) {
        tickerSet.add(item.ticker)
      }
    }
  }

  // If no breakdown data at all, fall back to aggregate "Holdings" key
  if (!hasAnyBreakdown) {
    const rows = dataPoints.map((point) => ({
      date: point.date,
      Cash: point.cash_balance,
      Holdings: point.holdings_value,
    }))
    const keys: string[] = []
    if (dataPoints.some((p) => p.cash_balance > 0)) keys.push('Cash')
    keys.push('Holdings')
    return { rows, keys }
  }

  const tickers = Array.from(tickerSet)

  const rows = dataPoints.map((point) => {
    const row: ChartRow = { date: point.date, Cash: point.cash_balance }

    if (point.holdings_breakdown && point.holdings_breakdown.length > 0) {
      // Full breakdown available
      for (const ticker of tickers) {
        const item = point.holdings_breakdown.find((b) => b.ticker === ticker)
        row[ticker] = item ? item.value : 0
      }
    } else {
      // Old snapshot: spread holdings_value across a "Holdings" bucket, zero individual tickers
      row['Holdings'] = point.holdings_value
      for (const ticker of tickers) {
        row[ticker] = 0
      }
    }

    return row
  })

  // Determine which keys to render (exclude any that are always 0)
  // 'Holdings' is placed after 'Cash' but before individual tickers so that
  // in mixed data sets it stacks logically between cash and position-level areas
  const potentialKeys = ['Cash', 'Holdings', ...tickers]
  const activeKeys = potentialKeys.filter((key) =>
    rows.some((row) => (row[key] as number) > 0)
  )

  return { rows, keys: activeKeys }
}

export function CompositionOverTimeChart({
  portfolioId,
}: CompositionOverTimeChartProps): React.JSX.Element {
  const [range, setRange] = useState<TimeRange>('1M')
  const { data, isLoading, error } = usePerformance(portfolioId, range)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div data-testid="composition-over-time-chart-loading">
            Loading chart...
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div
            data-testid="composition-over-time-chart-error"
            className="text-negative"
          >
            Failed to load composition data
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
            data-testid="composition-over-time-chart-empty"
            className="flex flex-col items-center gap-3"
          >
            <p className="text-foreground-secondary text-center">
              No composition data available yet.
            </p>
            <p className="text-sm text-foreground-tertiary text-center">
              Composition charts update daily after market close. Check back
              tomorrow!
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const { rows, keys } = buildChartData(data.data_points)

  // Assign colors: Cash → CASH_COLOR, others → TICKER_COLORS
  const tickerKeys = keys.filter((k) => k !== 'Cash')

  return (
    <Card data-testid="composition-over-time-chart">
      <CardHeader>
        <CardTitle className="text-heading-md">Composition</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Time Range Selector */}
        <div className="mb-4 flex gap-2">
          {TIME_RANGES.map((r) => (
            <Button
              key={r}
              data-testid={`composition-range-${r}`}
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
          <AreaChart data={rows}>
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
              formatter={(value: number | undefined, name: string) =>
                value !== undefined
                  ? [formatCurrency(value), name]
                  : ['---', name]
              }
              labelFormatter={(label) => formatDate(label, 'long')}
            />
            <Legend />

            {/* Cash area at the bottom (stackId groups them) */}
            {keys.includes('Cash') && (
              <Area
                key="Cash"
                type="monotone"
                dataKey="Cash"
                stackId="composition"
                stroke={CASH_COLOR}
                fill={CASH_COLOR}
                fillOpacity={0.7}
              />
            )}

            {/* One area per ticker stacked on top */}
            {tickerKeys.map((ticker, index) => (
              <Area
                key={ticker}
                type="monotone"
                dataKey={ticker}
                stackId="composition"
                stroke={getTickerColor(index)}
                fill={getTickerColor(index)}
                fillOpacity={0.7}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
