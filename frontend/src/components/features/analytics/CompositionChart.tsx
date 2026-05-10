/**
 * Editorial composition pie chart — uses the cool chart palette plus the
 * warm amber as a single accent (the editorial use of the warm tone). Sits
 * flush; no card chrome.
 */
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { useComposition } from '@/hooks/useAnalytics'
import { formatCurrency } from '@/utils/formatters'

interface CompositionChartProps {
  portfolioId: string
}

const COLORS = [
  'hsl(var(--chart-line-1))',
  'hsl(var(--chart-line-2))',
  'hsl(var(--chart-line-3))',
  'hsl(var(--chart-line-4))',
  'hsl(var(--accent-amber))',
  'hsl(var(--ink-muted))',
]

export function CompositionChart({
  portfolioId,
}: CompositionChartProps): React.JSX.Element {
  const { data, isLoading, error } = useComposition(portfolioId)

  if (isLoading) {
    return (
      <div
        data-testid="composition-chart-loading"
        className="flex h-[300px] items-center justify-center text-body-sm text-ink-muted"
      >
        Loading...
      </div>
    )
  }

  if (error) {
    return (
      <div
        data-testid="composition-chart-error"
        className="rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-body-sm text-ink"
      >
        Failed to load composition data
      </div>
    )
  }

  if (!data || data.composition.length === 0) {
    return (
      <div
        data-testid="composition-chart-empty"
        className="flex h-[200px] items-center justify-center text-body-sm text-ink-muted rounded-editorial border border-hairline bg-canvas-raised/40"
      >
        No holdings data
      </div>
    )
  }

  const chartData = data.composition.map((item) => ({
    name: item.ticker,
    value: Number(item.value),
    percentage: item.percentage,
  }))

  const renderLabel = (props: {
    name?: string
    percentage?: number
  }): string => {
    const { name, percentage } = props
    if (name && percentage !== undefined) {
      return `${name} (${percentage}%)`
    }
    return ''
  }

  return (
    <div data-testid="composition-chart">
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={renderLabel}
            stroke="hsl(var(--canvas))"
            strokeWidth={2}
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              fill: 'hsl(var(--ink-muted))',
            }}
          >
            {chartData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number | undefined) =>
              value !== undefined ? formatCurrency(value) : '---'
            }
            contentStyle={{
              backgroundColor: 'hsl(var(--canvas-raised))',
              border: '1px solid hsl(var(--hairline))',
              borderRadius: '0.25rem',
              color: 'hsl(var(--ink))',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
            }}
          />
          <Legend
            wrapperStyle={{
              fontFamily: 'var(--font-sans)',
              fontSize: '12px',
              color: 'hsl(var(--ink-muted))',
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
