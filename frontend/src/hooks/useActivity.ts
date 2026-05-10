/**
 * Recent-activity feed hook (Phase H2).
 *
 * Fetches the activity feed via TanStack Query. The feed is short-lived
 * data (it changes frequently as new events fire), so the staleTime is
 * deliberately conservative — 10 s is long enough to avoid hammering
 * the backend on UI re-renders but short enough that a fresh trade
 * shows up almost immediately when the panel re-mounts.
 */
import { useQuery } from '@tanstack/react-query'
import { activityApi } from '@/services/api'
import type { ListActivityParams } from '@/services/api/types'

const ACTIVITY_STALE_TIME_MS = 10_000

/**
 * Hook to fetch the recent-activity feed for the current user.
 *
 * @param params Query / pagination params. Pass `undefined` for the
 *   default first page; pass an explicit object to filter.
 */
export function useActivity(params?: ListActivityParams) {
  return useQuery({
    queryKey: ['activity', params],
    queryFn: () => activityApi.list(params),
    staleTime: ACTIVITY_STALE_TIME_MS,
  })
}
