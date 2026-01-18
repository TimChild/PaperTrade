/**
 * API Error types for handling different error scenarios
 */

/**
 * Categorizes different types of API errors for appropriate handling
 */
export type ApiErrorType =
  | 'rate_limit' // 503 from rate limiting
  | 'server_error' // 500 server error
  | 'not_found' // 404 ticker not found
  | 'network_error' // Network/timeout issues
  | 'unknown' // Other errors

/**
 * Structured error information for API failures
 * Provides context for displaying appropriate error messages to users
 */
export interface ApiError {
  type: ApiErrorType
  message: string
  retryAfter?: number // Seconds until retry (for rate limits)
  details?: string // Technical details for debugging
}
