/**
 * Tests for `useDataCoverage` + `useBackfillTicker`
 * (Phase J / Task #212 L4 + Task #215).
 *
 * Mocks at the API-client boundary (`@/services/api/admin`) so we exercise
 * the real query/mutation wiring — query keys, refetch interval,
 * mutation invalidation — without hitting the network.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  DATA_COVERAGE_POLL_INTERVAL_MS,
  dataCoverageQueryKeys,
  useBackfillTicker,
  useDataCoverage,
} from '../useDataCoverage'
import { dataCoverageApi } from '@/services/api/admin'
import type {
  BackfillResponse,
  DataCoverageResponse,
} from '@/services/api/types'

vi.mock('@/services/api/admin', () => ({
  dataCoverageApi: {
    list: vi.fn(),
    backfill: vi.fn(),
  },
}))

const mockResponse: DataCoverageResponse = {
  tickers: [
    {
      ticker: 'AAPL',
      coverage_start: '2025-01-06',
      coverage_end: '2025-01-10',
      last_refresh: '2025-01-10T00:00:00Z',
      gap_days_count: 0,
      target_epoch: '2015-01-01',
      is_active: true,
      backfill_status: null,
    },
  ],
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

describe('dataCoverageQueryKeys', () => {
  it('produces stable, namespaced keys', () => {
    expect(dataCoverageQueryKeys.all).toEqual(['admin', 'data-coverage'])
    expect(dataCoverageQueryKeys.list()).toEqual([
      'admin',
      'data-coverage',
      'list',
    ])
  })
})

describe('DATA_COVERAGE_POLL_INTERVAL_MS', () => {
  it('is 30 seconds per the Layer 4 spec', () => {
    expect(DATA_COVERAGE_POLL_INTERVAL_MS).toBe(30_000)
  })
})

describe('useDataCoverage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches the coverage list via dataCoverageApi.list', async () => {
    vi.mocked(dataCoverageApi.list).mockResolvedValue(mockResponse)
    const { Wrapper } = createWrapper()

    const { result } = renderHook(() => useDataCoverage(), {
      wrapper: Wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockResponse)
    expect(dataCoverageApi.list).toHaveBeenCalledOnce()
  })
})

describe('useBackfillTicker', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const baseResponse: BackfillResponse = {
    task_id: '00000000-0000-0000-0000-00000000abcd',
    status: 'pending',
    existing: false,
    start_date: '2015-01-01',
    end_date: '2025-01-10',
  }

  it('calls dataCoverageApi.backfill with the ticker-only payload', async () => {
    vi.mocked(dataCoverageApi.backfill).mockResolvedValue(baseResponse)
    const { Wrapper } = createWrapper()

    const { result } = renderHook(() => useBackfillTicker(), {
      wrapper: Wrapper,
    })

    let mutationResult: BackfillResponse | undefined
    await act(async () => {
      mutationResult = await result.current.mutateAsync({ ticker: 'AAPL' })
    })

    expect(dataCoverageApi.backfill).toHaveBeenCalledWith({ ticker: 'AAPL' })
    expect(mutationResult).toEqual(baseResponse)
  })

  it('invalidates the data-coverage query on success', async () => {
    vi.mocked(dataCoverageApi.backfill).mockResolvedValue(baseResponse)
    const { Wrapper, client } = createWrapper()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries')

    const { result } = renderHook(() => useBackfillTicker(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      await result.current.mutateAsync({ ticker: 'AAPL' })
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: dataCoverageQueryKeys.all,
    })
  })

  it('surfaces the existing-task flag on idempotency hit', async () => {
    const response: BackfillResponse = {
      task_id: '00000000-0000-0000-0000-00000000abcd',
      status: 'running',
      existing: true,
      start_date: '2015-01-01',
      end_date: '2025-01-10',
    }
    vi.mocked(dataCoverageApi.backfill).mockResolvedValue(response)
    const { Wrapper } = createWrapper()

    const { result } = renderHook(() => useBackfillTicker(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      const r = await result.current.mutateAsync({ ticker: 'AAPL' })
      expect(r.existing).toBe(true)
      expect(r.status).toBe('running')
    })
  })

  it('exposes the resolved date range on the response', async () => {
    vi.mocked(dataCoverageApi.backfill).mockResolvedValue(baseResponse)
    const { Wrapper } = createWrapper()

    const { result } = renderHook(() => useBackfillTicker(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      const r = await result.current.mutateAsync({ ticker: 'AAPL' })
      expect(r.start_date).toBe('2015-01-01')
      expect(r.end_date).toBe('2025-01-10')
    })
  })
})
