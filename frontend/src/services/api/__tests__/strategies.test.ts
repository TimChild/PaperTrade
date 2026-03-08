/**
 * Tests for strategiesApi
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { strategiesApi } from '../strategies'
import { apiClient } from '../client'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockStrategy = {
  id: 'strategy-1',
  user_id: 'user-1',
  name: 'Test Strategy',
  strategy_type: 'BUY_AND_HOLD' as const,
  tickers: ['AAPL', 'MSFT'],
  parameters: { allocation: { AAPL: 0.5, MSFT: 0.5 } },
  created_at: '2024-01-01T00:00:00Z',
}

describe('strategiesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('fetches all strategies', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: [mockStrategy] })

      const result = await strategiesApi.list()

      expect(apiClient.get).toHaveBeenCalledWith('/strategies')
      expect(result).toEqual([mockStrategy])
    })

    it('returns an empty array when no strategies exist', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: [] })

      const result = await strategiesApi.list()

      expect(result).toEqual([])
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
