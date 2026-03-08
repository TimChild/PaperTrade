/**
 * Backtest metrics display component
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency, formatPercent, formatDate } from '@/utils/formatters'
import type { BacktestRunResponse, BacktestStatus } from '@/services/api/types'

const STATUS_STYLES: Record<BacktestStatus, string> = {
  COMPLETED:
    'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  PENDING:
    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  RUNNING:
    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  FAILED: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
}

interface MetricCardProps {
  label: string
  value: string
  testId: string
  valueClassName?: string
}

function MetricCard({
  label,
  value,
  testId,
  valueClassName = '',
}: MetricCardProps): React.JSX.Element {
  return (
    <Card data-testid={testId}>
      <CardContent className="pt-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        <p className={`mt-1 text-xl font-bold ${valueClassName}`}>{value}</p>
      </CardContent>
    </Card>
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

  const getReturnClass = (value: number | null): string => {
    if (value === null) return ''
    return value >= 0
      ? 'text-green-600 dark:text-green-400'
      : 'text-red-600 dark:text-red-400'
  }

  return (
    <div data-testid="backtest-metrics">
      <div className="mb-4 flex items-center gap-3">
        <CardHeader className="p-0">
          <CardTitle>Metrics</CardTitle>
        </CardHeader>
        <span
          className={`rounded-full px-3 py-1 text-sm font-medium ${STATUS_STYLES[backtest.status]}`}
          data-testid="backtest-status-badge"
        >
          {backtest.status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <MetricCard
          label="Initial Cash"
          value={formatCurrency(parseFloat(backtest.initial_cash))}
          testId="metric-initial-cash"
        />
        <MetricCard
          label="Total Return"
          value={
            totalReturnPct !== null ? formatPercent(totalReturnPct) : '---'
          }
          testId="metric-total-return"
          valueClassName={getReturnClass(totalReturnPct)}
        />
        <MetricCard
          label="Annualized Return"
          value={
            annualizedReturnPct !== null
              ? formatPercent(annualizedReturnPct)
              : '---'
          }
          testId="metric-annualized-return"
          valueClassName={getReturnClass(annualizedReturnPct)}
        />
        <MetricCard
          label="Max Drawdown"
          value={
            maxDrawdownPct !== null
              ? formatPercent(maxDrawdownPct, false)
              : '---'
          }
          testId="metric-max-drawdown"
          valueClassName={
            maxDrawdownPct !== null && maxDrawdownPct < 0
              ? 'text-red-600 dark:text-red-400'
              : ''
          }
        />
        <MetricCard
          label="Total Trades"
          value={
            backtest.total_trades !== null
              ? String(backtest.total_trades)
              : '---'
          }
          testId="metric-total-trades"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-500 dark:text-gray-400">
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
