/**
 * Tests for backtestsApi
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { backtestsApi } from '../backtests'
import { apiClient } from '../client'
import type { BacktestRunResponse, PaginatedResponse } from '../types'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockBacktest: BacktestRunResponse = {
  id: 'backtest-1',
  user_id: 'user-1',
  strategy_id: 'strategy-1',
  portfolio_id: 'portfolio-1',
  backtest_name: 'Test Backtest',
  start_date: '2023-01-01',
  end_date: '2024-01-01',
  initial_cash: '10000.00',
  status: 'COMPLETED',
  created_at: '2024-01-01T00:00:00Z',
  completed_at: '2024-01-01T01:00:00Z',
  error_message: null,
  total_return_pct: '25.50',
  max_drawdown_pct: '-8.00',
  annualized_return_pct: '25.50',
  total_trades: 12,
}

function paginate(
  items: BacktestRunResponse[],
  limit = 20,
  offset = 0
): PaginatedResponse<BacktestRunResponse> {
  return {
    items,
    total: items.length,
    limit,
    offset,
    has_more: false,
  }
}

describe('backtestsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('fetches all backtests as a paginated envelope', async () => {
      const page = paginate([mockBacktest])
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: page })

      const result = await backtestsApi.list()

      expect(apiClient.get).toHaveBeenCalledWith('/backtests', {
        params: undefined,
      })
      expect(result).toEqual(page)
      expect(result.items).toEqual([mockBacktest])
    })

    it('returns an empty page when no backtests exist', async () => {
      const page = paginate([])
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: page })

      const result = await backtestsApi.list()

      expect(result.items).toEqual([])
      expect(result.total).toBe(0)
    })

    it('forwards limit/offset query params', async () => {
      const page = paginate([mockBacktest], 5, 10)
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: page })

      await backtestsApi.list({ limit: 5, offset: 10 })

      expect(apiClient.get).toHaveBeenCalledWith('/backtests', {
        params: { limit: 5, offset: 10 },
      })
    })
  })

  describe('getById', () => {
    it('fetches a backtest by id', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockBacktest })

      const result = await backtestsApi.getById('backtest-1')

      expect(apiClient.get).toHaveBeenCalledWith('/backtests/backtest-1')
      expect(result).toEqual(mockBacktest)
    })
  })

  describe('run', () => {
    it('runs a new backtest', async () => {
      const pendingBacktest: BacktestRunResponse = {
        ...mockBacktest,
        status: 'PENDING',
      }
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: pendingBacktest })

      const runData = {
        strategy_id: 'strategy-1',
        backtest_name: 'Test Backtest',
        start_date: '2023-01-01',
        end_date: '2024-01-01',
        initial_cash: 10000,
      }

      const result = await backtestsApi.run(runData)

      expect(apiClient.post).toHaveBeenCalledWith('/backtests', runData)
      expect(result).toEqual(pendingBacktest)
    })
  })

  describe('delete', () => {
    it('deletes a backtest by id', async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: undefined })

      await backtestsApi.delete('backtest-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/backtests/backtest-1')
    })
  })
})
