/**
 * React Query hooks for admin data-coverage (Phase J / Task #212 Layer 4).
 *
 * `useDataCoverage` powers the admin coverage page — polls every 30s
 * while the page is mounted (matches the §"Layer 4" spec) so the
 * operator sees backfill progress without a manual refresh.
 *
 * `useBackfillTicker` enqueues a backfill via the admin POST endpoint.
 * On success it invalidates the coverage query so the updated row
 * surfaces within one poll interval.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query'
import { dataCoverageApi } from '@/services/api/admin'
import type {
  BackfillRequest,
  BackfillResponse,
  DataCoverageResponse,
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
