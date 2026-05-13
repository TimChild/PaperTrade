/**
 * Tests for the Phase J / Task #214 usePortfolioBalance pricing-state
 * handling.
 *
 * Verifies:
 *
 *  - 200 with ``pricing_status === "ok"`` exposes the balance + ``ok``.
 *  - 503 with the ``status="fetching"`` body triggers an auto-retry
 *    after ``retry_after_seconds`` (mocked to 0s so the test runs
 *    instantly), then resolves to the eventual 200 response.
 *  - After ``MAX_PRICING_RETRIES`` consecutive 503-fetching responses
 *    the hook surfaces ``pricingStatus: "unavailable"`` with the stuck
 *    tickers.
 *  - Non-fetching errors propagate (no auto-retry).
 */

import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AxiosError, AxiosHeaders } from 'axios'
import { usePortfolioBalance } from '../usePortfolio'
import { portfoliosApi } from '@/services/api/portfolios'
import type { BalanceResponse } from '@/services/api/types'

vi.mock('@/services/api/portfolios', () => ({
  portfoliosApi: {
    getBalance: vi.fn(),
  },
}))

const okBalance: BalanceResponse = {
  cash_balance: '500.00',
  holdings_value: '1500.00',
  total_value: '2000.00',
  currency: 'USD',
  as_of: '2026-05-13T00:00:00Z',
  daily_change: '10.00',
  daily_change_percent: '0.50',
  pricing_status: 'ok',
  missing_tickers: [],
  retry_after_seconds: null,
}

function makeFetchingError(tickers: string[] = ['AAPL']): AxiosError {
  const err = new AxiosError('503 Service Unavailable')
  err.response = {
    status: 503,
    statusText: 'Service Unavailable',
    headers: {},
    config: { headers: new AxiosHeaders() },
    data: {
      status: 'fetching',
      missing_tickers: tickers,
      failed_reason: Object.fromEntries(
        tickers.map((t) => [t, 'market_data_unavailable'])
      ),
      retry_after_seconds: 0,
    },
  }
  return err
}

function makeGenericError(): AxiosError {
  const err = new AxiosError('500 Internal Server Error')
  err.response = {
    status: 500,
    statusText: 'Internal Server Error',
    headers: {},
    config: { headers: new AxiosHeaders() },
    data: { detail: 'oops' },
  }
  return err
}

function createWrapper(): {
  Wrapper: ({ children }: { children: React.ReactNode }) => React.JSX.Element
  client: QueryClient
} {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  const Wrapper = ({
    children,
  }: {
    children: React.ReactNode
  }): React.JSX.Element => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  return { Wrapper, client }
}

describe('usePortfolioBalance — Phase J / Task #214 pricing states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns the balance + pricingStatus="ok" on a successful first call', async () => {
    ;(portfoliosApi.getBalance as Mock).mockResolvedValueOnce(okBalance)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => usePortfolioBalance('p-1'), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.data).not.toBeNull())
    expect(result.current.pricingStatus).toBe('ok')
    expect(result.current.data?.total_value).toBe('2000.00')
    expect(result.current.missingTickers).toEqual([])
  })

  it('auto-retries after a 503-fetching response then succeeds', async () => {
    ;(portfoliosApi.getBalance as Mock)
      .mockRejectedValueOnce(makeFetchingError(['AAPL']))
      .mockResolvedValueOnce(okBalance)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => usePortfolioBalance('p-1'), {
      wrapper: Wrapper,
    })

    await waitFor(
      () => {
        expect(result.current.pricingStatus).toBe('ok')
        expect(result.current.data?.total_value).toBe('2000.00')
      },
      { timeout: 2000 }
    )
    expect(portfoliosApi.getBalance).toHaveBeenCalledTimes(2)
  })

  it('surfaces pricingStatus="unavailable" after the retry budget is exhausted', async () => {
    // 6 rejections: initial attempt + 5 retries — after the 6th the
    // hook surfaces the unavailable state.
    const errs = Array.from({ length: 6 }, () =>
      makeFetchingError(['AAPL', 'MSFT'])
    )
    const mock = portfoliosApi.getBalance as Mock
    mock.mockReset()
    errs.forEach((e) => mock.mockRejectedValueOnce(e))

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => usePortfolioBalance('p-1'), {
      wrapper: Wrapper,
    })

    await waitFor(
      () => expect(result.current.pricingStatus).toBe('unavailable'),
      { timeout: 5000 }
    )
    expect(result.current.missingTickers).toEqual(['AAPL', 'MSFT'])
    expect(result.current.data).toBeNull()
  })

  it('propagates non-fetching errors without retrying', async () => {
    ;(portfoliosApi.getBalance as Mock).mockRejectedValueOnce(
      makeGenericError()
    )

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => usePortfolioBalance('p-1'), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(portfoliosApi.getBalance).toHaveBeenCalledTimes(1)
    expect(result.current.pricingStatus).toBe('ok')
  })
})
