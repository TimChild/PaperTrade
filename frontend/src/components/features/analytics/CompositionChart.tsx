/**
 * Composition pie chart component displaying portfolio asset allocation
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
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

interface CompositionChartProps {
  portfolioId: string
}

const COLORS = [
  'hsl(var(--primary))',
  'hsl(var(--positive))',
  '#f59e0b',
  'hsl(var(--negative))',
  '#8b5cf6',
  '#6b7280',
]

export function CompositionChart({
  portfolioId,
}: CompositionChartProps): React.JSX.Element {
  const { data, isLoading, error } = useComposition(portfolioId)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div data-testid="composition-chart-loading">Loading...</div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div data-testid="composition-chart-error" className="text-negative">
            Failed to load composition data
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.composition.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div data-testid="composition-chart-empty">No holdings data</div>
        </CardContent>
      </Card>
    )
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
    <Card data-testid="composition-chart">
      <CardHeader>
        <CardTitle className="text-heading-md">Asset Composition</CardTitle>
      </CardHeader>
      <CardContent>
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
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--foreground) / 0.2)',
                borderRadius: '8px',
                color: 'hsl(var(--foreground))',
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
