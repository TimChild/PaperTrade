/**
 * Tests for strategyActivationsApi
 */
import { AxiosError } from 'axios'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { strategyActivationsApi } from '../strategyActivations'
import { apiClient } from '../client'
import type {
  PaginatedResponse,
  RunNowResponse,
  StrategyActivationResponse,
} from '../types'

vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const mockActivation: StrategyActivationResponse = {
  id: 'activation-1',
  user_id: 'user-1',
  strategy_id: 'strategy-1',
  portfolio_id: 'portfolio-1',
  status: 'ACTIVE',
  frequency: 'DAILY_MARKET_CLOSE',
  last_executed_at: null,
  last_error: null,
  deactivation_reason: null,
  created_at: '2026-05-09T00:00:00Z',
  updated_at: '2026-05-09T00:00:00Z',
}

function paginate(
  items: StrategyActivationResponse[],
  limit = 20,
  offset = 0
): PaginatedResponse<StrategyActivationResponse> {
  return {
    items,
    total: items.length,
    limit,
    offset,
    has_more: false,
  }
}

describe('strategyActivationsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('activate', () => {
    it('posts to /strategies/{id}/activate with the body', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: mockActivation })

      const result = await strategyActivationsApi.activate('strategy-1', {
        portfolio_id: 'portfolio-1',
      })

      expect(apiClient.post).toHaveBeenCalledWith(
        '/strategies/strategy-1/activate',
        { portfolio_id: 'portfolio-1' }
      )
      expect(result).toEqual(mockActivation)
    })

    it('forwards the optional frequency field', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: mockActivation })

      await strategyActivationsApi.activate('strategy-1', {
        portfolio_id: 'portfolio-1',
        frequency: 'DAILY_MARKET_CLOSE',
      })

      expect(apiClient.post).toHaveBeenCalledWith(
        '/strategies/strategy-1/activate',
        { portfolio_id: 'portfolio-1', frequency: 'DAILY_MARKET_CLOSE' }
      )
    })
  })

  describe('getByStrategy', () => {
    it('returns the activation when one exists', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockActivation })

      const result = await strategyActivationsApi.getByStrategy('strategy-1')

      expect(apiClient.get).toHaveBeenCalledWith(
        '/strategies/strategy-1/activation'
      )
      expect(result).toEqual(mockActivation)
    })

    it('returns null when the backend returns 404', async () => {
      // Build an AxiosError with the 404 response shape the client interceptor
      // sees in production.
      const axiosError = new AxiosError(
        'Not found',
        '404',
        undefined,
        undefined,
        {
          status: 404,
          statusText: 'Not Found',
          data: { detail: 'No activation found' },
          headers: {},
          // axios needs a config; an empty-but-non-null object is fine here.
          config: { headers: {} } as never,
        }
      )
      vi.mocked(apiClient.get).mockRejectedValueOnce(axiosError)

      const result = await strategyActivationsApi.getByStrategy('strategy-1')

      expect(result).toBeNull()
    })

    it('rethrows non-404 errors', async () => {
      const axiosError = new AxiosError(
        'Server error',
        '500',
        undefined,
        undefined,
        {
          status: 500,
          statusText: 'Server Error',
          data: { detail: 'oops' },
          headers: {},
          config: { headers: {} } as never,
        }
      )
      vi.mocked(apiClient.get).mockRejectedValueOnce(axiosError)

      await expect(
        strategyActivationsApi.getByStrategy('strategy-1')
      ).rejects.toBe(axiosError)
    })
  })

  describe('list', () => {
    it('fetches activations as a paginated envelope', async () => {
      const page = paginate([mockActivation])
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: page })

      const result = await strategyActivationsApi.list()

      expect(apiClient.get).toHaveBeenCalledWith('/activations', {
        params: undefined,
      })
      expect(result).toEqual(page)
    })

    it('forwards limit/offset query params', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        data: paginate([], 10, 5),
      })

      await strategyActivationsApi.list({ limit: 10, offset: 5 })

      expect(apiClient.get).toHaveBeenCalledWith('/activations', {
        params: { limit: 10, offset: 5 },
      })
    })
  })

  describe('deactivate', () => {
    it('posts an empty body when no reason is provided', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({
        data: { ...mockActivation, status: 'PAUSED' },
      })

      await strategyActivationsApi.deactivate('activation-1')

      expect(apiClient.post).toHaveBeenCalledWith(
        '/activations/activation-1/deactivate',
        {}
      )
    })

    it('forwards the reason when provided', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({
        data: { ...mockActivation, status: 'PAUSED' },
      })

      await strategyActivationsApi.deactivate('activation-1', 'taking a break')

      expect(apiClient.post).toHaveBeenCalledWith(
        '/activations/activation-1/deactivate',
        { reason: 'taking a break' }
      )
    })
  })

  describe('runNow', () => {
    it('posts to /activations/{id}/run-now and returns the run envelope', async () => {
      const runResponse: RunNowResponse = {
        activation: mockActivation,
        succeeded: true,
        trades: 2,
        error: null,
      }
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: runResponse })

      const result = await strategyActivationsApi.runNow('activation-1')

      expect(apiClient.post).toHaveBeenCalledWith(
        '/activations/activation-1/run-now'
      )
      expect(result).toEqual(runResponse)
    })
  })
})
