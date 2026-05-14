/**
 * Tests for the useStrategyActivation TanStack Query hooks.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  activationQueryKeys,
  useActivateStrategy,
  useActivations,
  useDeactivateActivation,
  useRunActivationNow,
  useStrategyActivation,
} from '../useStrategyActivation'
import { strategyActivationsApi } from '@/services/api/strategyActivations'
import type {
  PaginatedResponse,
  RunNowResponse,
  StrategyActivationResponse,
} from '@/services/api/types'

vi.mock('@/services/api/strategyActivations', () => ({
  strategyActivationsApi: {
    activate: vi.fn(),
    getByStrategy: vi.fn(),
    list: vi.fn(),
    deactivate: vi.fn(),
    runNow: vi.fn(),
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

function createWrapper(): {
  Wrapper: ({ children }: { children: React.ReactNode }) => React.JSX.Element
  client: QueryClient
} {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  const Wrapper = ({
    children,
  }: {
    children: React.ReactNode
  }): React.JSX.Element => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  return { Wrapper, client }
}

describe('activationQueryKeys', () => {
  it('produces stable, namespaced keys', () => {
    expect(activationQueryKeys.all).toEqual(['activations'])
    expect(activationQueryKeys.list({ limit: 10 })).toEqual([
      'activations',
      'list',
      { limit: 10 },
    ])
    expect(activationQueryKeys.byStrategy('s-1')).toEqual([
      'activations',
      'by-strategy',
      's-1',
    ])
  })
})

describe('useStrategyActivation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches the activation for a strategy', async () => {
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValueOnce(
      mockActivation
    )

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useStrategyActivation('strategy-1'), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockActivation)
    expect(strategyActivationsApi.getByStrategy).toHaveBeenCalledWith(
      'strategy-1'
    )
  })

  it('returns null when no activation exists', async () => {
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValueOnce(null)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useStrategyActivation('strategy-1'), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeNull()
  })

  it('is disabled when strategyId is empty', () => {
    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useStrategyActivation(''), {
      wrapper: Wrapper,
    })

    expect(result.current.fetchStatus).toBe('idle')
    expect(strategyActivationsApi.getByStrategy).not.toHaveBeenCalled()
  })
})

describe('useActivations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches paginated activations', async () => {
    const page: PaginatedResponse<StrategyActivationResponse> = {
      items: [mockActivation],
      total: 1,
      limit: 20,
      offset: 0,
      has_more: false,
    }
    vi.mocked(strategyActivationsApi.list).mockResolvedValueOnce(page)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useActivations({ limit: 20 }), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(page)
    expect(strategyActivationsApi.list).toHaveBeenCalledWith({ limit: 20 })
  })
})

describe('useActivateStrategy', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls the API and invalidates queries on success', async () => {
    vi.mocked(strategyActivationsApi.activate).mockResolvedValueOnce(
      mockActivation
    )

    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useActivateStrategy(), {
      wrapper: Wrapper,
    })

    result.current.mutate({
      strategyId: 'strategy-1',
      body: { portfolio_id: 'portfolio-1' },
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(strategyActivationsApi.activate).toHaveBeenCalledWith('strategy-1', {
      portfolio_id: 'portfolio-1',
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: activationQueryKeys.all,
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: activationQueryKeys.byStrategy('strategy-1'),
    })
  })
})

describe('useDeactivateActivation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('passes reason and invalidates by-strategy when given', async () => {
    vi.mocked(strategyActivationsApi.deactivate).mockResolvedValueOnce({
      ...mockActivation,
      status: 'PAUSED',
    })

    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useDeactivateActivation(), {
      wrapper: Wrapper,
    })

    result.current.mutate({
      activationId: 'activation-1',
      reason: 'taking a break',
      strategyId: 'strategy-1',
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(strategyActivationsApi.deactivate).toHaveBeenCalledWith(
      'activation-1',
      'taking a break'
    )
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: activationQueryKeys.byStrategy('strategy-1'),
    })
  })

  it('invalidates only the list when no strategyId is given', async () => {
    vi.mocked(strategyActivationsApi.deactivate).mockResolvedValueOnce({
      ...mockActivation,
      status: 'PAUSED',
    })

    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useDeactivateActivation(), {
      wrapper: Wrapper,
    })

    result.current.mutate({ activationId: 'activation-1' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: activationQueryKeys.all,
    })
    // Without a strategyId we shouldn't invalidate any by-strategy key.
    const calls = invalidateSpy.mock.calls
    const byStrategyCalls = calls.filter((call) => {
      const arg = call[0] as { queryKey?: readonly unknown[] } | undefined
      return arg?.queryKey?.[1] === 'by-strategy'
    })
    expect(byStrategyCalls).toHaveLength(0)
  })
})

describe('useRunActivationNow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns the run envelope and invalidates queries', async () => {
    const runResponse: RunNowResponse = {
      activation: mockActivation,
      succeeded: true,
      trades: 3,
      error: null,
    }
    vi.mocked(strategyActivationsApi.runNow).mockResolvedValueOnce(runResponse)

    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useRunActivationNow(), {
      wrapper: Wrapper,
    })

    result.current.mutate({
      activationId: 'activation-1',
      strategyId: 'strategy-1',
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(runResponse)
    expect(strategyActivationsApi.runNow).toHaveBeenCalledWith('activation-1')
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: activationQueryKeys.byStrategy('strategy-1'),
    })
  })
})
