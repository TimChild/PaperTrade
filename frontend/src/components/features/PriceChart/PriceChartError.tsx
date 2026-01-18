/**
 * Enhanced error state component for price charts
 * Displays different UI based on error type with actionable guidance
 */
import { Clock, AlertTriangle, WifiOff, Search } from 'lucide-react'
import type { ApiError, ApiErrorType } from '@/types/errors'

interface PriceChartErrorProps {
  error: ApiError
  ticker: string
  onRetry?: () => void
}

export function PriceChartError({
  error,
  ticker,
  onRetry,
}: PriceChartErrorProps): React.JSX.Element {
  const { icon, title } = getErrorDisplay(error.type)

  return (
    <div
      className="flex h-64 flex-col items-center justify-center rounded-lg border border-red-300 bg-red-50 p-6 dark:border-red-800 dark:bg-red-950"
      data-testid="price-chart-error"
    >
      <div className="mb-4 text-red-600 dark:text-red-400">{icon}</div>

      <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
        {title}
      </h3>

      <p className="mb-4 text-center text-sm text-gray-600 dark:text-gray-300">
        {error.message}
      </p>

      {error.type === 'rate_limit' && error.retryAfter && (
        <p className="mb-4 text-xs text-gray-500 dark:text-gray-400">
          Please try again in {error.retryAfter} seconds
        </p>
      )}

      {onRetry && error.type !== 'not_found' && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600"
          aria-label="Retry loading price history"
          data-testid="retry-button"
        >
          Retry
        </button>
      )}

      {import.meta.env.DEV && error.details && (
        <details className="mt-4 w-full text-xs text-gray-500 dark:text-gray-400">
          <summary className="cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">
            Technical Details
          </summary>
          <pre className="mt-2 overflow-auto rounded bg-gray-100 p-2 dark:bg-gray-800">
            {error.details}
          </pre>
        </details>
      )}
    </div>
  )
}

/**
 * Get icon and title for each error type
 */
function getErrorDisplay(type: ApiErrorType): {
  icon: React.JSX.Element
  title: string
} {
  switch (type) {
    case 'rate_limit':
      return {
        icon: <Clock className="h-12 w-12" aria-hidden="true" />,
        title: 'Too Many Requests',
      }
    case 'server_error':
      return {
        icon: <AlertTriangle className="h-12 w-12" aria-hidden="true" />,
        title: 'Server Error',
      }
    case 'network_error':
      return {
        icon: <WifiOff className="h-12 w-12" aria-hidden="true" />,
        title: 'Connection Error',
      }
    case 'not_found':
      return {
        icon: <Search className="h-12 w-12" aria-hidden="true" />,
        title: 'Data Not Found',
      }
    default:
      return {
        icon: <AlertTriangle className="h-12 w-12" aria-hidden="true" />,
        title: 'Something Went Wrong',
      }
  }
}
