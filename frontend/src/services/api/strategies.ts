/**
 * Strategies API functions
 */
import { apiClient } from './client'
import type { StrategyResponse, CreateStrategyRequest } from './types'

export const strategiesApi = {
  list: async (): Promise<StrategyResponse[]> => {
    const response = await apiClient.get<StrategyResponse[]>('/strategies')
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
