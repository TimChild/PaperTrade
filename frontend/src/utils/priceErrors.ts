/**
 * Utility functions for parsing and handling price API errors
 */
import axios from 'axios'
import type { ApiError } from '@/types/errors'

/**
 * Parse an error from a price API call into a structured ApiError
 * @param error - The error from the API call
 * @param ticker - Optional ticker symbol for context in error messages
 * @returns Structured ApiError with type and user-friendly message
 */
export function parseApiError(error: unknown, ticker?: string): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const detail = error.response?.data?.detail

    switch (status) {
      case 503:
        if (typeof detail === 'string' && detail.includes('Rate limit')) {
          return {
            type: 'rate_limit',
            message: 'Market data temporarily unavailable due to high demand',
            retryAfter: 60, // Estimate based on rate limit
            details: detail,
          }
        }
        return {
          type: 'server_error',
          message: 'Service temporarily unavailable',
          details: detail,
        }

      case 404:
        return {
          type: 'not_found',
          message: ticker
            ? `No data found for ${ticker}`
            : 'No data found for this ticker',
          details: detail,
        }

      case 500:
        return {
          type: 'server_error',
          message: 'Server error occurred',
          details: detail,
        }

      default:
        return {
          type: 'unknown',
          message: error.message || 'An unexpected error occurred',
          details: detail,
        }
    }
  }

  // Network/timeout errors
  if (error instanceof Error) {
    if (error.message.includes('timeout') || error.message.includes('network')) {
      return {
        type: 'network_error',
        message: 'Unable to connect to server',
        details: error.message,
      }
    }
    return {
      type: 'unknown',
      message: error.message,
    }
  }

  // Unknown error types
  return {
    type: 'unknown',
    message: 'An unexpected error occurred',
  }
}

/**
 * Type guard to check if an error is an ApiError
 */
export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'type' in error &&
    'message' in error
  )
}
