/**
 * Tests for the exploration-tasks TanStack Query hooks.
 *
 * Mocks at the API-client boundary (`@/services/api/explorationTasks`) so we
 * exercise the real query/mutation wiring — query keys, success
 * invalidation, error propagation — without hitting the network.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  explorationTaskQueryKeys,
  useAbandonExplorationTask,
  useCreateExplorationTask,
  useExplorationTask,
  useExplorationTasks,
} from '../useExplorationTasks'
import { explorationTasksApi } from '@/services/api/explorationTasks'
import type {
  CreateExplorationTaskRequest,
  ExplorationTaskResponse,
  PaginatedResponse,
} from '@/services/api/types'

vi.mock('@/services/api/explorationTasks', () => ({
  explorationTasksApi: {
    list: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    abandon: vi.fn(),
  },
}))

const mockTask: ExplorationTaskResponse = {
  id: 'task-1',
  created_by: 'user-1',
  prompt: 'Explore mean reversion on AAPL',
  status: 'OPEN',
  target_portfolio_id: null,
  tickers: ['AAPL'],
  constraints: null,
  claimed_by: null,
  claimed_at: null,
  findings: null,
  created_at: '2026-05-09T12:00:00Z',
  updated_at: '2026-05-09T12:00:00Z',
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

describe('explorationTaskQueryKeys', () => {
  it('produces stable, namespaced keys', () => {
    expect(explorationTaskQueryKeys.all).toEqual(['exploration-tasks'])
    expect(explorationTaskQueryKeys.list({ scope: 'mine' })).toEqual([
      'exploration-tasks',
      'list',
      { scope: 'mine' },
    ])
    expect(explorationTaskQueryKeys.byId('t-1')).toEqual([
      'exploration-tasks',
      'by-id',
      't-1',
    ])
  })
})

describe('useExplorationTasks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('lists tasks and forwards filter params to the API client', async () => {
    const page: PaginatedResponse<ExplorationTaskResponse> = {
      items: [mockTask],
      total: 1,
      limit: 20,
      offset: 0,
      has_more: false,
    }
    vi.mocked(explorationTasksApi.list).mockResolvedValueOnce(page)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(
      () => useExplorationTasks({ scope: 'mine', status: 'OPEN' }),
      { wrapper: Wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(page)
    expect(explorationTasksApi.list).toHaveBeenCalledWith({
      scope: 'mine',
      status: 'OPEN',
    })
  })
})

describe('useExplorationTask', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches a single task by id', async () => {
    vi.mocked(explorationTasksApi.getById).mockResolvedValueOnce(mockTask)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useExplorationTask('task-1'), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockTask)
    expect(explorationTasksApi.getById).toHaveBeenCalledWith('task-1')
  })

  it('does not fire the request when the id is empty', () => {
    const { Wrapper } = createWrapper()
    renderHook(() => useExplorationTask(''), { wrapper: Wrapper })
    expect(explorationTasksApi.getById).not.toHaveBeenCalled()
  })
})

describe('useCreateExplorationTask', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('invalidates the list cache on success', async () => {
    vi.mocked(explorationTasksApi.create).mockResolvedValueOnce(mockTask)
    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useCreateExplorationTask(), {
      wrapper: Wrapper,
    })

    const payload: CreateExplorationTaskRequest = {
      prompt: 'Explore something',
    }

    await act(async () => {
      await result.current.mutateAsync(payload)
    })

    expect(explorationTasksApi.create).toHaveBeenCalledWith(payload)
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: explorationTaskQueryKeys.all,
    })
  })
})

describe('useAbandonExplorationTask', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('invalidates the list and per-task caches on success', async () => {
    vi.mocked(explorationTasksApi.abandon).mockResolvedValueOnce(undefined)
    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useAbandonExplorationTask(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      await result.current.mutateAsync('task-1')
    })

    expect(explorationTasksApi.abandon).toHaveBeenCalledWith('task-1')
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: explorationTaskQueryKeys.all,
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: explorationTaskQueryKeys.byId('task-1'),
    })
  })

  it('surfaces an error when the API rejects', async () => {
    const apiError = new Error('Forbidden')
    vi.mocked(explorationTasksApi.abandon).mockRejectedValueOnce(apiError)

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useAbandonExplorationTask(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      await expect(result.current.mutateAsync('task-1')).rejects.toThrow(
        'Forbidden'
      )
    })
  })
})
