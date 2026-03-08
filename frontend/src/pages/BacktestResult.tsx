/**
 * Backtest result detail page
 */
import { Link, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Card, CardContent } from '@/components/ui/card'
import { BacktestMetrics } from '@/components/features/backtests/BacktestMetrics'
import { PerformanceChart } from '@/components/features/analytics/PerformanceChart'
import { useBacktest } from '@/hooks/useBacktests'
import { formatDate } from '@/utils/formatters'
import type { BacktestStatus } from '@/services/api/types'

const STATUS_STYLES: Record<BacktestStatus, string> = {
  COMPLETED:
    'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  PENDING:
    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  RUNNING:
    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  FAILED: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
}

export function BacktestResult(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const backtestId = id ?? ''
  const { data: backtest, isLoading, error } = useBacktest(backtestId)

  if (isLoading) {
    return (
      <div
        className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8"
        data-testid="backtest-result-loading"
      >
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !backtest) {
    return (
      <div
        className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
        data-testid="backtest-result-error"
      >
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 dark:border-red-800 dark:bg-red-900/20">
          <p className="text-red-600 dark:text-red-400">
            Failed to load backtest. It may have been deleted or does not exist.
          </p>
        </div>
        <div className="mt-4">
          <Link to="/backtests">
            <Button variant="secondary">← Back to Backtests</Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
      data-testid="backtest-result-page"
    >
      {/* Back link */}
      <div className="mb-4">
        <Link to="/backtests">
          <Button variant="secondary" size="sm" data-testid="back-to-backtests">
            ← Back to Backtests
          </Button>
        </Link>
      </div>

      {/* Header */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2
            className="text-2xl font-bold text-gray-900 dark:text-white"
            data-testid="backtest-name"
          >
            {backtest.backtest_name}
          </h2>
          <p
            className="mt-1 text-sm text-gray-500 dark:text-gray-400"
            data-testid="backtest-date-range-header"
          >
            {formatDate(backtest.start_date, false)} –{' '}
            {formatDate(backtest.end_date, false)}
          </p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-sm font-medium ${STATUS_STYLES[backtest.status]}`}
          data-testid="backtest-status-badge"
        >
          {backtest.status}
        </span>
      </div>

      {/* Failed error message */}
      {backtest.status === 'FAILED' && backtest.error_message && (
        <Card className="mb-6 border-red-200 dark:border-red-800">
          <CardContent className="pt-4">
            <p className="font-semibold text-red-700 dark:text-red-400">
              Backtest Failed
            </p>
            <p
              className="mt-1 text-sm text-red-600 dark:text-red-300"
              data-testid="backtest-error-message"
            >
              {backtest.error_message}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Metrics */}
      <div className="mb-8">
        <BacktestMetrics backtest={backtest} />
      </div>

      {/* Performance chart */}
      <PerformanceChart portfolioId={backtest.portfolio_id} />
    </div>
  )
}
