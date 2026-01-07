/**
 * Unit tests for usePriceQuery hooks
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import {
  usePriceQuery,
  useBatchPricesQuery,
  usePriceStaleness,
} from '../usePriceQuery'
import type { PricePoint } from '@/types/price'
import React from 'react'

const API_BASE_URL = 'http://localhost:8000/api/v1'

// Mock server setup
const server = setupServer(
  // Get current price for a ticker
  http.get(`${API_BASE_URL}/prices/:ticker`, ({ params }) => {
    const { ticker } = params

    const mockPrices: Record<string, number> = {
      AAPL: 192.53,
      GOOGL: 140.93,
      MSFT: 374.58,
    }

    const price = mockPrices[ticker as string]
    if (!price) {
      return HttpResponse.json(
        { detail: `Ticker ${ticker} not found` },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      ticker: { symbol: ticker },
      price: { amount: price, currency: 'USD' },
      timestamp: new Date().toISOString(),
      source: 'database',
      interval: 'real-time',
    })
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries for faster tests
        gcTime: 0, // Disable caching for test isolation
      },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('usePriceQuery', () => {
  it('fetches price successfully for valid ticker', async () => {
    const { result } = renderHook(() => usePriceQuery('AAPL'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toMatchObject({
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      source: 'database',
      interval: 'real-time',
    })
  })

  it.skip('handles ticker not found error', async () => {
    const { result } = renderHook(() => usePriceQuery('INVALID'), {
      wrapper: createWrapper(),
    })

    await waitFor(
      () => {
        expect(result.current.isError).toBe(true)
      },
      { timeout: 3000 }
    )
    expect(result.current.error).toBeTruthy()
  })

  it('does not fetch when ticker is empty', () => {
    const { result } = renderHook(() => usePriceQuery(''), {
      wrapper: createWrapper(),
    })

    expect(result.current.isFetching).toBe(false)
    expect(result.current.data).toBeUndefined()
  })
})

describe('useBatchPricesQuery', () => {
  it('fetches prices for multiple tickers successfully', async () => {
    const { result } = renderHook(
      () => useBatchPricesQuery(['AAPL', 'GOOGL', 'MSFT']),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toBeInstanceOf(Map)
    expect(result.current.data?.size).toBe(3)
    expect(result.current.data?.get('AAPL')).toMatchObject({
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
    })
    expect(result.current.data?.get('GOOGL')).toMatchObject({
      ticker: { symbol: 'GOOGL' },
      price: { amount: 140.93, currency: 'USD' },
    })
  })

  it('handles partial failures gracefully', async () => {
    const { result } = renderHook(
      () => useBatchPricesQuery(['AAPL', 'INVALID', 'MSFT']),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    // Should succeed overall even if some tickers fail
    expect(result.current.data).toBeInstanceOf(Map)
    expect(result.current.data?.size).toBe(2) // Only AAPL and MSFT
    expect(result.current.data?.has('AAPL')).toBe(true)
    expect(result.current.data?.has('MSFT')).toBe(true)
    expect(result.current.data?.has('INVALID')).toBe(false)
  })

  it('does not fetch when tickers array is empty', () => {
    const { result } = renderHook(() => useBatchPricesQuery([]), {
      wrapper: createWrapper(),
    })

    expect(result.current.isFetching).toBe(false)
    expect(result.current.data).toBeUndefined()
  })

  it('returns empty map when all tickers fail', async () => {
    const { result } = renderHook(
      () => useBatchPricesQuery(['INVALID1', 'INVALID2']),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toBeInstanceOf(Map)
    expect(result.current.data?.size).toBe(0)
  })
})

describe('usePriceStaleness', () => {
  it('returns "Just now" for recent prices', () => {
    const pricePoint: PricePoint = {
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      timestamp: new Date().toISOString(),
      source: 'database',
      interval: 'real-time',
    }

    const { result } = renderHook(() => usePriceStaleness(pricePoint))
    expect(result.current).toBe('Just now')
  })

  it('returns minutes for slightly old prices', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000)
    const pricePoint: PricePoint = {
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      timestamp: fiveMinutesAgo.toISOString(),
      source: 'database',
      interval: 'real-time',
    }

    const { result } = renderHook(() => usePriceStaleness(pricePoint))
    expect(result.current).toBe('5 minutes ago')
  })

  it('returns single minute without plural', () => {
    const oneMinuteAgo = new Date(Date.now() - 1 * 60 * 1000)
    const pricePoint: PricePoint = {
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      timestamp: oneMinuteAgo.toISOString(),
      source: 'database',
      interval: 'real-time',
    }

    const { result } = renderHook(() => usePriceStaleness(pricePoint))
    expect(result.current).toBe('1 minute ago')
  })

  it('returns hours for older prices', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000)
    const pricePoint: PricePoint = {
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      timestamp: twoHoursAgo.toISOString(),
      source: 'database',
      interval: 'real-time',
    }

    const { result } = renderHook(() => usePriceStaleness(pricePoint))
    expect(result.current).toBe('2 hours ago')
  })

  it('returns single hour without plural', () => {
    const oneHourAgo = new Date(Date.now() - 1 * 60 * 60 * 1000)
    const pricePoint: PricePoint = {
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      timestamp: oneHourAgo.toISOString(),
      source: 'database',
      interval: 'real-time',
    }

    const { result } = renderHook(() => usePriceStaleness(pricePoint))
    expect(result.current).toBe('1 hour ago')
  })

  it('returns days for very old prices', () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000)
    const pricePoint: PricePoint = {
      ticker: { symbol: 'AAPL' },
      price: { amount: 192.53, currency: 'USD' },
      timestamp: threeDaysAgo.toISOString(),
      source: 'database',
      interval: 'real-time',
    }

    const { result } = renderHook(() => usePriceStaleness(pricePoint))
    expect(result.current).toBe('3 days ago')
  })

  it('returns null for undefined pricePoint', () => {
    const { result } = renderHook(() => usePriceStaleness(undefined))
    expect(result.current).toBeNull()
  })
})
