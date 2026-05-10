/**
 * Exploration tasks API functions (Phase H1).
 *
 * Frontend client for the human-queued, agent-claimed task queue. Backend
 * source of truth: `backend/src/zebu/adapters/inbound/api/exploration_tasks.py`.
 *
 * The list endpoint supports two scopes:
 *
 * - `scope=all` (default) — global queue, defaults to `OPEN` so a bare
 *   `GET /exploration-tasks` returns the claimable backlog.
 * - `scope=mine` — only tasks created by the current user. The H1 dashboard
 *   uses this scope so the human sees their queue regardless of status.
 *
 * Abandon is implemented server-side as `DELETE /exploration-tasks/{id}` —
 * it's a hard delete restricted to the creator.
 */
import { apiClient } from './client'
import type {
  CreateExplorationTaskRequest,
  ExplorationTaskResponse,
  ListExplorationTasksParams,
  PaginatedResponse,
} from './types'

export const explorationTasksApi = {
  /**
   * List exploration tasks. See `ListExplorationTasksParams` for the
   * `scope` / `status` semantics — the H1 list view passes `scope=mine`.
   */
  list: async (
    params?: ListExplorationTasksParams
  ): Promise<PaginatedResponse<ExplorationTaskResponse>> => {
    const response = await apiClient.get<
      PaginatedResponse<ExplorationTaskResponse>
    >('/exploration-tasks', { params })
    return response.data
  },

  /**
   * Fetch a single exploration task by id. 404s surface as a query error
   * the caller can handle via TanStack Query's `error` state.
   */
  getById: async (taskId: string): Promise<ExplorationTaskResponse> => {
    const response = await apiClient.get<ExplorationTaskResponse>(
      `/exploration-tasks/${taskId}`
    )
    return response.data
  },

  /**
   * Create a new exploration task. The caller becomes the task's owner
   * (`created_by`); the task starts in `OPEN` status.
   */
  create: async (
    data: CreateExplorationTaskRequest
  ): Promise<ExplorationTaskResponse> => {
    const response = await apiClient.post<ExplorationTaskResponse>(
      '/exploration-tasks',
      data
    )
    return response.data
  },

  /**
   * Abandon a task. Backend implements this as `DELETE` (hard delete);
   * only the creator may call it. The endpoint is currently allowed in any
   * status, though the UI only surfaces the action while the task is
   * `OPEN` to match the spec.
   */
  abandon: async (taskId: string): Promise<void> => {
    await apiClient.delete(`/exploration-tasks/${taskId}`)
  },
}
