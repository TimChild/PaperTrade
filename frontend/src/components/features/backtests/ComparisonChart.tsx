/**
 * Normalized % return overlay chart for comparing multiple backtest series
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
  '#3b82f6',
  '#ef4444',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
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
        className="flex h-64 items-center justify-center text-gray-500 dark:text-gray-400"
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
            strokeDasharray="3 3"
            stroke="hsl(var(--foreground) / 0.1)"
          />
          <XAxis
            dataKey="date"
            tickFormatter={(date: string) => formatDate(date, 'short')}
            stroke="hsl(var(--foreground) / 0.5)"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            tickFormatter={(value: number) =>
              `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
            }
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
            formatter={formatTooltipValue}
            labelFormatter={(label: string) => formatDate(label, 'long')}
          />
          <Legend />
          {series.map((s, index) => (
            <Line
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stroke={CHART_COLORS[index % CHART_COLORS.length]}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
