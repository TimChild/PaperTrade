/**
 * Unit tests for price error parsing utilities
 */
import { describe, it, expect } from 'vitest'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { parseApiError, isApiError } from '@/utils/priceErrors'

describe('parseApiError', () => {
  it('parses 503 rate limit error', () => {
    const axiosError = new AxiosError(
      'Request failed',
      '503',
      {} as InternalAxiosRequestConfig,
      {},
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
        data: {
          detail: 'Rate limit exceeded for Alpha Vantage API',
        },
      }
    )

    const result = parseApiError(axiosError, 'AAPL')

    expect(result.type).toBe('rate_limit')
    expect(result.message).toBe(
      'Market data temporarily unavailable due to high demand'
    )
    expect(result.retryAfter).toBe(60)
    expect(result.details).toContain('Rate limit')
  })

  it('parses 503 server error (non-rate-limit)', () => {
    const axiosError = new AxiosError(
      'Request failed',
      '503',
      {} as InternalAxiosRequestConfig,
      {},
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
        data: {
          detail: 'Service temporarily down for maintenance',
        },
      }
    )

    const result = parseApiError(axiosError)

    expect(result.type).toBe('server_error')
    expect(result.message).toBe('Service temporarily unavailable')
  })

  it('parses 404 not found error with ticker', () => {
    const axiosError = new AxiosError(
      'Request failed',
      '404',
      {} as InternalAxiosRequestConfig,
      {},
      {
        status: 404,
        statusText: 'Not Found',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
        data: {
          detail: 'Ticker INVALID not found',
        },
      }
    )

    const result = parseApiError(axiosError, 'INVALID')

    expect(result.type).toBe('not_found')
    expect(result.message).toBe('No data found for INVALID')
  })

  it('parses 404 not found error without ticker', () => {
    const axiosError = new AxiosError(
      'Request failed',
      '404',
      {} as InternalAxiosRequestConfig,
      {},
      {
        status: 404,
        statusText: 'Not Found',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
        data: {
          detail: 'Resource not found',
        },
      }
    )

    const result = parseApiError(axiosError)

    expect(result.type).toBe('not_found')
    expect(result.message).toBe('No data found for this ticker')
  })

  it('parses 500 server error', () => {
    const axiosError = new AxiosError(
      'Request failed',
      '500',
      {} as InternalAxiosRequestConfig,
      {},
      {
        status: 500,
        statusText: 'Internal Server Error',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
        data: {
          detail: 'Database connection failed',
        },
      }
    )

    const result = parseApiError(axiosError)

    expect(result.type).toBe('server_error')
    expect(result.message).toBe('Server error occurred')
    expect(result.details).toBe('Database connection failed')
  })

  it('parses network timeout error', () => {
    const error = new Error('Network timeout error')

    const result = parseApiError(error)

    expect(result.type).toBe('network_error')
    expect(result.message).toBe('Unable to connect to server')
  })

  it('parses unknown axios error status', () => {
    const axiosError = new AxiosError(
      'Request failed',
      '418',
      {} as InternalAxiosRequestConfig,
      {},
      {
        status: 418,
        statusText: "I'm a teapot",
        headers: {},
        config: {} as InternalAxiosRequestConfig,
        data: {
          detail: 'Teapot error',
        },
      }
    )

    const result = parseApiError(axiosError)

    expect(result.type).toBe('unknown')
    expect(result.message).toBe('Request failed')
  })

  it('parses generic Error', () => {
    const error = new Error('Something went wrong')

    const result = parseApiError(error)

    expect(result.type).toBe('unknown')
    expect(result.message).toBe('Something went wrong')
  })

  it('parses non-Error object', () => {
    const result = parseApiError('string error')

    expect(result.type).toBe('unknown')
    expect(result.message).toBe('An unexpected error occurred')
  })
})

describe('isApiError', () => {
  it('returns true for valid ApiError', () => {
    const error = {
      type: 'rate_limit' as const,
      message: 'Too many requests',
      retryAfter: 60,
    }

    expect(isApiError(error)).toBe(true)
  })

  it('returns false for Error object', () => {
    const error = new Error('Test error')

    expect(isApiError(error)).toBe(false)
  })

  it('returns false for string', () => {
    expect(isApiError('error string')).toBe(false)
  })

  it('returns false for null', () => {
    expect(isApiError(null)).toBe(false)
  })

  it('returns false for object missing type', () => {
    const error = {
      message: 'Error message',
    }

    expect(isApiError(error)).toBe(false)
  })

  it('returns false for object missing message', () => {
    const error = {
      type: 'rate_limit',
    }

    expect(isApiError(error)).toBe(false)
  })
})
