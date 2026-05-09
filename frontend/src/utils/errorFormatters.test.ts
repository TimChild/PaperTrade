/**
 * Tests for error formatting utilities.
 *
 * Wave 3-G aligned: the backend now returns a single envelope:
 *   { detail: string, code?: ErrorCode | null, fields?: Record<string,string> | null }
 *
 * `fields` is dict[str, str] on the backend (Pydantic enforces this), so
 * numeric auxiliary fields (`available`, `required`, `shortfall`) arrive as
 * strings even when they semantically are numbers — these tests reflect that.
 */
import { describe, it, expect } from 'vitest'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { formatTradeError } from './errorFormatters'
import type { ErrorResponse } from '@/services/api/types'

function makeAxiosError(
  data: ErrorResponse | undefined,
  status = 400
): AxiosError<ErrorResponse> {
  return new AxiosError<ErrorResponse>(
    `Request failed with status code ${status}`,
    String(status),
    undefined,
    undefined,
    {
      status,
      statusText: 'Bad Request',
      data: data as ErrorResponse,
      headers: {},
      config: {} as InternalAxiosRequestConfig,
    }
  )
}

describe('formatTradeError', () => {
  describe('structured errors via code + fields', () => {
    it('formats insufficient_funds with all numeric fields', () => {
      const err = makeAxiosError({
        detail:
          'Insufficient funds. You have $739.67 but need $1,301.65. Shortfall: $561.98',
        code: 'insufficient_funds',
        fields: {
          available: '739.67',
          required: '1301.65',
          shortfall: '561.98',
        },
      })

      expect(formatTradeError(err)).toBe(
        'Insufficient funds. You have $739.67 but need $1,301.65 (shortfall: $561.98)'
      )
    })

    it('falls back to detail string for insufficient_funds with missing fields', () => {
      const err = makeAxiosError({
        detail: 'Insufficient funds',
        code: 'insufficient_funds',
        fields: null,
      })

      expect(formatTradeError(err)).toBe('Insufficient funds')
    })

    it('formats insufficient_shares with all fields', () => {
      const err = makeAxiosError({
        detail: 'Insufficient shares',
        code: 'insufficient_shares',
        fields: {
          ticker: 'AAPL',
          available: '50',
          required: '100',
          shortfall: '50',
        },
      })

      expect(formatTradeError(err)).toBe(
        'Insufficient shares. You have 50 shares of AAPL but need 100 (shortfall: 50)'
      )
    })

    it('falls back to detail for insufficient_shares with missing fields', () => {
      const err = makeAxiosError({
        detail: 'Not enough shares',
        code: 'insufficient_shares',
        fields: null,
      })

      expect(formatTradeError(err)).toBe('Not enough shares')
    })

    it('formats invalid_ticker with ticker field', () => {
      const err = makeAxiosError({
        detail: 'Invalid ticker symbol',
        code: 'invalid_ticker',
        fields: { ticker: 'INVALID' },
      })

      expect(formatTradeError(err)).toBe('Invalid ticker symbol: INVALID')
    })

    it('returns detail for invalid_quantity', () => {
      const err = makeAxiosError({
        detail: 'Quantity must be positive',
        code: 'invalid_quantity',
        fields: null,
      })

      expect(formatTradeError(err)).toBe('Quantity must be positive')
    })

    it('returns detail for market_data_unavailable', () => {
      const err = makeAxiosError(
        {
          detail: 'Unable to fetch market data',
          code: 'market_data_unavailable',
          fields: { reason: 'API rate limit exceeded' },
        },
        503
      )

      expect(formatTradeError(err)).toBe('Unable to fetch market data')
    })

    it('falls back to detail for unknown error codes', () => {
      const err = makeAxiosError({
        detail: 'Something went wrong',
        code: 'unknown_error_type',
        fields: null,
      })

      expect(formatTradeError(err)).toBe('Something went wrong')
    })

    it('falls back to AxiosError message when only an unmapped code is present', () => {
      // detail empty + unmapped code → fall through to axios message.
      const err = makeAxiosError({
        detail: '',
        code: 'unknown_error_type',
        fields: null,
      })

      expect(formatTradeError(err)).toBe('Request failed with status code 400')
    })
  })

  describe('plain string detail (no code)', () => {
    it('returns the detail string when no code is provided', () => {
      const err = makeAxiosError({ detail: 'Simple error message' })

      expect(formatTradeError(err)).toBe('Simple error message')
    })

    it('handles ticker_not_found with ticker field', () => {
      const err = makeAxiosError(
        {
          detail: 'Ticker not found',
          code: 'ticker_not_found',
          fields: { ticker: 'ZZZZ' },
        },
        404
      )

      expect(formatTradeError(err)).toBe('Ticker not found: ZZZZ')
    })
  })

  describe('fallback behavior', () => {
    it('handles AxiosError without response', () => {
      const err = new AxiosError('Network error')
      expect(formatTradeError(err)).toBe('Network error')
    })

    it('handles AxiosError without response data', () => {
      const err = makeAxiosError(undefined, 500)
      expect(formatTradeError(err)).toBe('Request failed with status code 500')
    })

    it('handles generic Error objects', () => {
      expect(formatTradeError(new Error('Generic error'))).toBe('Generic error')
    })

    it('handles non-Error objects', () => {
      expect(formatTradeError('string error')).toBe(
        'An unexpected error occurred'
      )
    })

    it('handles null/undefined', () => {
      expect(formatTradeError(null)).toBe('An unexpected error occurred')
      expect(formatTradeError(undefined)).toBe('An unexpected error occurred')
    })
  })
})
