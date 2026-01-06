/**
 * Composition pie chart component displaying portfolio asset allocation
 */
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useComposition } from '@/hooks/useAnalytics'
import { formatCurrency } from '@/utils/formatters'

interface CompositionChartProps {
  portfolioId: string
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6b7280']

export function CompositionChart({ portfolioId }: CompositionChartProps): React.JSX.Element {
  const { data, isLoading, error } = useComposition(portfolioId)

  if (isLoading) {
    return <div data-testid="composition-chart-loading">Loading...</div>
  }

  if (error) {
    return (
      <div data-testid="composition-chart-error" className="text-red-500">
        Failed to load composition data
      </div>
    )
  }

  if (!data || data.composition.length === 0) {
    return <div data-testid="composition-chart-empty">No holdings data</div>
  }

  const chartData = data.composition.map((item) => ({
    name: item.ticker,
    value: Number(item.value),
    percentage: item.percentage,
  }))

  const renderLabel = (props: { name?: string; percentage?: number }) => {
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
          >
            {chartData.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number | undefined) =>
              value !== undefined ? formatCurrency(value) : '---'
            }
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
