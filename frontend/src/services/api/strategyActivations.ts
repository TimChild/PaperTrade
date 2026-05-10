/**
 * Strategy activations API functions
 *
 * Phase C1.4 — frontend client for the live-strategy-execution endpoints
 * shipped in PR #235 (entity) and PR #238 (service + API).
 *
 * Five endpoints across two routers:
 *
 * - `POST /strategies/{id}/activate` — link a strategy to a portfolio.
 * - `GET  /strategies/{id}/activation` — fetch activation linked to a strategy.
 * - `GET  /activations` — paginated list of the user's activations.
 * - `POST /activations/{id}/deactivate` — pause an activation.
 * - `POST /activations/{id}/run-now` — manual execution outside the cadence.
 */
import { isAxiosError } from 'axios'
import { apiClient } from './client'
import type {
  ActivateStrategyRequest,
  DeactivateActivationRequest,
  PaginatedResponse,
  RunNowResponse,
  StrategyActivationResponse,
} from './types'

export interface ListActivationsParams {
  limit?: number
  offset?: number
}

export const strategyActivationsApi = {
  /**
   * Activate a strategy for live execution against a portfolio.
   */
  activate: async (
    strategyId: string,
    body: ActivateStrategyRequest
  ): Promise<StrategyActivationResponse> => {
    const response = await apiClient.post<StrategyActivationResponse>(
      `/strategies/${strategyId}/activate`,
      body
    )
    return response.data
  },

  /**
   * Fetch the activation for a strategy.
   *
   * Returns `null` cleanly when the backend responds 404 — the absence of an
   * activation is a valid state for a strategy and should not surface as an
   * error in the UI.
   */
  getByStrategy: async (
    strategyId: string
  ): Promise<StrategyActivationResponse | null> => {
    try {
      const response = await apiClient.get<StrategyActivationResponse>(
        `/strategies/${strategyId}/activation`
      )
      return response.data
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  /**
   * List the current user's activations, paginated.
   */
  list: async (
    params?: ListActivationsParams
  ): Promise<PaginatedResponse<StrategyActivationResponse>> => {
    const response = await apiClient.get<
      PaginatedResponse<StrategyActivationResponse>
    >('/activations', { params })
    return response.data
  },

  /**
   * Pause an activation (sets `status=PAUSED`).
   */
  deactivate: async (
    activationId: string,
    reason?: string
  ): Promise<StrategyActivationResponse> => {
    const body: DeactivateActivationRequest = reason ? { reason } : {}
    const response = await apiClient.post<StrategyActivationResponse>(
      `/activations/${activationId}/deactivate`,
      body
    )
    return response.data
  },

  /**
   * Trigger immediate execution of an activation outside the cadence.
   *
   * Returns the post-run activation state plus the execution outcome
   * (`succeeded`, `trades`, `error`).
   */
  runNow: async (activationId: string): Promise<RunNowResponse> => {
    const response = await apiClient.post<RunNowResponse>(
      `/activations/${activationId}/run-now`
    )
    return response.data
  },
}
