/**
 * Editorial stacked area chart — portfolio composition over time. Uses the
 * cool chart palette plus the warm amber as a single accent. Sits flush;
 * no card chrome.
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
import { Button } from '@/components/ui/button'

interface CompositionOverTimeChartProps {
  portfolioId: string
}

const TIME_RANGES: TimeRange[] = ['1W', '1M', '3M', '1Y', 'ALL']

const TICKER_COLORS = [
  'hsl(var(--chart-line-1))',
  'hsl(var(--chart-line-2))',
  'hsl(var(--chart-line-3))',
  'hsl(var(--chart-line-4))',
  'hsl(var(--accent-amber))',
  'hsl(var(--ink-muted))',
  'hsl(195 25% 38%)',
  'hsl(215 20% 45%)',
]
const CASH_COLOR = 'hsl(var(--ink-faint))'

function getTickerColor(index: number): string {
  return TICKER_COLORS[index % TICKER_COLORS.length]
}

type ChartRow = Record<string, string | number>

function buildChartData(
  dataPoints: {
    date: string
    cash_balance: number
    holdings_value: number
    holdings_breakdown?: { ticker: string; value: number }[]
  }[]
): { rows: ChartRow[]; keys: string[] } {
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
      for (const ticker of tickers) {
        const item = point.holdings_breakdown.find((b) => b.ticker === ticker)
        row[ticker] = item ? item.value : 0
      }
    } else {
      row['Holdings'] = point.holdings_value
      for (const ticker of tickers) {
        row[ticker] = 0
      }
    }

    return row
  })

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
      <div
        data-testid="composition-over-time-chart-loading"
        className="flex h-[400px] items-center justify-center text-body-sm text-ink-muted"
      >
        Loading chart...
      </div>
    )
  }

  if (error) {
    return (
      <div
        data-testid="composition-over-time-chart-error"
        className="rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-body-sm text-ink"
      >
        Failed to load composition data
      </div>
    )
  }

  if (!data || data.data_points.length === 0) {
    return (
      <div
        data-testid="composition-over-time-chart-empty"
        className="flex h-[300px] flex-col items-center justify-center gap-2 rounded-editorial border border-hairline bg-canvas-raised/40 p-6"
      >
        <p className="text-body-sm text-ink">
          No composition data available yet.
        </p>
        <p className="text-body-sm text-ink-muted">
          Composition charts update daily after market close. Check back
          tomorrow.
        </p>
      </div>
    )
  }

  const { rows, keys } = buildChartData(data.data_points)
  const tickerKeys = keys.filter((k) => k !== 'Cash')

  return (
    <div data-testid="composition-over-time-chart">
      <div className="mb-5 flex flex-wrap gap-2">
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

      <ResponsiveContainer width="100%" height={400}>
        <AreaChart data={rows}>
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
            formatter={(value: number | undefined, name: string | undefined) =>
              value !== undefined
                ? [formatCurrency(value), name ?? '']
                : ['---', name ?? '']
            }
            labelFormatter={(label) => formatDate(label, 'long')}
          />
          <Legend
            wrapperStyle={{
              fontFamily: 'var(--font-sans)',
              fontSize: '12px',
              color: 'hsl(var(--ink-muted))',
            }}
          />

          {keys.includes('Cash') && (
            <Area
              key="Cash"
              type="monotone"
              dataKey="Cash"
              stackId="composition"
              stroke={CASH_COLOR}
              fill={CASH_COLOR}
              fillOpacity={0.55}
            />
          )}

          {tickerKeys.map((ticker, index) => (
            <Area
              key={ticker}
              type="monotone"
              dataKey={ticker}
              stackId="composition"
              stroke={getTickerColor(index)}
              fill={getTickerColor(index)}
              fillOpacity={0.55}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
