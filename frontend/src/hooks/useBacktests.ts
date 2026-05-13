/**
 * React Query hooks for backtests
 */
import { useCallback, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { backtestsApi } from '@/services/api/backtests'
import type {
  BacktestRunResponse,
  RunBacktestRequest,
} from '@/services/api/types'

export function useBacktests() {
  return useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestsApi.list(),
    staleTime: 30_000,
  })
}

export function useBacktest(id: string) {
  return useQuery({
    queryKey: ['backtests', id],
    queryFn: () => backtestsApi.getById(id),
    staleTime: 30_000,
    enabled: Boolean(id),
  })
}

/**
 * Phase J / Task #212 Layer 3: shape of the 503 body the backend
 * returns when historical data is being lazily fetched. Mirrors
 * ``handle_incomplete_historical_data`` in
 * ``backend/src/zebu/adapters/inbound/api/error_handlers.py``.
 *
 * Distinguishable from other 503 responses by the literal
 * ``status: "fetching"`` discriminator at the top level — the standard
 * error envelope uses ``detail / code / fields``, so this shape will
 * not collide.
 */
export interface FetchingResponseBody {
  status: 'fetching'
  ticker: string
  missing_range: {
    start: string
    end: string
  }
  eta_seconds: number
  retry_after_seconds: number
}

function isFetchingResponseBody(value: unknown): value is FetchingResponseBody {
  if (!value || typeof value !== 'object') return false
  const obj = value as Record<string, unknown>
  if (obj.status !== 'fetching') return false
  if (typeof obj.ticker !== 'string') return false
  if (typeof obj.retry_after_seconds !== 'number') return false
  return true
}

/**
 * Maximum number of consecutive "fetching" retries before surfacing the
 * 503 to the caller. The backfill is enqueued at HIGH priority — three
 * one-minute waits (~3 min total) is a generous bound for a single-
 * ticker, single-window fetch.
 */
const MAX_FETCHING_RETRIES = 3

/**
 * Sleep helper used by the auto-retry loop. Returns a promise that
 * resolves after ``ms`` milliseconds.
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Hook for running a backtest. Phase J / Task #212 Layer 3 — auto-
 * retries the mutation when the backend returns the 503 ``fetching``
 * shape, with a fixed delay (no exponential backoff — the backend's
 * ``retry_after_seconds`` is already a server-controlled bound).
 *
 * Returned state extends the standard ``useMutation`` shape with:
 *
 * * ``dataFetching`` — ``true`` while we are waiting on a backfill
 *   between retries. Distinct from ``isPending`` (which is true during
 *   the actual HTTP call); a caller can render "loading historical
 *   data for AAPL…" when ``dataFetching === true`` and a normal
 *   "running…" spinner when ``isPending === true``.
 * * ``fetchingTicker`` — the ticker we're waiting on, surfaced for UI
 *   copy. ``null`` outside an active fetch.
 * * ``mutate(args)`` — fire-and-forget; ``mutateAsync`` is preferred
 *   for callers that need to await the final outcome.
 */
export function useRunBacktest() {
  const queryClient = useQueryClient()
  const [dataFetching, setDataFetching] = useState(false)
  const [fetchingTicker, setFetchingTicker] = useState<string | null>(null)

  const mutationFn = useCallback(
    async (data: RunBacktestRequest): Promise<BacktestRunResponse> => {
      // Attempt 0 + up to MAX_FETCHING_RETRIES retries on 503-fetching.
      for (let attempt = 0; attempt <= MAX_FETCHING_RETRIES; attempt++) {
        try {
          const result = await backtestsApi.run(data)
          // Successful — clear any prior fetching state.
          setDataFetching(false)
          setFetchingTicker(null)
          return result
        } catch (err) {
          // Only auto-retry 503-fetching responses; everything else
          // propagates immediately.
          if (
            err instanceof AxiosError &&
            err.response?.status === 503 &&
            isFetchingResponseBody(err.response.data) &&
            attempt < MAX_FETCHING_RETRIES
          ) {
            const body = err.response.data
            setFetchingTicker(body.ticker)
            setDataFetching(true)
            await sleep(body.retry_after_seconds * 1000)
            continue
          }
          // Either not a fetching 503, or we've exhausted retries.
          setDataFetching(false)
          setFetchingTicker(null)
          throw err
        }
      }
      // Should be unreachable — the for-loop either returns or throws.
      setDataFetching(false)
      setFetchingTicker(null)
      throw new Error('useRunBacktest: exhausted retry budget')
    },
    []
  )

  const mutation = useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })

  return {
    ...mutation,
    dataFetching,
    fetchingTicker,
  }
}

export function useDeleteBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => backtestsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })
}
