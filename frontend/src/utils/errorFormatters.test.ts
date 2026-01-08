/**
 * Tests for error formatting utilities
 */
import { describe, it, expect } from 'vitest'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { formatTradeError } from './errorFormatters'
import type { ErrorResponse, StructuredErrorDetail } from '@/services/api/types'

describe('formatTradeError', () => {
  describe('structured errors', () => {
    it('should format insufficient_funds error with all details', () => {
      const errorDetail: StructuredErrorDetail = {
        type: 'insufficient_funds',
        message:
          'Insufficient funds. You have $739.67 but need $1,301.65. Shortfall: $561.98',
        available: 739.67,
        required: 1301.65,
        shortfall: 561.98,
      }

      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed with status code 400',
        '400',
        undefined,
        undefined,
        {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: errorDetail },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe(
        'Insufficient funds. You have $739.67 but need $1,301.65 (shortfall: $561.98)'
      )
    })

    it('should format insufficient_funds error with missing fields', () => {
      const errorDetail: StructuredErrorDetail = {
        type: 'insufficient_funds',
        message: 'Insufficient funds',
      }

      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed',
        '400',
        undefined,
        undefined,
        {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: errorDetail },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe('Insufficient funds')
    })

    it('should format insufficient_shares error with all details', () => {
      const errorDetail: StructuredErrorDetail = {
        type: 'insufficient_shares',
        message: 'Insufficient shares',
        ticker: 'AAPL',
        available: 50,
        required: 100,
        shortfall: 50,
      }

      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed',
        '400',
        undefined,
        undefined,
        {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: errorDetail },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe(
        'Insufficient shares. You have 50 shares of AAPL but need 100 (shortfall: 50)'
      )
    })

    it('should format insufficient_shares error with missing fields', () => {
      const errorDetail: StructuredErrorDetail = {
        type: 'insufficient_shares',
        message: 'Not enough shares',
      }

      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed',
        '400',
        undefined,
        undefined,
        {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: errorDetail },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe('Not enough shares')
    })

    it('should format invalid_ticker error', () => {
      const errorDetail: StructuredErrorDetail = {
        type: 'invalid_ticker',
        message: 'Invalid ticker symbol',
        ticker: 'INVALID',
      }

      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed',
        '400',
        undefined,
        undefined,
        {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: errorDetail },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe('Invalid ticker symbol: INVALID')
    })

    it('should format invalid_quantity error', () => {
      const errorDetail: StructuredErrorDetail = {
        type: 'invalid_quantity',
        message: 'Quantity must be positive',
      }

      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed',
        '400',
        undefined,
        undefined,
        {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: errorDetail },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe('Quantity must be positive')
    })

    it('should format market_data_unavailable error', () => {
      const errorDetail: StructuredErrorDetail = {
        type: 'market_data_unavailable',
        message: 'Unable to fetch market data',
        reason: 'API rate limit exceeded',
      }

      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed',
        '503',
        undefined,
        undefined,
        {
          status: 503,
          statusText: 'Service Unavailable',
          data: { detail: errorDetail },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe('Unable to fetch market data')
    })

    it('should handle unknown error types with message', () => {
      const errorDetail: StructuredErrorDetail = {
        type: 'unknown_error_type',
        message: 'Something went wrong',
      }

      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed',
        '400',
        undefined,
        undefined,
        {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: errorDetail },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe('Something went wrong')
    })

    it('should handle unknown error types without message', () => {
      const errorDetail = {
        type: 'unknown_error_type',
      } as StructuredErrorDetail

      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed',
        '400',
        undefined,
        undefined,
        {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: errorDetail },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe('An error occurred')
    })
  })

  describe('simple string errors', () => {
    it('should handle simple string error detail', () => {
      const axiosError = new AxiosError<ErrorResponse>(
        'Request failed',
        '400',
        undefined,
        undefined,
        {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: 'Simple error message' },
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe('Simple error message')
    })
  })

  describe('fallback behavior', () => {
    it('should handle AxiosError without response', () => {
      const axiosError = new AxiosError('Network error')

      const result = formatTradeError(axiosError)
      expect(result).toBe('Network error')
    })

    it('should handle AxiosError without response data', () => {
      const axiosError = new AxiosError(
        'Request failed',
        '500',
        undefined,
        undefined,
        {
          status: 500,
          statusText: 'Internal Server Error',
          data: undefined,
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        }
      )

      const result = formatTradeError(axiosError)
      expect(result).toBe('Request failed')
    })

    it('should handle generic Error objects', () => {
      const error = new Error('Generic error')

      const result = formatTradeError(error)
      expect(result).toBe('Generic error')
    })

    it('should handle non-Error objects', () => {
      const result = formatTradeError('string error')
      expect(result).toBe('An unexpected error occurred')
    })

    it('should handle null/undefined', () => {
      expect(formatTradeError(null)).toBe('An unexpected error occurred')
      expect(formatTradeError(undefined)).toBe('An unexpected error occurred')
    })
  })
})
