/**
 * API Keys service — thin wrappers over the Clerk-gated `/api-keys` router.
 *
 * The mint endpoint returns the raw key exactly once; callers are responsible
 * for surfacing it to the user immediately and never re-rendering it.
 *
 * Backend contract: `backend/src/zebu/adapters/inbound/api/api_keys.py`.
 */
import { apiClient } from './client'
import type {
  ApiKeyListResponse,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
} from './types'

export const apiKeysApi = {
  list: async (): Promise<ApiKeyListResponse> => {
    const response = await apiClient.get<ApiKeyListResponse>('/api-keys')
    return response.data
  },

  create: async (data: CreateApiKeyRequest): Promise<CreateApiKeyResponse> => {
    const response = await apiClient.post<CreateApiKeyResponse>(
      '/api-keys',
      data
    )
    return response.data
  },

  revoke: async (id: string): Promise<void> => {
    await apiClient.delete(`/api-keys/${id}`)
  },
}
