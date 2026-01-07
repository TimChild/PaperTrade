/**
 * Portfolio Analytics page displaying performance charts and metrics
 */
import { useParams, Link } from 'react-router-dom'
import { usePortfolio } from '@/hooks/usePortfolio'
import { PerformanceChart } from '@/components/features/analytics/PerformanceChart'
import { CompositionChart } from '@/components/features/analytics/CompositionChart'
import { MetricsCards } from '@/components/features/analytics/MetricsCards'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'

export function PortfolioAnalytics(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const portfolioId = id || ''

  const { data: portfolio, isLoading, error } = usePortfolio(portfolioId)

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <LoadingSpinner size="lg" className="py-12" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <ErrorDisplay error={error} />
        <Link
          to="/dashboard"
          className="mt-4 inline-block text-blue-600 hover:underline dark:text-blue-400"
        >
          ← Back to Dashboard
        </Link>
      </div>
    )
  }

  if (!portfolioId) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p className="text-red-500">Portfolio not found</p>
        <Link
          to="/dashboard"
          className="mt-4 inline-block text-blue-600 hover:underline dark:text-blue-400"
        >
          ← Back to Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div
      className="container mx-auto px-4 py-8"
      data-testid="portfolio-analytics"
    >
      {/* Header with navigation */}
      <div className="mb-6">
        <Link
          to={`/portfolio/${portfolioId}`}
          data-testid="analytics-back-link"
          className="mb-4 inline-flex items-center text-blue-600 hover:underline dark:text-blue-400"
        >
          ← Back to Portfolio
        </Link>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
          {portfolio?.name} - Analytics
        </h1>
      </div>

      <div className="space-y-8">
        {/* Performance Summary */}
        <section>
          <h2 className="mb-4 text-2xl font-semibold text-gray-900 dark:text-white">
            Performance Summary
          </h2>
          <MetricsCards portfolioId={portfolioId} />
        </section>

        {/* Performance Chart */}
        <section>
          <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
            Portfolio Value Over Time
          </h3>
          <div className="rounded-lg bg-white p-4 shadow dark:bg-gray-800">
            <PerformanceChart portfolioId={portfolioId} />
          </div>
        </section>

        {/* Composition Chart */}
        <section>
          <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
            Holdings Composition
          </h3>
          <div className="rounded-lg bg-white p-4 shadow dark:bg-gray-800">
            <CompositionChart portfolioId={portfolioId} />
          </div>
        </section>
      </div>
    </div>
  )
}
