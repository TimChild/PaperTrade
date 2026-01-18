/**
 * Tests for useHistoricalPriceQuery hook
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useHistoricalPriceQuery } from '../useHistoricalPriceQuery'
import * as pricesApi from '@/services/api/prices'
import type { PricePoint } from '@/types/price'

// Mock the API
vi.mock('@/services/api/prices', () => ({
  getHistoricalPrice: vi.fn(),
}))

const mockPricePoint: PricePoint = {
  ticker: { symbol: 'AAPL' },
  price: {
    amount: 150.25,
    currency: 'USD',
  },
  timestamp: '2026-01-10T16:00:00Z',
  source: 'database',
  interval: '1day',
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useHistoricalPriceQuery', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches historical price for valid ticker and date', async () => {
    vi.mocked(pricesApi.getHistoricalPrice).mockResolvedValue(mockPricePoint)

    const { result } = renderHook(
      () => useHistoricalPriceQuery('AAPL', '2026-01-10'),
      {
        wrapper: createWrapper(),
      }
    )

    // Initially loading
    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()

    // Wait for query to complete
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockPricePoint)
    expect(pricesApi.getHistoricalPrice).toHaveBeenCalledWith(
      'AAPL',
      '2026-01-10'
    )
  })

  it('disables query when ticker is empty', () => {
    const { result } = renderHook(
      () => useHistoricalPriceQuery('', '2026-01-10'),
      {
        wrapper: createWrapper(),
      }
    )

    expect(result.current.isPending).toBe(true)
    expect(result.current.fetchStatus).toBe('idle')
    expect(pricesApi.getHistoricalPrice).not.toHaveBeenCalled()
  })

  it('disables query when date is empty', () => {
    const { result } = renderHook(() => useHistoricalPriceQuery('AAPL', ''), {
      wrapper: createWrapper(),
    })

    expect(result.current.isPending).toBe(true)
    expect(result.current.fetchStatus).toBe('idle')
    expect(pricesApi.getHistoricalPrice).not.toHaveBeenCalled()
  })

  it('retries on other errors', async () => {
    const error = new Error('Network error')
    vi.mocked(pricesApi.getHistoricalPrice).mockRejectedValue(error)

    const { result } = renderHook(
      () => useHistoricalPriceQuery('AAPL', '2026-01-10'),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => expect(result.current.isError).toBe(true), {
      timeout: 5000,
    })

    // Should retry up to 2 times (initial + 2 retries = 3 total calls)
    expect(pricesApi.getHistoricalPrice).toHaveBeenCalledTimes(3)
    expect(result.current.error).toBeDefined()
  })

  it('caches results with correct query key', async () => {
    vi.mocked(pricesApi.getHistoricalPrice).mockResolvedValue(mockPricePoint)

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0,
        },
      },
    })

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(
      () => useHistoricalPriceQuery('AAPL', '2026-01-10'),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    // Check that the cache has the expected key
    const cachedData = queryClient.getQueryData([
      'price-historical',
      'AAPL',
      '2026-01-10',
    ])
    expect(cachedData).toEqual(mockPricePoint)
  })

  it('does not retry on 404 errors', async () => {
    const error = {
      response: { status: 404 },
    }
    vi.mocked(pricesApi.getHistoricalPrice).mockRejectedValue(error)

    const { result } = renderHook(
      () => useHistoricalPriceQuery('INVALID', '2026-01-10'),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => expect(result.current.isError).toBe(true))

    // Should only call once (no retries)
    expect(pricesApi.getHistoricalPrice).toHaveBeenCalledTimes(1)
  })

  it('does not retry on 503 errors', async () => {
    const error = {
      response: { status: 503 },
    }
    vi.mocked(pricesApi.getHistoricalPrice).mockRejectedValue(error)

    const { result } = renderHook(
      () => useHistoricalPriceQuery('AAPL', '2026-01-10'),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => expect(result.current.isError).toBe(true))

    // Should only call once (no retries)
    expect(pricesApi.getHistoricalPrice).toHaveBeenCalledTimes(1)
  })
})
