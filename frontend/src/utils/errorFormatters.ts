/**
 * Utility functions for formatting API errors.
 *
 * Backend (PR #226 / Wave 3-G) emits a single envelope:
 *   { detail: str, code?: ErrorCode | null, fields?: Record<string,string> | null }
 *
 * `detail` is always a human-readable string. `code` is the machine-readable
 * error code we switch on for richer messages. `fields` carries auxiliary
 * payloads (e.g. `{ available, required, shortfall, ticker }`) — note: numeric
 * values arrive as strings because Pydantic dict[str, str] enforces it.
 */
import { AxiosError } from 'axios'
import type { ErrorResponse, ErrorCode } from '@/services/api/types'
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
  const data = axiosError.response?.data
  const detail = data?.detail
  const code = data?.code ?? null
  const fields = data?.fields ?? null

  // Prefer a code-driven, contextual message when we have a known code +
  // useful auxiliary fields. Fall back to the (always-string) `detail` from
  // the backend, then to the AxiosError message.
  if (code) {
    const formatted = formatStructuredError(code, fields, detail)
    if (formatted) return formatted
  }

  if (typeof detail === 'string' && detail.length > 0) {
    return detail
  }

  return error.message || 'An unexpected error occurred'
}

/**
 * Build a user-facing message for a known error code, using `fields` for
 * extra context where available.
 *
 * Numeric fields in `fields` arrive as strings (Pydantic dict[str, str]); we
 * parse them defensively and only enrich the message when all required
 * fields are present and parseable. Otherwise we fall back to the backend's
 * human-readable `detail`.
 */
function formatStructuredError(
  code: ErrorCode,
  fields: Record<string, string> | null,
  detail: string | undefined
): string | null {
  const fallback = detail && detail.length > 0 ? detail : null

  switch (code) {
    case 'insufficient_funds': {
      const available = parseNumericField(fields, 'available')
      const required = parseNumericField(fields, 'required')
      const shortfall = parseNumericField(fields, 'shortfall')
      if (available !== null && required !== null && shortfall !== null) {
        return `Insufficient funds. You have ${formatCurrency(available)} but need ${formatCurrency(required)} (shortfall: ${formatCurrency(shortfall)})`
      }
      return fallback ?? 'Insufficient funds'
    }

    case 'insufficient_shares': {
      const ticker = fields?.ticker
      const available = parseNumericField(fields, 'available')
      const required = parseNumericField(fields, 'required')
      const shortfall = parseNumericField(fields, 'shortfall')
      if (
        typeof ticker === 'string' &&
        available !== null &&
        required !== null &&
        shortfall !== null
      ) {
        return `Insufficient shares. You have ${available} shares of ${ticker} but need ${required} (shortfall: ${shortfall})`
      }
      return fallback ?? 'Insufficient shares'
    }

    case 'invalid_ticker': {
      const ticker = fields?.ticker
      if (typeof ticker === 'string') {
        return `Invalid ticker symbol: ${ticker}`
      }
      return fallback ?? 'Invalid ticker symbol'
    }

    case 'invalid_quantity':
      return fallback ?? 'Invalid quantity'

    case 'invalid_money':
      return fallback ?? 'Invalid amount'

    case 'ticker_not_found': {
      const ticker = fields?.ticker
      if (typeof ticker === 'string') {
        return `Ticker not found: ${ticker}`
      }
      return fallback ?? 'Ticker not found'
    }

    case 'market_data_unavailable':
      return fallback ?? 'Unable to fetch market data. Please try again later.'

    default:
      // Unknown / unmapped code — let caller fall back to `detail`.
      return null
  }
}

function parseNumericField(
  fields: Record<string, string> | null,
  key: string
): number | null {
  const raw = fields?.[key]
  if (typeof raw !== 'string') return null
  const value = Number(raw)
  return Number.isFinite(value) ? value : null
}
