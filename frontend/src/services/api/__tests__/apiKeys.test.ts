/**
 * Tests for apiKeysApi
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiKeysApi } from '../apiKeys'
import { apiClient } from '../client'
import type {
  ApiKeyListResponse,
  ApiKeySummary,
  CreateApiKeyResponse,
} from '../types'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockSummary: ApiKeySummary = {
  id: '00000000-0000-0000-0000-000000000001',
  label: 'claude-code-laptop',
  scopes: ['read', 'trade'],
  created_at: '2024-01-01T00:00:00Z',
  last_used_at: null,
  revoked_at: null,
  expires_at: null,
  is_active: true,
}

describe('apiKeysApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('fetches all API keys', async () => {
      const list: ApiKeyListResponse = { items: [mockSummary], total: 1 }
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: list })

      const result = await apiKeysApi.list()

      expect(apiClient.get).toHaveBeenCalledWith('/api-keys')
      expect(result).toEqual(list)
    })

    it('returns an empty list when no keys exist', async () => {
      const list: ApiKeyListResponse = { items: [], total: 0 }
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: list })

      const result = await apiKeysApi.list()

      expect(result.items).toEqual([])
      expect(result.total).toBe(0)
    })
  })

  describe('create', () => {
    it('mints a new key and returns the raw secret', async () => {
      const response: CreateApiKeyResponse = {
        id: '00000000-0000-0000-0000-000000000002',
        label: 'agent-bot',
        scopes: ['read'],
        raw_key: 'zk_test_abcdef0123456789',
        created_at: '2024-01-01T00:00:00Z',
        expires_at: null,
      }
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: response })

      const result = await apiKeysApi.create({
        label: 'agent-bot',
        scopes: ['read'],
      })

      expect(apiClient.post).toHaveBeenCalledWith('/api-keys', {
        label: 'agent-bot',
        scopes: ['read'],
      })
      expect(result.raw_key).toBe('zk_test_abcdef0123456789')
    })

    it('forwards expires_at when provided', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({
        data: {
          id: 'id',
          label: 'temp',
          scopes: ['read'],
          raw_key: 'zk_x',
          created_at: '2024-01-01T00:00:00Z',
          expires_at: '2024-12-31T23:59:59.000Z',
        },
      })

      await apiKeysApi.create({
        label: 'temp',
        scopes: ['read'],
        expires_at: '2024-12-31T23:59:59.000Z',
      })

      expect(apiClient.post).toHaveBeenCalledWith('/api-keys', {
        label: 'temp',
        scopes: ['read'],
        expires_at: '2024-12-31T23:59:59.000Z',
      })
    })
  })

  describe('revoke', () => {
    it('deletes an API key by id', async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: undefined })

      await apiKeysApi.revoke('00000000-0000-0000-0000-000000000001')

      expect(apiClient.delete).toHaveBeenCalledWith(
        '/api-keys/00000000-0000-0000-0000-000000000001'
      )
    })
  })
})
