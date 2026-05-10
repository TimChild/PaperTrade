/**
 * Tests for the strategy-provenance hook.
 *
 * Verifies the hook correctly classifies the strategy as agent/human
 * based on the matching `strategy_created` activity row, and surfaces a
 * recommending exploration task when one is present.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useStrategyProvenance } from '@/hooks/useStrategyProvenance'
import { activityApi } from '@/services/api/activity'
import { explorationTasksApi } from '@/services/api/explorationTasks'
import type {
  ActivityEventResponse,
  ExplorationTaskResponse,
  PaginatedResponse,
} from '@/services/api/types'

vi.mock('@/services/api/activity', () => ({
  activityApi: {
    list: vi.fn(),
  },
}))

vi.mock('@/services/api/explorationTasks', () => ({
  explorationTasksApi: {
    list: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    abandon: vi.fn(),
  },
}))

function paged<T>(items: T[]): PaginatedResponse<T> {
  return { items, total: items.length, limit: 100, offset: 0, has_more: false }
}

function buildEvent(
  overrides: Partial<ActivityEventResponse> = {}
): ActivityEventResponse {
  return {
    type: 'strategy_created',
    occurred_at: '2026-04-01T12:00:00Z',
    actor_kind: 'user',
    actor_label: null,
    actor_user_id: 'user-1',
    subject_type: 'strategy',
    subject_id: 'strat-1',
    subject_name: null,
    summary: 'Created strategy',
    ...overrides,
  }
}

function buildTask(
  overrides: Partial<ExplorationTaskResponse> = {}
): ExplorationTaskResponse {
  return {
    id: 'task-x',
    created_by: 'user-1',
    prompt: 'Investigate mean-reversion variants on AAPL.',
    status: 'DONE',
    target_portfolio_id: null,
    tickers: null,
    constraints: null,
    claimed_by: 'claude-explorer',
    claimed_at: '2026-04-01T11:00:00Z',
    findings: {
      summary: 'Recommended variant.',
      backtest_run_ids: ['bt-1'],
      strategy_ids: ['strat-1'],
      notes: null,
      recommended_strategy_id: 'strat-1',
      recommended_parameters: null,
      metrics: null,
      comparison_to_baseline: null,
      confidence: null,
    },
    created_at: '2026-04-01T10:00:00Z',
    updated_at: '2026-04-01T12:00:00Z',
    ...overrides,
  }
}

function createWrapper(): ({
  children,
}: {
  children: React.ReactNode
}) => React.JSX.Element {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return function Wrapper({
    children,
  }: {
    children: React.ReactNode
  }): React.JSX.Element {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useStrategyProvenance', () => {
  it('classifies as agent when the strategy_created event has an api_key actor', async () => {
    vi.mocked(activityApi.list).mockResolvedValue(
      paged([
        buildEvent({
          subject_id: 'strat-1',
          actor_kind: 'api_key',
          actor_label: 'claude-explorer',
        }),
      ])
    )
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged([]))

    const { result } = renderHook(() => useStrategyProvenance('strat-1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.authorKind).toBe('agent')
    expect(result.current.agentLabel).toBe('claude-explorer')
  })

  it('classifies as human when the matching event has a user actor', async () => {
    vi.mocked(activityApi.list).mockResolvedValue(
      paged([buildEvent({ subject_id: 'strat-1', actor_kind: 'user' })])
    )
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged([]))

    const { result } = renderHook(() => useStrategyProvenance('strat-1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.authorKind).toBe('human')
    expect(result.current.agentLabel).toBeNull()
  })

  it('returns unknown when no matching event is found', async () => {
    vi.mocked(activityApi.list).mockResolvedValue(
      paged([
        // Wrong subject_id — should not match.
        buildEvent({ subject_id: 'other-strategy' }),
      ])
    )
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged([]))

    const { result } = renderHook(() => useStrategyProvenance('strat-1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.authorKind).toBe('unknown')
  })

  it('surfaces the recommending exploration task when findings.recommended_strategy_id matches', async () => {
    vi.mocked(activityApi.list).mockResolvedValue(
      paged([
        buildEvent({
          subject_id: 'strat-1',
          actor_kind: 'api_key',
          actor_label: 'claude-explorer',
        }),
      ])
    )
    vi.mocked(explorationTasksApi.list).mockResolvedValue(
      paged([buildTask({ id: 'task-7' })])
    )

    const { result } = renderHook(() => useStrategyProvenance('strat-1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.recommendingTask).not.toBeNull()
    expect(result.current.recommendingTask!.taskId).toBe('task-7')
    expect(result.current.recommendingTask!.taskTitle).toBe(
      'Investigate mean-reversion variants on AAPL.'
    )
  })

  it('returns no recommending task when no DONE task points at this strategy', async () => {
    vi.mocked(activityApi.list).mockResolvedValue(paged([]))
    vi.mocked(explorationTasksApi.list).mockResolvedValue(
      paged([
        buildTask({
          id: 'task-9',
          findings: {
            summary: 's',
            backtest_run_ids: [],
            strategy_ids: [],
            notes: null,
            recommended_strategy_id: 'other-strat',
            recommended_parameters: null,
            metrics: null,
            comparison_to_baseline: null,
            confidence: null,
          },
        }),
      ])
    )

    const { result } = renderHook(() => useStrategyProvenance('strat-1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.recommendingTask).toBeNull()
  })

  it('is disabled when strategyId is empty', () => {
    vi.mocked(activityApi.list).mockResolvedValue(paged([]))
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged([]))

    const { result } = renderHook(() => useStrategyProvenance(''), {
      wrapper: createWrapper(),
    })

    // Disabled queries don't fetch; the API mocks should not have been called.
    expect(activityApi.list).not.toHaveBeenCalled()
    expect(explorationTasksApi.list).not.toHaveBeenCalled()
    expect(result.current.authorKind).toBe('unknown')
  })
})
