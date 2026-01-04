/**
 * Error display component
 */
import { AxiosError } from 'axios'
import type { ErrorResponse } from '@/services/api/types'

interface ErrorDisplayProps {
  error: Error | AxiosError<ErrorResponse> | null
  className?: string
}

export function ErrorDisplay({ error, className = '' }: ErrorDisplayProps) {
  if (!error) return null

  // Extract error message
  let message = 'An unexpected error occurred'

  if (error instanceof Error) {
    // Check if it's an Axios error
    if ('response' in error && error.response?.data) {
      const axiosError = error as AxiosError<ErrorResponse>
      message = axiosError.response?.data?.detail || error.message
    } else {
      message = error.message
    }
  }

  return (
    <div
      className={`rounded-lg border border-red-200 bg-red-50 p-4 ${className}`}
      role="alert"
    >
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-red-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-semibold text-red-800">Error</h3>
          <p className="mt-1 text-sm text-red-600">{message}</p>
        </div>
      </div>
    </div>
  )
}
