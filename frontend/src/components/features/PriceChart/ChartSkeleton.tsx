/**
 * Skeleton loader for price charts
 * Displays while chart data is being fetched
 */

export function ChartSkeleton(): React.JSX.Element {
  return (
    <div className="animate-pulse">
      {/* Price stats skeleton */}
      <div className="mb-4 flex items-baseline gap-4">
        <div className="h-9 w-32 rounded bg-gray-300 dark:bg-gray-700"></div>
        <div className="h-6 w-24 rounded bg-gray-300 dark:bg-gray-700"></div>
        <div className="h-6 w-20 rounded bg-gray-300 dark:bg-gray-700"></div>
      </div>

      {/* Chart area skeleton */}
      <div className="h-64 rounded-lg bg-gray-200 dark:bg-gray-700"></div>
    </div>
  )
}
