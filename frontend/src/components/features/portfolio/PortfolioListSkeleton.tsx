/**
 * Skeleton loader for portfolio list on dashboard
 * Displays while portfolio data is being fetched
 */

export function PortfolioListSkeleton(): React.JSX.Element {
  return (
    <div
      className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
      data-testid="portfolio-list-skeleton"
    >
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
        >
          <div className="animate-pulse space-y-4">
            {/* Portfolio name */}
            <div className="h-6 w-3/4 rounded bg-gray-300 dark:bg-gray-700"></div>

            {/* Total value label + amount */}
            <div className="space-y-2">
              <div className="h-4 w-24 rounded bg-gray-300 dark:bg-gray-700"></div>
              <div className="h-8 w-32 rounded bg-gray-300 dark:bg-gray-700"></div>
            </div>

            {/* Divider */}
            <div className="border-t border-gray-200 pt-3 dark:border-gray-700">
              <div className="flex justify-between">
                {/* Cash balance */}
                <div className="space-y-2">
                  <div className="h-3 w-20 rounded bg-gray-300 dark:bg-gray-700"></div>
                  <div className="h-4 w-16 rounded bg-gray-300 dark:bg-gray-700"></div>
                </div>

                {/* Daily change */}
                <div className="space-y-2 text-right">
                  <div className="h-3 w-20 rounded bg-gray-300 dark:bg-gray-700"></div>
                  <div className="h-4 w-16 rounded bg-gray-300 dark:bg-gray-700"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
