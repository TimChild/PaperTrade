/**
 * Compare backtests page — overlay normalized % return chart + metrics table
 */
import { Link, useSearchParams } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ComparisonChart } from '@/components/features/backtests/ComparisonChart'
import { ComparisonTable } from '@/components/features/backtests/ComparisonTable'
import { useStrategies } from '@/hooks/useStrategies'
import { backtestsApi } from '@/services/api/backtests'
import { analyticsApi } from '@/services/api/analytics'

export function CompareBacktests(): React.JSX.Element {
  const [searchParams] = useSearchParams()
  const idsParam = searchParams.get('ids') ?? ''
  const ids = idsParam
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean)

  const { data: strategies } = useStrategies()

  const strategyNames: Record<string, string> = {}
  strategies?.forEach((s) => {
    strategyNames[s.id] = s.name
  })

  // Load all backtests in parallel using useQueries
  const backtestQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ['backtests', id],
      queryFn: () => backtestsApi.getById(id),
      staleTime: 30_000,
      enabled: Boolean(id),
    })),
  })

  const loadedBacktests = backtestQueries
    .map((q) => q.data)
    .filter((b) => b !== undefined)

  // Load performance data for all loaded backtests in parallel
  const performanceQueries = useQueries({
    queries: loadedBacktests.map((b) => ({
      queryKey: ['performance', b.portfolio_id, 'ALL'],
      queryFn: () => analyticsApi.getPerformance(b.portfolio_id, 'ALL'),
      staleTime: 5 * 60 * 1000,
      enabled: Boolean(b.portfolio_id),
    })),
  })

  const isLoadingBacktests = backtestQueries.some((q) => q.isLoading)
  const isLoadingPerformance =
    loadedBacktests.length > 0 && performanceQueries.some((q) => q.isLoading)
  const isLoading = isLoadingBacktests || isLoadingPerformance

  const performanceSeries = loadedBacktests
    .map((b, i) => {
      const perfData = performanceQueries[i]?.data
      if (!perfData) return null
      return {
        name: b.backtest_name,
        data: perfData.data_points.map((d) => ({
          date: d.date,
          total_value: d.total_value,
        })),
      }
    })
    .filter(
      (
        entry
      ): entry is {
        name: string
        data: { date: string; total_value: number }[]
      } => entry !== null
    )

  if (ids.length === 0) {
    return (
      <div
        className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
        data-testid="compare-backtests-page"
      >
        <div className="mb-4">
          <Link to="/backtests">
            <Button variant="secondary" size="sm">
              ← Back to Backtests
            </Button>
          </Link>
        </div>
        <p className="text-gray-500 dark:text-gray-400">
          No backtest IDs provided. Please select backtests to compare.
        </p>
      </div>
    )
  }

  return (
    <div
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
      data-testid="compare-backtests-page"
    >
      {/* Back link */}
      <div className="mb-4">
        <Link to="/backtests">
          <Button variant="secondary" size="sm" data-testid="back-to-backtests">
            ← Back to Backtests
          </Button>
        </Link>
      </div>

      <h2 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white">
        Compare Backtests
      </h2>

      {/* Loading state */}
      {isLoading && (
        <div data-testid="compare-loading" className="py-12">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
            Loading backtest data…
          </p>
        </div>
      )}

      {/* Content once loaded */}
      {!isLoading && (
        <>
          {/* Normalized performance chart */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Normalized Performance (%)</CardTitle>
            </CardHeader>
            <CardContent>
              <ComparisonChart series={performanceSeries} />
            </CardContent>
          </Card>

          {/* Metrics comparison table */}
          <Card>
            <CardHeader>
              <CardTitle>Metrics Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <ComparisonTable
                backtests={loadedBacktests}
                strategyNames={strategyNames}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
