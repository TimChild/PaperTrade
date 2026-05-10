/**
 * Activations page — list of all the user's strategy activations.
 *
 * Phase C1.4 bonus: a top-level surface to see every active strategy at once,
 * independent of the strategy library. Each row exposes status, target
 * portfolio, frequency, and last-run timestamp.
 */
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { ActivationStatusBadge } from '@/components/features/strategies/ActivationStatusBadge'
import { useActivations } from '@/hooks/useStrategyActivation'
import { useStrategies } from '@/hooks/useStrategies'
import { usePortfolios } from '@/hooks/usePortfolio'
import { formatDate } from '@/utils/formatters'

export function Activations(): React.JSX.Element {
  const { data: activationsPage, isLoading, error } = useActivations()
  const { data: strategiesPage } = useStrategies()
  const { data: portfoliosPage } = usePortfolios()

  const activations = activationsPage?.items
  const strategyNames: Record<string, string> = {}
  strategiesPage?.items.forEach((s) => {
    strategyNames[s.id] = s.name
  })
  const portfolioNames: Record<string, string> = {}
  portfoliosPage?.items.forEach((p) => {
    portfolioNames[p.id] = p.name
  })

  return (
    <div
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
      data-testid="activations-page"
    >
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Live Activations
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Strategies currently set up to run live against your portfolios
          </p>
        </div>
        <Link to="/strategies">
          <Button
            variant="secondary"
            data-testid="activations-go-to-strategies"
          >
            Manage Strategies
          </Button>
        </Link>
      </div>

      {isLoading && (
        <div data-testid="activations-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {error && !isLoading && (
        <div
          data-testid="activations-error"
          className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/20"
        >
          <p className="text-red-600 dark:text-red-400">
            Failed to load activations. Please try again.
          </p>
        </div>
      )}

      {!isLoading && !error && activations?.length === 0 && (
        <EmptyState
          data-testid="activations-empty"
          message="No live activations yet. Activate a strategy from the Strategies page to start trading live."
          action={
            <Link to="/strategies">
              <Button>Go to Strategies</Button>
            </Link>
          }
        />
      )}

      {!isLoading && !error && activations && activations.length > 0 && (
        <div
          className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"
          data-testid="activations-table"
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Strategy
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Status
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Portfolio
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Frequency
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Last Run
                </th>
              </tr>
            </thead>
            <tbody>
              {activations.map((a) => (
                <tr
                  key={a.id}
                  data-testid={`activation-row-${a.id}`}
                  className="border-b border-gray-100 dark:border-gray-800"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                    {strategyNames[a.strategy_id] ?? a.strategy_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3">
                    <ActivationStatusBadge status={a.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {portfolioNames[a.portfolio_id] ??
                      a.portfolio_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {a.frequency.replace(/_/g, ' ').toLowerCase()}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {a.last_executed_at
                      ? formatDate(a.last_executed_at, true)
                      : 'Never'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
