/**
 * React Query hooks for exploration tasks (Phase H1).
 *
 * The list hook accepts a `ListExplorationTasksParams` filter so the
 * dashboard can swap between status filters without re-creating a hook.
 * Mutations invalidate the list and the per-task cache so any open detail
 * view re-fetches after a status flip.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query'
import { explorationTasksApi } from '@/services/api/explorationTasks'
import type {
  CreateExplorationTaskRequest,
  ExplorationTaskResponse,
  ListExplorationTasksParams,
  PaginatedResponse,
} from '@/services/api/types'

/** Stable query keys used across the exploration-task feature. */
export const explorationTaskQueryKeys = {
  all: ['exploration-tasks'] as const,
  list: (params?: ListExplorationTasksParams) =>
    ['exploration-tasks', 'list', params] as const,
  byId: (taskId: string) => ['exploration-tasks', 'by-id', taskId] as const,
}

/**
 * Paginated list of exploration tasks. The dashboard typically passes
 * `scope: 'mine'` so the user sees their queue across all statuses.
 */
export function useExplorationTasks(
  params?: ListExplorationTasksParams
): UseQueryResult<PaginatedResponse<ExplorationTaskResponse>> {
  return useQuery<PaginatedResponse<ExplorationTaskResponse>>({
    queryKey: explorationTaskQueryKeys.list(params),
    queryFn: () => explorationTasksApi.list(params),
    staleTime: 30_000,
  })
}

/**
 * Single exploration task by id. Returns the full task with constraints
 * and findings expanded. Disabled when `taskId` is falsy.
 */
export function useExplorationTask(
  taskId: string
): UseQueryResult<ExplorationTaskResponse> {
  return useQuery<ExplorationTaskResponse>({
    queryKey: explorationTaskQueryKeys.byId(taskId),
    queryFn: () => explorationTasksApi.getById(taskId),
    staleTime: 30_000,
    enabled: Boolean(taskId),
  })
}

/**
 * Create a new exploration task. Invalidates the list cache so the new
 * task appears once the mutation settles.
 */
export function useCreateExplorationTask(): UseMutationResult<
  ExplorationTaskResponse,
  Error,
  CreateExplorationTaskRequest
> {
  const queryClient = useQueryClient()
  return useMutation<
    ExplorationTaskResponse,
    Error,
    CreateExplorationTaskRequest
  >({
    mutationFn: (data: CreateExplorationTaskRequest) =>
      explorationTasksApi.create(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: explorationTaskQueryKeys.all,
      })
    },
  })
}

/**
 * Abandon an exploration task (creator-only). Invalidates the list and
 * the per-task cache so any rendered detail view refetches.
 */
export function useAbandonExplorationTask(): UseMutationResult<
  void,
  Error,
  string
> {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (taskId: string) => explorationTasksApi.abandon(taskId),
    onSuccess: (_data, taskId) => {
      void queryClient.invalidateQueries({
        queryKey: explorationTaskQueryKeys.all,
      })
      void queryClient.invalidateQueries({
        queryKey: explorationTaskQueryKeys.byId(taskId),
      })
    },
  })
}
