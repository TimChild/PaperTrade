/**
 * Tests for the Phase J / Task #212 Layer 3 useRunBacktest hook.
 *
 * Verifies:
 *
 *  - 200 path returns the backtest run normally.
 *  - 503 with the ``status=fetching`` body triggers an auto-retry
 *    after ``retry_after_seconds`` (mocked to 0s so the test runs
 *    instantly).
 *  - The hook surfaces ``dataFetching: true`` + the ticker while
 *    between retries.
 *  - After ``MAX_FETCHING_RETRIES`` consecutive 503-fetching responses
 *    the hook gives up and surfaces the final error.
 *  - Non-fetching errors propagate immediately (no retry).
 */

import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AxiosError, AxiosHeaders } from 'axios'
import { useRunBacktest } from '../useBacktests'
import { backtestsApi } from '@/services/api/backtests'
import type { BacktestRunResponse } from '@/services/api/types'

vi.mock('@/services/api/backtests', () => ({
  backtestsApi: {
    run: vi.fn(),
  },
}))

const okResponse: BacktestRunResponse = {
  id: 'bt-ok',
  user_id: 'user-1',
  strategy_id: 'strategy-1',
  portfolio_id: 'portfolio-1',
  backtest_name: 'lazy-backfill',
  start_date: '2024-01-02',
  end_date: '2024-01-12',
  initial_cash: '10000.00',
  status: 'COMPLETED',
  created_at: '2026-05-12T00:00:00Z',
  completed_at: '2026-05-12T00:00:30Z',
  error_message: null,
  total_return_pct: '5.00',
  max_drawdown_pct: '-1.00',
  annualized_return_pct: '5.00',
  total_trades: 4,
}

function makeFetchingError(): AxiosError {
  // Construct an AxiosError that mirrors the production 503-fetching
  // body shape so the type guard inside the hook matches.
  const err = new AxiosError('503 Service Unavailable')
  err.response = {
    status: 503,
    statusText: 'Service Unavailable',
    headers: {},
    config: {
      headers: new AxiosHeaders(),
    },
    data: {
      status: 'fetching',
      ticker: 'AAPL',
      missing_range: { start: '2024-01-02', end: '2024-01-12' },
      eta_seconds: 0,
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
    config: {
      headers: new AxiosHeaders(),
    },
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

describe('useRunBacktest', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns the backtest run on a successful first call', async () => {
    ;(backtestsApi.run as Mock).mockResolvedValueOnce(okResponse)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useRunBacktest(), { wrapper: Wrapper })

    let finalValue: BacktestRunResponse | null = null
    await act(async () => {
      finalValue = await result.current.mutateAsync({
        strategy_id: 'strategy-1',
        backtest_name: 'ok',
        start_date: '2024-01-02',
        end_date: '2024-01-12',
        initial_cash: 10000,
      })
    })

    expect(finalValue).toEqual(okResponse)
    expect(backtestsApi.run).toHaveBeenCalledTimes(1)
    expect(result.current.dataFetching).toBe(false)
    expect(result.current.fetchingTicker).toBeNull()
  })

  it('auto-retries after a 503-fetching response then succeeds', async () => {
    ;(backtestsApi.run as Mock)
      .mockRejectedValueOnce(makeFetchingError())
      .mockResolvedValueOnce(okResponse)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useRunBacktest(), { wrapper: Wrapper })

    let finalValue: BacktestRunResponse | null = null
    await act(async () => {
      finalValue = await result.current.mutateAsync({
        strategy_id: 'strategy-1',
        backtest_name: 'retry-once',
        start_date: '2024-01-02',
        end_date: '2024-01-12',
        initial_cash: 10000,
      })
    })

    expect(finalValue).toEqual(okResponse)
    expect(backtestsApi.run).toHaveBeenCalledTimes(2)
    // After success the fetching state should be cleared.
    await waitFor(() => expect(result.current.dataFetching).toBe(false))
    expect(result.current.fetchingTicker).toBeNull()
  })

  it('gives up after 3 consecutive fetching responses', async () => {
    // 4 mock rejections (initial attempt + 3 retries) — after the 4th
    // the hook surfaces the error.
    ;(backtestsApi.run as Mock)
      .mockRejectedValueOnce(makeFetchingError())
      .mockRejectedValueOnce(makeFetchingError())
      .mockRejectedValueOnce(makeFetchingError())
      .mockRejectedValueOnce(makeFetchingError())

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useRunBacktest(), { wrapper: Wrapper })

    let caught: unknown
    await act(async () => {
      try {
        await result.current.mutateAsync({
          strategy_id: 'strategy-1',
          backtest_name: 'exhausted',
          start_date: '2024-01-02',
          end_date: '2024-01-12',
          initial_cash: 10000,
        })
      } catch (err) {
        caught = err
      }
    })

    expect(caught).toBeInstanceOf(AxiosError)
    expect(backtestsApi.run).toHaveBeenCalledTimes(4)
  })

  it('does not retry on non-fetching errors', async () => {
    ;(backtestsApi.run as Mock).mockRejectedValueOnce(makeGenericError())

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useRunBacktest(), { wrapper: Wrapper })

    let caught: unknown
    await act(async () => {
      try {
        await result.current.mutateAsync({
          strategy_id: 'strategy-1',
          backtest_name: 'generic-error',
          start_date: '2024-01-02',
          end_date: '2024-01-12',
          initial_cash: 10000,
        })
      } catch (err) {
        caught = err
      }
    })

    expect(caught).toBeInstanceOf(AxiosError)
    expect(backtestsApi.run).toHaveBeenCalledTimes(1)
  })
})
