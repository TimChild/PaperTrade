/**
 * Tests for the trigger TanStack Query hooks (Phase G-1).
 *
 * Mocks at the API-client boundary (`@/services/api/triggers`) so we exercise
 * the real query/mutation wiring — query keys, success invalidation, error
 * propagation — without hitting the network.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  triggerQueryKeys,
  useCreateTrigger,
  useDeleteTrigger,
  useTrigger,
  useTriggerFires,
  useTriggers,
  useUpdateTrigger,
} from '../useTriggers'
import { triggersApi } from '@/services/api/triggers'
import type {
  CreateTriggerRequest,
  PaginatedResponse,
  TriggerFireResponse,
  TriggerResponse,
} from '@/services/api/types'

vi.mock('@/services/api/triggers', () => ({
  triggersApi: {
    listForActivation: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    listFires: vi.fn(),
  },
}))

const mockTrigger: TriggerResponse = {
  id: 'trigger-1',
  activation_id: 'activation-1',
  user_id: 'user-1',
  condition_type: 'DRAWDOWN_THRESHOLD',
  condition_params: {
    threshold_pct: '5',
    lookback_days: 3,
    metric: 'PORTFOLIO_TOTAL',
  },
  agent_prompt: 'Investigate the drawdown.',
  cooldown_seconds: 21_600,
  last_fired_at: null,
  status: 'ACTIVE',
  priority: 0,
  default_api_key_id: null,
  expires_at: null,
  created_at: '2026-05-09T12:00:00Z',
  created_by: 'user-1',
  updated_at: '2026-05-09T12:00:00Z',
  mode: 'direct',
}

const mockFire: TriggerFireResponse = {
  id: 'fire-1',
  trigger_id: 'trigger-1',
  activation_id: 'activation-1',
  fired_at: '2026-05-09T13:00:00Z',
  condition_evaluation_data: { drawdown_pct: '6.0' },
  invocation_mode: 'direct',
  agent_invocation_id: 'inv-1',
  agent_response: 'HOLD',
  agent_response_raw: 'No action required.',
  resulting_trade_id: null,
  resulting_modify_payload: null,
  resulting_exploration_task_id: null,
  latency_ms: 1234,
  api_key_id_used: 'key-1',
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

describe('triggerQueryKeys', () => {
  it('produces stable, namespaced keys', () => {
    expect(triggerQueryKeys.all).toEqual(['triggers'])
    expect(triggerQueryKeys.listByActivation('a-1')).toEqual([
      'triggers',
      'by-activation',
      'a-1',
      undefined,
    ])
    expect(triggerQueryKeys.byId('t-1')).toEqual(['triggers', 'by-id', 't-1'])
    expect(triggerQueryKeys.fires('t-1', { limit: 10 })).toEqual([
      'triggers',
      'fires',
      't-1',
      { limit: 10 },
    ])
  })
})

describe('useTriggers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('lists triggers by activation id', async () => {
    const page: PaginatedResponse<TriggerResponse> = {
      items: [mockTrigger],
      total: 1,
      limit: 20,
      offset: 0,
      has_more: false,
    }
    vi.mocked(triggersApi.listForActivation).mockResolvedValueOnce(page)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useTriggers('activation-1'), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(page)
    expect(triggersApi.listForActivation).toHaveBeenCalledWith(
      'activation-1',
      undefined
    )
  })

  it('skips the request when activationId is empty', () => {
    const { Wrapper } = createWrapper()
    renderHook(() => useTriggers(''), { wrapper: Wrapper })
    expect(triggersApi.listForActivation).not.toHaveBeenCalled()
  })
})

describe('useTrigger', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches a single trigger by id', async () => {
    vi.mocked(triggersApi.getById).mockResolvedValueOnce(mockTrigger)
    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useTrigger('trigger-1'), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockTrigger)
  })
})

describe('useTriggerFires', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('paginates fires with the supplied params', async () => {
    const page: PaginatedResponse<TriggerFireResponse> = {
      items: [mockFire],
      total: 1,
      limit: 50,
      offset: 0,
      has_more: false,
    }
    vi.mocked(triggersApi.listFires).mockResolvedValueOnce(page)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(
      () => useTriggerFires('trigger-1', { limit: 50 }),
      { wrapper: Wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(page)
    expect(triggersApi.listFires).toHaveBeenCalledWith('trigger-1', {
      limit: 50,
    })
  })
})

describe('useCreateTrigger', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('invalidates the trigger cache on success', async () => {
    vi.mocked(triggersApi.create).mockResolvedValueOnce(mockTrigger)
    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useCreateTrigger(), {
      wrapper: Wrapper,
    })

    const body: CreateTriggerRequest = {
      condition_type: 'DRAWDOWN_THRESHOLD',
      condition_params: {
        threshold_pct: '5',
        lookback_days: 3,
        metric: 'PORTFOLIO_TOTAL',
      },
      agent_prompt: 'Investigate.',
    }

    await act(async () => {
      await result.current.mutateAsync({
        activationId: 'activation-1',
        body,
      })
    })

    expect(triggersApi.create).toHaveBeenCalledWith('activation-1', body)
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: triggerQueryKeys.all,
    })
  })
})

describe('useUpdateTrigger', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('invalidates list + by-id caches on success', async () => {
    vi.mocked(triggersApi.update).mockResolvedValueOnce({
      ...mockTrigger,
      status: 'PAUSED',
    })
    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useUpdateTrigger(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      await result.current.mutateAsync({
        triggerId: 'trigger-1',
        body: { status: 'PAUSED' },
      })
    })

    expect(triggersApi.update).toHaveBeenCalledWith('trigger-1', {
      status: 'PAUSED',
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: triggerQueryKeys.all,
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: triggerQueryKeys.byId('trigger-1'),
    })
  })
})

describe('useDeleteTrigger', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('invalidates list + by-id caches on success', async () => {
    vi.mocked(triggersApi.delete).mockResolvedValueOnce(undefined)
    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useDeleteTrigger(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      await result.current.mutateAsync('trigger-1')
    })

    expect(triggersApi.delete).toHaveBeenCalledWith('trigger-1')
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: triggerQueryKeys.all,
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: triggerQueryKeys.byId('trigger-1'),
    })
  })

  it('surfaces an error when the API rejects', async () => {
    const apiError = new Error('Forbidden')
    vi.mocked(triggersApi.delete).mockRejectedValueOnce(apiError)
    const { Wrapper } = createWrapper()

    const { result } = renderHook(() => useDeleteTrigger(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      await expect(result.current.mutateAsync('trigger-1')).rejects.toThrow(
        'Forbidden'
      )
    })
  })
})
