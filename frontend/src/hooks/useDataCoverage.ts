/**
 * React Query hooks for admin data-coverage
 * (Phase J / Task #212 Layer 4 + Task #215 + Task #220).
 *
 * `useDataCoverage` powers the admin coverage page — polls every 30s
 * while the page is mounted (matches the §"Layer 4" spec) so the
 * operator sees backfill progress without a manual refresh.
 *
 * `useBackfillTicker` enqueues a "catch up" backfill via the admin POST
 * endpoint. Task #215: the payload is `{ ticker }` only — the backend
 * fills `[ZEBU_HISTORY_EPOCH, today]`. On success it invalidates the
 * coverage query so the updated row (including `backfill_status`)
 * surfaces within one poll interval.
 *
 * `usePinTicker` / `useUnpinTicker` cover the Task #220 Pin/Unpin
 * surface; both invalidate the coverage query on success so the
 * `is_watchlisted` flag round-trips within one poll interval.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query'
import { dataCoverageApi, watchlistApi } from '@/services/api/admin'
import type {
  BackfillRequest,
  BackfillResponse,
  DataCoverageResponse,
  PinTickerRequest,
  PinTickerResponse,
} from '@/services/api/types'

/** Stable query keys used across the data-coverage feature. */
export const dataCoverageQueryKeys = {
  all: ['admin', 'data-coverage'] as const,
  list: () => ['admin', 'data-coverage', 'list'] as const,
}

/** Poll cadence (ms) used by the coverage table per the Layer 4 spec. */
export const DATA_COVERAGE_POLL_INTERVAL_MS = 30_000

/**
 * Per-ticker data coverage list. Polls every 30 seconds while mounted
 * so the operator sees backfill progress in near-real-time.
 *
 * `staleTime` matches the poll interval so a focus/blur during the
 * window doesn't trigger an extra fetch.
 */
export function useDataCoverage(): UseQueryResult<DataCoverageResponse> {
  return useQuery<DataCoverageResponse>({
    queryKey: dataCoverageQueryKeys.list(),
    queryFn: () => dataCoverageApi.list(),
    refetchInterval: DATA_COVERAGE_POLL_INTERVAL_MS,
    staleTime: DATA_COVERAGE_POLL_INTERVAL_MS,
  })
}

/**
 * Enqueue a backfill task. Invalidates the coverage query on success
 * so the table re-fetches and the operator sees the freshly-queued row.
 */
export function useBackfillTicker(): UseMutationResult<
  BackfillResponse,
  Error,
  BackfillRequest
> {
  const queryClient = useQueryClient()
  return useMutation<BackfillResponse, Error, BackfillRequest>({
    mutationFn: (body) => dataCoverageApi.backfill(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dataCoverageQueryKeys.all,
      })
    },
  })
}

/**
 * Pin a ticker to the watchlist (Task #220). Invalidates the coverage
 * query on success so the `is_watchlisted=true` flag surfaces on the
 * row within one poll interval (or sooner via the invalidation refetch).
 *
 * Disabled-state pattern: callers gate the per-row Pin button on
 * `mutation.variables?.ticker === row.ticker` so only the in-flight
 * row is disabled, not the whole table (mirrors the PR #296 / #303
 * pattern).
 */
export function usePinTicker(): UseMutationResult<
  PinTickerResponse,
  Error,
  PinTickerRequest
> {
  const queryClient = useQueryClient()
  return useMutation<PinTickerResponse, Error, PinTickerRequest>({
    mutationFn: (body) => watchlistApi.add(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dataCoverageQueryKeys.all,
      })
    },
  })
}

/**
 * Unpin a ticker from the watchlist (Task #220). Invalidates the
 * coverage query on success so the `is_watchlisted=false` flag (or
 * the row's disappearance entirely, if the ticker had no other
 * active-set membership) surfaces within one poll interval.
 *
 * The mutation payload is the bare ticker symbol so the
 * `mutation.variables === row.ticker` per-row disabled-state pattern
 * works without wrapping in an object.
 */
export function useUnpinTicker(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (ticker) => watchlistApi.remove(ticker),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dataCoverageQueryKeys.all,
      })
    },
  })
}
