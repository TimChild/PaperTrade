/**
 * Strategies API functions
 */
import { apiClient } from './client'
import type {
  StrategyResponse,
  CreateStrategyRequest,
  PaginatedResponse,
} from './types'

export interface ListStrategiesParams {
  limit?: number
  offset?: number
}

export const strategiesApi = {
  list: async (
    params?: ListStrategiesParams
  ): Promise<PaginatedResponse<StrategyResponse>> => {
    const response = await apiClient.get<PaginatedResponse<StrategyResponse>>(
      '/strategies',
      { params }
    )
    return response.data
  },

  getById: async (id: string): Promise<StrategyResponse> => {
    const response = await apiClient.get<StrategyResponse>(`/strategies/${id}`)
    return response.data
  },

  create: async (data: CreateStrategyRequest): Promise<StrategyResponse> => {
    const response = await apiClient.post<StrategyResponse>('/strategies', data)
    return response.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/strategies/${id}`)
  },
}
