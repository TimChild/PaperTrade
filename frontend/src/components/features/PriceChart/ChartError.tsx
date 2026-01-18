/**
 * Error state component for price charts
 * Displays when chart data fails to load
 */

interface ChartErrorProps {
  onRetry: () => void
  message?: string
  'data-testid'?: string
}

export function ChartError({
  onRetry,
  message = 'Failed to load price history',
  'data-testid': dataTestId = 'price-chart-error',
}: ChartErrorProps): React.JSX.Element {
  return (
    <div
      className="flex h-64 flex-col items-center justify-center rounded-lg border border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950"
      data-testid={dataTestId}
    >
      <div className="text-center">
        <p className="mb-4 text-lg font-medium text-red-800 dark:text-red-200">
          {message}
        </p>
        <button
          onClick={onRetry}
          className="rounded-lg bg-red-600 px-4 py-2 text-white transition-colors hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-600"
          aria-label="Retry loading chart"
        >
          Retry
        </button>
      </div>
    </div>
  )
}
