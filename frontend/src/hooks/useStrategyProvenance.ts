/**
 * Strategy provenance hook (Phase G-2.1).
 *
 * Reverse-engineers a strategy's author identity from the existing activity
 * feed and exploration-task data — there's no `agent_author` column on the
 * `Strategy` entity, so we infer "agent vs human" by looking at the
 * `strategy_created` event for this strategy in the activity feed. If the
 * row's `actor_kind == 'api_key'`, the strategy was authored by an agent
 * and we surface the key's `actor_label`.
 *
 * We additionally probe the user's `DONE` exploration tasks for a finding
 * whose `recommended_strategy_id` matches — when present, the strategy was
 * recommended via that task and we expose enough to link back.
 *
 * Both probes are cached (TanStack Query) so multiple `StrategyCard` instances
 * on the strategy library page share fetches.
 */
import { useMemo } from 'react'
import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { activityApi } from '@/services/api/activity'
import { explorationTasksApi } from '@/services/api/explorationTasks'
import { extractTaskTitle } from '@/utils/explorationTaskTitle'
import type {
  ActivityEventResponse,
  ExplorationTaskResponse,
} from '@/services/api/types'

/**
 * Author kind for a strategy.
 *
 * - `agent` — strategy was created via an API-key-authenticated request
 *   (an agent / scheduled task / MCP client).
 * - `human` — strategy was created via a Clerk-authenticated request
 *   (a human in the UI).
 * - `unknown` — no matching `strategy_created` event was found (e.g. the
 *   activity feed page was too small to include it, or the event predates
 *   the activity-tracking system).
 */
export type StrategyAuthorKind = 'agent' | 'human' | 'unknown'

/**
 * The exploration task that recommended this strategy, if any.
 *
 * `taskTitle` is the human-readable title derived from the prompt's first
 * line — same convention used elsewhere in the exploration-task UI.
 */
export interface StrategyRecommendingTask {
  taskId: string
  taskTitle: string
}

/**
 * Resolved provenance for a single strategy.
 */
export interface StrategyProvenance {
  authorKind: StrategyAuthorKind
  /** API-key label when `authorKind == 'agent'`; `null` otherwise. */
  agentLabel: string | null
  /** Exploration task that recommended this strategy, if any. */
  recommendingTask: StrategyRecommendingTask | null
  /** Whether the underlying queries are still loading. */
  isLoading: boolean
}

/**
 * Find the strategy-creation event for a given strategy id in an
 * activity-feed page. The activity feed sorts DESC by `occurred_at` and the
 * lookup is by `subject_id`, so this is O(n) over the page items.
 */
function findStrategyCreatedEvent(
  events: ActivityEventResponse[],
  strategyId: string
): ActivityEventResponse | null {
  for (const event of events) {
    if (event.type === 'strategy_created' && event.subject_id === strategyId) {
      return event
    }
  }
  return null
}

/**
 * Find a DONE exploration task whose `findings.recommended_strategy_id`
 * matches the given strategy id.
 */
function findRecommendingTask(
  tasks: ExplorationTaskResponse[],
  strategyId: string
): ExplorationTaskResponse | null {
  for (const task of tasks) {
    if (task.findings?.recommended_strategy_id === strategyId) {
      return task
    }
  }
  return null
}

/**
 * Hook that returns provenance metadata for a single strategy.
 *
 * Both queries use long stale times — provenance only changes when a
 * strategy is freshly created (never afterwards), so caching aggressively
 * is correct.
 */
export function useStrategyProvenance(strategyId: string): StrategyProvenance {
  // Activity probe — uses the platform `MAX_PAGE_LIMIT` (100) so we
  // maximise the chance of finding the strategy_created row even when
  // there's a lot of recent activity. The event_type filter keeps the
  // server-side query narrow.
  const activityQuery: UseQueryResult<{
    items: ActivityEventResponse[]
  }> = useQuery({
    queryKey: ['strategy-provenance', 'activity', strategyId],
    queryFn: () =>
      activityApi.list({
        limit: 100,
        event_type: ['strategy_created'],
      }),
    staleTime: 5 * 60_000,
    enabled: Boolean(strategyId),
  })

  // Recommending-task probe — look at the user's DONE tasks. We don't need
  // pagination beyond the most recent page; in practice the relevant task
  // is the one that produced the strategy, and tasks are paginated DESC.
  const tasksQuery: UseQueryResult<{
    items: ExplorationTaskResponse[]
  }> = useQuery({
    queryKey: ['strategy-provenance', 'tasks', strategyId],
    queryFn: () =>
      explorationTasksApi.list({ scope: 'mine', status: 'DONE', limit: 100 }),
    staleTime: 5 * 60_000,
    enabled: Boolean(strategyId),
  })

  return useMemo<StrategyProvenance>(() => {
    const isLoading = activityQuery.isLoading || tasksQuery.isLoading

    const event = activityQuery.data
      ? findStrategyCreatedEvent(activityQuery.data.items, strategyId)
      : null

    let authorKind: StrategyAuthorKind = 'unknown'
    let agentLabel: string | null = null
    if (event !== null) {
      if (event.actor_kind === 'api_key') {
        authorKind = 'agent'
        agentLabel = event.actor_label
      } else {
        authorKind = 'human'
      }
    }

    const recommendingTask = tasksQuery.data
      ? findRecommendingTask(tasksQuery.data.items, strategyId)
      : null

    return {
      authorKind,
      agentLabel,
      recommendingTask: recommendingTask
        ? {
            taskId: recommendingTask.id,
            taskTitle: extractTaskTitle(recommendingTask.prompt),
          }
        : null,
      isLoading,
    }
  }, [
    activityQuery.data,
    activityQuery.isLoading,
    tasksQuery.data,
    tasksQuery.isLoading,
    strategyId,
  ])
}
