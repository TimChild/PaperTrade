/**
 * Enhanced error state component
 * Provides specific, actionable error messages with recovery options
 */

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  actionLabel?: string
  onAction?: () => void
  className?: string
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  actionLabel,
  onAction,
  className = '',
}: ErrorStateProps): React.JSX.Element {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-lg border border-red-200 bg-red-50 p-8 dark:border-red-900 dark:bg-red-900/20 ${className}`}
      data-testid="error-state"
    >
      {/* Error icon */}
      <div className="mb-4 rounded-full bg-red-100 p-3 dark:bg-red-900/30">
        <svg
          className="h-8 w-8 text-red-600 dark:text-red-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>

      <h3 className="mb-2 text-lg font-semibold text-red-900 dark:text-red-200">
        {title}
      </h3>
      <p className="mb-6 max-w-md text-center text-sm text-red-700 dark:text-red-300">
        {message}
      </p>

      <div className="flex flex-wrap justify-center gap-3">
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:bg-red-700 dark:hover:bg-red-600"
            data-testid="error-state-retry"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Try Again
          </button>
        )}

        {onAction && actionLabel && (
          <button
            onClick={onAction}
            className="rounded-md border border-red-600 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:border-red-500 dark:text-red-400 dark:hover:bg-red-900/20"
            data-testid="error-state-action"
          >
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  )
}
