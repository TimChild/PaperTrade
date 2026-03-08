/**
 * Backtests API functions
 */
import { apiClient } from './client'
import type { BacktestRunResponse, RunBacktestRequest } from './types'

export const backtestsApi = {
  list: async (): Promise<BacktestRunResponse[]> => {
    const response = await apiClient.get<BacktestRunResponse[]>('/backtests')
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
}
