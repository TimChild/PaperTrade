/**
 * Backtest metrics — editorial 5-up grid of MetricStats. Each tile pairs a
 * small-caps label with a display-serif tabular value; gain/loss tones
 * use the muted gain/loss palette.
 */
import { MetricStat } from '@/components/ui/MetricStat'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { formatCurrency, formatPercent, formatDate } from '@/utils/formatters'
import type { BacktestRunResponse, BacktestStatus } from '@/services/api/types'

const STATUS_LABELS: Record<BacktestStatus, string> = {
  COMPLETED: 'Completed',
  PENDING: 'Pending',
  RUNNING: 'Running',
  FAILED: 'Failed',
}

const STATUS_STYLES: Record<BacktestStatus, string> = {
  COMPLETED: 'bg-gain-soft text-gain',
  PENDING: 'bg-amber-soft text-amber',
  RUNNING: 'bg-amber-soft text-amber',
  FAILED: 'bg-loss-soft text-loss',
}

interface BacktestStatusBadgeProps {
  status: BacktestStatus
}

/**
 * Inline backtest status badge — mirrors ActivationStatusBadge tones.
 * Reused by BacktestResult and BacktestMetrics.
 */
export function BacktestStatusBadge({
  status,
}: BacktestStatusBadgeProps): React.JSX.Element {
  return (
    <span
      data-testid="backtest-status-badge"
      role="status"
      aria-label={`Backtest status: ${STATUS_LABELS[status]}`}
      className={`inline-flex items-center font-eyebrow rounded-editorial px-2 py-1 ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  )
}

interface BacktestMetricsProps {
  backtest: BacktestRunResponse
}

export function BacktestMetrics({
  backtest,
}: BacktestMetricsProps): React.JSX.Element {
  const totalReturnPct =
    backtest.total_return_pct !== null
      ? parseFloat(backtest.total_return_pct) / 100
      : null
  const annualizedReturnPct =
    backtest.annualized_return_pct !== null
      ? parseFloat(backtest.annualized_return_pct) / 100
      : null
  const maxDrawdownPct =
    backtest.max_drawdown_pct !== null
      ? parseFloat(backtest.max_drawdown_pct) / 100
      : null

  const returnTone = (value: number | null): 'neutral' | 'gain' | 'loss' => {
    if (value === null) return 'neutral'
    return value >= 0 ? 'gain' : 'loss'
  }

  return (
    <div data-testid="backtest-metrics">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <Eyebrow>Performance</Eyebrow>
          <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
            Metrics
          </h2>
        </div>
        <BacktestStatusBadge status={backtest.status} />
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3 lg:grid-cols-5">
        <MetricStat
          label="Initial cash"
          value={formatCurrency(parseFloat(backtest.initial_cash))}
          size="sm"
          testId="metric-initial-cash"
        />
        <MetricStat
          label="Total return"
          value={
            totalReturnPct !== null ? formatPercent(totalReturnPct) : '---'
          }
          size="sm"
          tone={returnTone(totalReturnPct)}
          testId="metric-total-return"
        />
        <MetricStat
          label="Annualized return"
          value={
            annualizedReturnPct !== null
              ? formatPercent(annualizedReturnPct)
              : '---'
          }
          size="sm"
          tone={returnTone(annualizedReturnPct)}
          testId="metric-annualized-return"
        />
        <MetricStat
          label="Max drawdown"
          value={
            maxDrawdownPct !== null
              ? formatPercent(maxDrawdownPct, false)
              : '---'
          }
          size="sm"
          tone={
            maxDrawdownPct !== null && maxDrawdownPct < 0 ? 'loss' : 'neutral'
          }
          testId="metric-max-drawdown"
        />
        <MetricStat
          label="Total trades"
          value={
            backtest.total_trades !== null
              ? String(backtest.total_trades)
              : '---'
          }
          size="sm"
          testId="metric-total-trades"
        />
      </div>

      <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 font-tabular text-body-sm text-ink-muted">
        <span data-testid="backtest-date-range">
          {formatDate(backtest.start_date, false)} –{' '}
          {formatDate(backtest.end_date, false)}
        </span>
        {backtest.completed_at && (
          <span data-testid="backtest-completed-at">
            Completed {formatDate(backtest.completed_at, true)}
          </span>
        )}
      </div>
    </div>
  )
}
