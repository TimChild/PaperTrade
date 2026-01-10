/**
 * Skeleton loader for portfolio detail page
 * Displays while portfolio data is being fetched
 */

export function PortfolioDetailSkeleton(): React.JSX.Element {
  return (
    <div className="space-y-6" data-testid="portfolio-detail-skeleton">
      {/* Header skeleton */}
      <div className="animate-pulse">
        <div className="mb-2 h-8 w-64 rounded bg-gray-300 dark:bg-gray-700"></div>
        <div className="h-4 w-48 rounded bg-gray-300 dark:bg-gray-700"></div>
      </div>

      {/* Summary cards skeleton */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="rounded-lg border border-gray-300 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div className="animate-pulse space-y-3">
              <div className="h-4 w-24 rounded bg-gray-300 dark:bg-gray-700"></div>
              <div className="h-6 w-32 rounded bg-gray-300 dark:bg-gray-700"></div>
            </div>
          </div>
        ))}
      </div>

      {/* Holdings table skeleton */}
      <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-4 h-6 w-32 rounded bg-gray-300 dark:bg-gray-700"></div>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 rounded bg-gray-200 dark:bg-gray-700"
            ></div>
          ))}
        </div>
      </div>

      {/* Transaction history skeleton */}
      <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-4 h-6 w-48 rounded bg-gray-300 dark:bg-gray-700"></div>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-16 rounded bg-gray-200 dark:bg-gray-700"
            ></div>
          ))}
        </div>
      </div>
    </div>
  )
}
