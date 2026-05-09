/**
 * Tests for strategiesApi
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { strategiesApi } from '../strategies'
import { apiClient } from '../client'
import type { PaginatedResponse, StrategyResponse } from '../types'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockStrategy: StrategyResponse = {
  id: 'strategy-1',
  user_id: 'user-1',
  name: 'Test Strategy',
  strategy_type: 'BUY_AND_HOLD',
  tickers: ['AAPL', 'MSFT'],
  parameters: { allocation: { AAPL: 0.5, MSFT: 0.5 } },
  created_at: '2024-01-01T00:00:00Z',
}

function paginate(
  items: StrategyResponse[],
  limit = 20,
  offset = 0
): PaginatedResponse<StrategyResponse> {
  return {
    items,
    total: items.length,
    limit,
    offset,
    has_more: false,
  }
}

describe('strategiesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('fetches all strategies as a paginated envelope', async () => {
      const page = paginate([mockStrategy])
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: page })

      const result = await strategiesApi.list()

      expect(apiClient.get).toHaveBeenCalledWith('/strategies', {
        params: undefined,
      })
      expect(result).toEqual(page)
      expect(result.items).toEqual([mockStrategy])
    })

    it('returns an empty page when no strategies exist', async () => {
      const page = paginate([])
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: page })

      const result = await strategiesApi.list()

      expect(result.items).toEqual([])
      expect(result.total).toBe(0)
      expect(result.has_more).toBe(false)
    })

    it('forwards limit/offset query params', async () => {
      const page = paginate([mockStrategy], 10, 5)
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: page })

      await strategiesApi.list({ limit: 10, offset: 5 })

      expect(apiClient.get).toHaveBeenCalledWith('/strategies', {
        params: { limit: 10, offset: 5 },
      })
    })
  })

  describe('getById', () => {
    it('fetches a strategy by id', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockStrategy })

      const result = await strategiesApi.getById('strategy-1')

      expect(apiClient.get).toHaveBeenCalledWith('/strategies/strategy-1')
      expect(result).toEqual(mockStrategy)
    })
  })

  describe('create', () => {
    it('creates a new strategy', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: mockStrategy })

      const createData = {
        name: 'Test Strategy',
        strategy_type: 'BUY_AND_HOLD' as const,
        tickers: ['AAPL', 'MSFT'],
        parameters: { allocation: { AAPL: 0.5, MSFT: 0.5 } },
      }

      const result = await strategiesApi.create(createData)

      expect(apiClient.post).toHaveBeenCalledWith('/strategies', createData)
      expect(result).toEqual(mockStrategy)
    })
  })

  describe('delete', () => {
    it('deletes a strategy by id', async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: undefined })

      await strategiesApi.delete('strategy-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/strategies/strategy-1')
    })
  })
})
