/**
 * Metrics cards component displaying portfolio performance metrics
 *
 * "Current Value" and the gain/return derived from it use the live balance
 * (computed from holdings * current_price), which matches the value shown on
 * the portfolio detail card. Time-series stats — Starting/Highest/Lowest —
 * still come from the daily snapshot history. This keeps the analytics
 * "Current Value" stat aligned with the detail page (and the user's mental
 * model of "what's the portfolio worth right now"), while preserving the
 * snapshot-driven definition of period extremes.
 */
import { usePerformance } from '@/hooks/useAnalytics'
import { usePortfolioBalance } from '@/hooks/usePortfolio'
import { formatCurrency, formatPercent } from '@/utils/formatters'

interface MetricsCardsProps {
  portfolioId: string
}

export function MetricsCards({
  portfolioId,
}: MetricsCardsProps): React.JSX.Element {
  const {
    data: performance,
    isLoading: performanceLoading,
    error: performanceError,
  } = usePerformance(portfolioId, '1M')
  const {
    data: balance,
    isLoading: balanceLoading,
    error: balanceError,
  } = usePortfolioBalance(portfolioId)

  if (performanceLoading || balanceLoading) {
    return <div data-testid="metrics-cards-loading">Loading metrics...</div>
  }

  if (performanceError || balanceError) {
    return (
      <div data-testid="metrics-cards-error" className="text-red-500">
        Failed to load performance metrics. Please try again.
      </div>
    )
  }

  if (!performance?.metrics) {
    return (
      <div data-testid="metrics-cards-empty" className="text-gray-500">
        No performance data available yet. Metrics will be calculated after the
        first daily snapshot is generated.
      </div>
    )
  }

  const { metrics } = performance
  // Use the live total value as "Current Value" so analytics stays aligned
  // with the detail card. Fall back to the last snapshot's ending_value if
  // the balance call has not resolved yet (shouldn't happen given the loading
  // gate above, but keeps the type narrow).
  const liveCurrentValue =
    balance != null ? parseFloat(balance.total_value) : metrics.ending_value
  const liveAbsoluteGain = liveCurrentValue - metrics.starting_value
  const livePercentageGain =
    metrics.starting_value > 0
      ? (liveCurrentValue / metrics.starting_value - 1) * 100
      : 0
  const isPositive = liveAbsoluteGain >= 0
  // Stretch the period's high/low so they remain consistent with the live
  // current value (otherwise a current value above the snapshot high — or
  // below the snapshot low — would render an impossible-looking row).
  const liveHighest = Math.max(metrics.highest_value, liveCurrentValue)
  const liveLowest = Math.min(metrics.lowest_value, liveCurrentValue)

  const cards = [
    {
      label: 'Total Gain/Loss',
      value: formatCurrency(Math.abs(liveAbsoluteGain)),
      trend: isPositive ? 'up' : 'down',
      testId: 'metric-total-gain-loss',
    },
    {
      label: 'Return',
      value: formatPercent(Math.abs(livePercentageGain / 100)),
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
      value: formatCurrency(liveCurrentValue),
      testId: 'metric-current-value',
    },
    {
      label: 'Highest Value',
      value: formatCurrency(liveHighest),
      testId: 'metric-highest-value',
    },
    {
      label: 'Lowest Value',
      value: formatCurrency(liveLowest),
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
          className="rounded-lg bg-white p-4 shadow dark:bg-gray-800"
          data-testid={card.testId}
        >
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {card.label}
          </p>
          <p
            className={`text-xl font-semibold ${
              card.trend === 'up'
                ? 'text-green-600 dark:text-green-400'
                : card.trend === 'down'
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-gray-900 dark:text-white'
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
