import apiClient from './api'
import type { HealthResponse } from '@/types/api'

export const healthService = {
  async check(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health')
    return response.data
  },
}
