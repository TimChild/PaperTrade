/**
 * Utility functions for formatting API errors
 */
import { AxiosError } from 'axios'
import type { ErrorResponse, StructuredErrorDetail } from '@/services/api/types'
import { formatCurrency } from './formatters'

/**
 * Format a trade error from the API into a user-friendly message
 * @param error - The error from the API call
 * @returns Formatted error message string
 */
export function formatTradeError(error: unknown): string {
  // Handle non-Axios errors
  if (!(error instanceof Error)) {
    return 'An unexpected error occurred'
  }

  // Check if it's an Axios error with response data
  if (!('response' in error) || !error.response) {
    return error.message || 'An unexpected error occurred'
  }

  const axiosError = error as AxiosError<ErrorResponse>
  const detail = axiosError.response?.data?.detail

  // Handle structured error objects
  if (typeof detail === 'object' && detail !== null && 'type' in detail) {
    return formatStructuredError(detail as StructuredErrorDetail)
  }

  // Handle simple string errors
  if (typeof detail === 'string') {
    return detail
  }

  // Fallback to generic error message
  return error.message || 'An unexpected error occurred'
}

/**
 * Format a structured error detail into a user-friendly message
 * @param detail - The structured error detail from the backend
 * @returns Formatted error message string
 */
function formatStructuredError(detail: StructuredErrorDetail): string {
  switch (detail.type) {
    case 'insufficient_funds':
      if (
        typeof detail.available === 'number' &&
        typeof detail.required === 'number' &&
        typeof detail.shortfall === 'number'
      ) {
        return `Insufficient funds. You have ${formatCurrency(detail.available)} but need ${formatCurrency(detail.required)} (shortfall: ${formatCurrency(detail.shortfall)})`
      }
      return detail.message || 'Insufficient funds'

    case 'insufficient_shares':
      if (
        typeof detail.available === 'number' &&
        typeof detail.required === 'number' &&
        typeof detail.shortfall === 'number' &&
        typeof detail.ticker === 'string'
      ) {
        return `Insufficient shares. You have ${detail.available} shares of ${detail.ticker} but need ${detail.required} (shortfall: ${detail.shortfall})`
      }
      return detail.message || 'Insufficient shares'

    case 'invalid_ticker':
      if (typeof detail.ticker === 'string') {
        return `Invalid ticker symbol: ${detail.ticker}`
      }
      return detail.message || 'Invalid ticker symbol'

    case 'invalid_quantity':
      return detail.message || 'Invalid quantity'

    case 'invalid_money':
      return detail.message || 'Invalid amount'

    case 'ticker_not_found':
      if (typeof detail.ticker === 'string') {
        return `Ticker not found: ${detail.ticker}`
      }
      return detail.message || 'Ticker not found'

    case 'market_data_unavailable':
      return (
        detail.message || 'Unable to fetch market data. Please try again later.'
      )

    default:
      // For unknown error types, return the message if available
      return detail.message || 'An error occurred'
  }
}
