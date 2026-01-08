/**
 * Metrics cards component displaying portfolio performance metrics
 */
import { usePerformance } from '@/hooks/useAnalytics'
import { formatCurrency, formatPercent } from '@/utils/formatters'

interface MetricsCardsProps {
  portfolioId: string
}

export function MetricsCards({
  portfolioId,
}: MetricsCardsProps): React.JSX.Element {
  const { data, isLoading, error } = usePerformance(portfolioId, '1M')

  if (isLoading) {
    return <div data-testid="metrics-cards-loading">Loading metrics...</div>
  }

  if (error) {
    return (
      <div data-testid="metrics-cards-error" className="text-red-500">
        Failed to load performance metrics. Please try again.
      </div>
    )
  }

  if (!data?.metrics) {
    return (
      <div data-testid="metrics-cards-empty" className="text-gray-500">
        No performance data available yet. Metrics will be calculated after the
        first daily snapshot is generated.
      </div>
    )
  }

  const { metrics } = data
  const isPositive = metrics.absolute_gain >= 0

  const cards = [
    {
      label: 'Total Gain/Loss',
      value: formatCurrency(Math.abs(metrics.absolute_gain)),
      trend: isPositive ? 'up' : 'down',
      testId: 'metric-total-gain-loss',
    },
    {
      label: 'Return',
      value: formatPercent(Math.abs(metrics.percentage_gain / 100)),
      trend: isPositive ? 'up' : 'down',
      testId: 'metric-return',
    },
    {
      label: 'Starting Value',
      value: formatCurrency(metrics.starting_value),
      testId: 'metric-starting-value',
    },
    {
      label: 'Current Value',
      value: formatCurrency(metrics.ending_value),
      testId: 'metric-current-value',
    },
    {
      label: 'Highest Value',
      value: formatCurrency(metrics.highest_value),
      testId: 'metric-highest-value',
    },
    {
      label: 'Lowest Value',
      value: formatCurrency(metrics.lowest_value),
      testId: 'metric-lowest-value',
    },
  ]

  return (
    <div
      data-testid="metrics-cards"
      className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6"
    >
      {cards.map((card) => (
        <div
          key={card.testId}
          className="rounded-lg bg-white p-4 shadow"
          data-testid={card.testId}
        >
          <p className="text-sm text-gray-500">{card.label}</p>
          <p
            className={`text-xl font-semibold ${
              card.trend === 'up'
                ? 'text-green-600'
                : card.trend === 'down'
                  ? 'text-red-600'
                  : ''
            }`}
          >
            {card.trend === 'down' && '-'}
            {card.value}
          </p>
        </div>
      ))}
    </div>
  )
}
