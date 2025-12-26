import axios from 'axios'
import type { HealthResponse } from '@/types/api'

// Health check calls /health directly (proxied to backend in dev)
const healthClient = axios.create({
  timeout: 5000,
})

export const healthService = {
  async check(): Promise<HealthResponse> {
    const response = await healthClient.get<HealthResponse>('/health')
    return response.data
  },
}
