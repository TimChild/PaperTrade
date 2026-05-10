/**
 * Editorial normalized % return overlay chart for comparing multiple
 * backtest series. Uses the cool chart palette (slate / teal) — distinct
 * from the warm amber accent used for active states.
 */
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { formatDate } from '@/utils/formatters'

const CHART_COLORS = [
  'hsl(var(--chart-line-1))',
  'hsl(var(--chart-line-2))',
  'hsl(var(--chart-line-3))',
  'hsl(var(--chart-line-4))',
  'hsl(var(--accent-amber))',
  'hsl(var(--ink-muted))',
]

interface SeriesData {
  name: string
  data: { date: string; total_value: number }[]
}

interface ComparisonChartProps {
  series: SeriesData[]
}

interface ChartPoint {
  date: string
  [key: string]: number | string
}

export function ComparisonChart({
  series,
}: ComparisonChartProps): React.JSX.Element {
  if (series.length === 0 || series.every((s) => s.data.length === 0)) {
    return (
      <div
        data-testid="comparison-chart-empty"
        className="flex h-64 items-center justify-center text-body-sm text-ink-muted"
      >
        No performance data available to compare
      </div>
    )
  }

  // Build merged date-indexed data with normalized % returns
  const allDates = Array.from(
    new Set(series.flatMap((s) => s.data.map((d) => d.date)))
  ).sort()

  const normalizedSeries = series.map((s) => {
    const initialValue = s.data[0]?.total_value ?? 1
    const valueMap = new Map(s.data.map((d) => [d.date, d.total_value]))
    return { name: s.name, valueMap, initialValue }
  })

  const chartData: ChartPoint[] = allDates.map((date) => {
    const point: ChartPoint = { date }
    normalizedSeries.forEach(({ name, valueMap, initialValue }) => {
      const value = valueMap.get(date)
      if (value !== undefined && initialValue !== 0) {
        point[name] = parseFloat(
          (((value - initialValue) / initialValue) * 100).toFixed(2)
        )
      }
    })
    return point
  })

  const formatTooltipValue = (value: number | undefined): [string, string] => {
    if (value === undefined) return ['', '']
    return [`${value >= 0 ? '+' : ''}${value.toFixed(2)}%`, '']
  }

  return (
    <div data-testid="comparison-chart">
      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 20, bottom: 5, left: 10 }}
        >
          <CartesianGrid
            strokeDasharray="2 4"
            stroke="hsl(var(--chart-grid))"
          />
          <XAxis
            dataKey="date"
            tickFormatter={(date: string) => formatDate(date, 'short')}
            stroke="hsl(var(--chart-axis))"
            style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}
          />
          <YAxis
            tickFormatter={(value: number) =>
              `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
            }
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
            formatter={formatTooltipValue}
            labelFormatter={(label: string) => formatDate(label, 'long')}
          />
          <Legend
            wrapperStyle={{
              fontFamily: 'var(--font-sans)',
              fontSize: '12px',
              color: 'hsl(var(--ink-muted))',
            }}
          />
          {series.map((s, index) => (
            <Line
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stroke={CHART_COLORS[index % CHART_COLORS.length]}
              strokeWidth={1.5}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
