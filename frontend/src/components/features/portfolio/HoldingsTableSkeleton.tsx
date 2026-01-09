/**
 * Skeleton loader for holdings table
 * Displays while holdings data is being fetched
 */

export function HoldingsTableSkeleton(): React.JSX.Element {
  return (
    <div
      className="rounded-lg border border-gray-300 bg-white dark:border-gray-700 dark:bg-gray-800"
      data-testid="holdings-table-skeleton"
    >
      <div className="p-4">
        <div className="animate-pulse space-y-4">
          {/* Table header */}
          <div className="flex gap-4 border-b border-gray-200 pb-3 dark:border-gray-700">
            <div className="h-4 w-16 rounded bg-gray-300 dark:bg-gray-700"></div>
            <div className="h-4 w-20 rounded bg-gray-300 dark:bg-gray-700"></div>
            <div className="h-4 w-24 rounded bg-gray-300 dark:bg-gray-700"></div>
            <div className="h-4 w-24 rounded bg-gray-300 dark:bg-gray-700"></div>
          </div>

          {/* Table rows */}
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-4 py-3">
              <div className="h-5 w-16 rounded bg-gray-200 dark:bg-gray-700"></div>
              <div className="h-5 w-20 rounded bg-gray-200 dark:bg-gray-700"></div>
              <div className="h-5 w-24 rounded bg-gray-200 dark:bg-gray-700"></div>
              <div className="h-5 w-24 rounded bg-gray-200 dark:bg-gray-700"></div>
              <div className="h-5 w-20 rounded bg-gray-200 dark:bg-gray-700"></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
