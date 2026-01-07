/**
 * Debug API functions
 */
import { apiClient } from './client'

export interface DebugEnvironment {
  environment: string
  python_version: string
  fastapi_version: string
}

export interface DebugDatabase {
  connected: boolean
  url: string
  pool_size: number
}

export interface DebugRedis {
  connected: boolean
  url: string
  ping: string
}

export interface DebugApiKey {
  present: boolean
  prefix?: string
  length?: number
}

export interface DebugApiKeys {
  clerk_secret_key: DebugApiKey
  alpha_vantage_api_key: DebugApiKey
}

export interface DebugService {
  configured: boolean
  last_check: string
}

export interface DebugServices {
  clerk?: DebugService
  alpha_vantage?: DebugService
}

export interface DebugInfo {
  environment: DebugEnvironment
  database: DebugDatabase
  redis: DebugRedis
  api_keys: DebugApiKeys
  services: DebugServices
}

export const debugApi = {
  /**
   * Get debug information from the backend
   */
  getInfo: async (): Promise<DebugInfo> => {
    const response = await apiClient.get<DebugInfo>('/debug')
    return response.data
  },
}
