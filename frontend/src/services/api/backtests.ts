/**
 * Backtests API functions
 */
import { apiClient } from './client'
import type {
  BacktestAgentInvocationResponse,
  BacktestRunResponse,
  ListBacktestAgentInvocationsParams,
  PaginatedResponse,
  RunBacktestRequest,
} from './types'

export interface ListBacktestsParams {
  limit?: number
  offset?: number
}

export const backtestsApi = {
  list: async (
    params?: ListBacktestsParams
  ): Promise<PaginatedResponse<BacktestRunResponse>> => {
    const response = await apiClient.get<
      PaginatedResponse<BacktestRunResponse>
    >('/backtests', { params })
    return response.data
  },

  getById: async (id: string): Promise<BacktestRunResponse> => {
    const response = await apiClient.get<BacktestRunResponse>(
      `/backtests/${id}`
    )
    return response.data
  },

  run: async (data: RunBacktestRequest): Promise<BacktestRunResponse> => {
    const response = await apiClient.post<BacktestRunResponse>(
      '/backtests',
      data
    )
    return response.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/backtests/${id}`)
  },

  /**
   * List the agent-invocation audit rows for one backtest run (Phase
   * L-4, Task #220). Chronological in simulation time. Backed by
   * `GET /api/v1/backtests/{id}/agent-invocations`.
   *
   * Used by the result-page "Agent invocations" section. The UI calls
   * this only when the parent run's `agent_invocation_mode` is not
   * `"none"` — a NONE-mode run will always return an empty page.
   */
  listAgentInvocations: async (
    backtestId: string,
    params?: ListBacktestAgentInvocationsParams
  ): Promise<PaginatedResponse<BacktestAgentInvocationResponse>> => {
    const response = await apiClient.get<
      PaginatedResponse<BacktestAgentInvocationResponse>
    >(`/backtests/${backtestId}/agent-invocations`, { params })
    return response.data
  },
}
