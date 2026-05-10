/**
 * Editorial metrics cards for portfolio analytics — six MetricStats laid
 * out as a 2/3/6-column grid. Total gain/loss + return are tone-coded
 * (gain/loss); the rest are neutral ink.
 *
 * "Current Value" and the gain/return derived from it use the live balance
 * (computed from holdings * current_price), which matches the value shown on
 * the portfolio detail card. Time-series stats — Starting/Highest/Lowest —
 * still come from the daily snapshot history.
 */
import { MetricStat } from '@/components/ui/MetricStat'
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
    return (
      <div
        data-testid="metrics-cards-loading"
        className="text-body-sm text-ink-muted"
      >
        Loading metrics...
      </div>
    )
  }

  if (performanceError || balanceError) {
    return (
      <div
        data-testid="metrics-cards-error"
        className="rounded-editorial border border-hairline bg-loss-soft/40 p-4 text-body-sm text-ink"
      >
        Failed to load performance metrics. Please try again.
      </div>
    )
  }

  if (!performance?.metrics) {
    return (
      <div
        data-testid="metrics-cards-empty"
        className="rounded-editorial border border-hairline bg-canvas-raised/40 p-4 text-body-sm text-ink-muted"
      >
        No performance data available yet. Metrics will be calculated after the
        first daily snapshot is generated.
      </div>
    )
  }

  const { metrics } = performance
  const liveCurrentValue =
    balance != null ? parseFloat(balance.total_value) : metrics.ending_value
  const liveAbsoluteGain = liveCurrentValue - metrics.starting_value
  const livePercentageGain =
    metrics.starting_value > 0
      ? (liveCurrentValue / metrics.starting_value - 1) * 100
      : 0
  const isPositive = liveAbsoluteGain >= 0
  const liveHighest = Math.max(metrics.highest_value, liveCurrentValue)
  const liveLowest = Math.min(metrics.lowest_value, liveCurrentValue)

  // Pre-format the gain/loss display value with sign so the snapshot tests
  // looking for `-$1,500.00` (with the leading minus) keep matching.
  const gainDisplay = `${isPositive ? '' : '-'}${formatCurrency(Math.abs(liveAbsoluteGain))}`
  const returnDisplay = `${isPositive ? '' : '-'}${formatPercent(Math.abs(livePercentageGain / 100))}`
  const tone = isPositive ? 'gain' : 'loss'

  return (
    <div
      data-testid="metrics-cards"
      className="grid grid-cols-2 gap-x-6 gap-y-8 md:grid-cols-3 lg:grid-cols-6"
    >
      <MetricStat
        label="Total gain/loss"
        value={gainDisplay}
        size="sm"
        tone={tone}
        testId="metric-total-gain-loss"
      />
      <MetricStat
        label="Return"
        value={returnDisplay}
        size="sm"
        tone={tone}
        testId="metric-return"
      />
      <MetricStat
        label="Starting value"
        value={formatCurrency(metrics.starting_value)}
        size="sm"
        testId="metric-starting-value"
      />
      <MetricStat
        label="Current value"
        value={formatCurrency(liveCurrentValue)}
        size="sm"
        testId="metric-current-value"
      />
      <MetricStat
        label="Highest value"
        value={formatCurrency(liveHighest)}
        size="sm"
        testId="metric-highest-value"
      />
      <MetricStat
        label="Lowest value"
        value={formatCurrency(liveLowest)}
        size="sm"
        testId="metric-lowest-value"
      />
    </div>
  )
}
