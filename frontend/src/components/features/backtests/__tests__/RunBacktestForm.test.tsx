/**
 * Tests for the RunBacktestForm component, focused on the Phase J /
 * Task #212 Layer 3 "loading historical data" affordance.
 *
 * Renders the form with a mocked useRunBacktest hook that exposes the
 * ``dataFetching`` + ``fetchingTicker`` state introduced for the lazy-
 * backfill flow.
 */

import type { ReactElement } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RunBacktestForm } from '../RunBacktestForm'
import { useRunBacktest } from '@/hooks/useBacktests'
import { useStrategies } from '@/hooks/useStrategies'

vi.mock('@/hooks/useBacktests', () => ({
  useRunBacktest: vi.fn(),
}))

vi.mock('@/hooks/useStrategies', () => ({
  useStrategies: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

interface RunBacktestMock {
  mutate: ReturnType<typeof vi.fn>
  isPending: boolean
  dataFetching: boolean
  fetchingTicker: string | null
}

function makeRunBacktestMock(
  overrides: Partial<RunBacktestMock>
): RunBacktestMock {
  return {
    mutate: vi.fn(),
    isPending: false,
    dataFetching: false,
    fetchingTicker: null,
    ...overrides,
  }
}

function renderWithProviders(ui: ReactElement): void {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useStrategies).mockReturnValue({
    data: {
      items: [
        {
          id: 'strategy-1',
          user_id: 'user-1',
          name: 'Buy and Hold',
          strategy_type: 'BUY_AND_HOLD',
          tickers: ['AAPL'],
          parameters: { allocation: { AAPL: '1.0' } },
          created_at: '2026-05-12T00:00:00Z',
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
      has_more: false,
    },
    isLoading: false,
  } as unknown as ReturnType<typeof useStrategies>)
})

describe('RunBacktestForm — Phase J fetching affordance', () => {
  it('renders the loading banner when dataFetching is true', () => {
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({
        isPending: false,
        dataFetching: true,
        fetchingTicker: 'AAPL',
      }) as unknown as ReturnType<typeof useRunBacktest>
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    const banner = screen.getByTestId('backtest-fetching-banner')
    expect(banner).toBeInTheDocument()
    expect(banner).toHaveTextContent(/loading historical data/i)
    expect(banner).toHaveTextContent('AAPL')
  })

  it('disables the submit button while dataFetching is true', () => {
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({
        dataFetching: true,
        fetchingTicker: 'AAPL',
      }) as unknown as ReturnType<typeof useRunBacktest>
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    const submit = screen.getByTestId('run-backtest-submit')
    expect(submit).toBeDisabled()
    expect(submit).toHaveTextContent(/fetching data/i)
  })

  it('does not render the loading banner in idle state', () => {
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({}) as unknown as ReturnType<typeof useRunBacktest>
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    expect(
      screen.queryByTestId('backtest-fetching-banner')
    ).not.toBeInTheDocument()
  })
})
