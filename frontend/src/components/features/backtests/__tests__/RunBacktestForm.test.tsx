/**
 * Tests for the RunBacktestForm component:
 *
 * - Phase J / Task #212 Layer 3 "loading historical data" affordance.
 * - Phase L-4 (Task #220) agent invocation mode toggle.
 *
 * Renders the form with a mocked useRunBacktest hook that exposes the
 * ``dataFetching`` + ``fetchingTicker`` state introduced for the lazy-
 * backfill flow.
 */

import type { ReactElement } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
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

// ---------------------------------------------------------------------------
// Date validator boundary: exactly 3 years must be accepted; > 3 rejected.
// ---------------------------------------------------------------------------
describe('RunBacktestForm — date range validator', () => {
  beforeEach(() => {
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({}) as unknown as ReturnType<typeof useRunBacktest>
    )
  })

  function fillAndSubmit(startDate: string, endDate: string): void {
    fireEvent.change(screen.getByTestId('backtest-strategy-select'), {
      target: { value: 'strategy-1' },
    })
    fireEvent.change(screen.getByTestId('backtest-name-input'), {
      target: { value: 'Test run' },
    })
    fireEvent.change(screen.getByTestId('backtest-start-date-input'), {
      target: { value: startDate },
    })
    fireEvent.change(screen.getByTestId('backtest-end-date-input'), {
      target: { value: endDate },
    })
    fireEvent.submit(screen.getByTestId('run-backtest-form'))
  }

  it('allows a range of exactly 3 years (start and end on same month/day)', () => {
    const mutate = vi.fn()
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({ mutate }) as unknown as ReturnType<
        typeof useRunBacktest
      >
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    // 2020-01-15 → 2023-01-15 is exactly 3 years (crosses leap year 2020).
    // Both dates are safely in the past so the "future date" guard does not fire.
    fillAndSubmit('2020-01-15', '2023-01-15')

    // Should submit, not show the "cannot exceed 3 years" error.
    expect(screen.queryByText(/cannot exceed 3 years/i)).not.toBeInTheDocument()
    expect(mutate).toHaveBeenCalledTimes(1)
  })

  it('rejects a range of 3 years + 1 day', () => {
    const mutate = vi.fn()
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({ mutate }) as unknown as ReturnType<
        typeof useRunBacktest
      >
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    // One day past the 3-year boundary; both dates safely in the past.
    fillAndSubmit('2020-01-15', '2023-01-16')

    expect(screen.getByText(/cannot exceed 3 years/i)).toBeInTheDocument()
    expect(mutate).not.toHaveBeenCalled()
  })
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

describe('RunBacktestForm — Phase L-4 agent mode toggle', () => {
  it('renders all three agent-mode options with captions', () => {
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({}) as unknown as ReturnType<typeof useRunBacktest>
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    expect(screen.getByTestId('agent-mode-fieldset')).toBeInTheDocument()
    expect(screen.getByTestId('agent-mode-radio-none')).toBeInTheDocument()
    expect(screen.getByTestId('agent-mode-radio-mock')).toBeInTheDocument()
    expect(screen.getByTestId('agent-mode-radio-live')).toBeInTheDocument()
  })

  it('defaults to NONE selected', () => {
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({}) as unknown as ReturnType<typeof useRunBacktest>
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    const none = screen.getByTestId('agent-mode-radio-none') as HTMLInputElement
    const mock = screen.getByTestId('agent-mode-radio-mock') as HTMLInputElement
    const live = screen.getByTestId('agent-mode-radio-live') as HTMLInputElement

    expect(none.checked).toBe(true)
    expect(mock.checked).toBe(false)
    expect(live.checked).toBe(false)
  })

  it('renders the cost warning chip on Live only', () => {
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({}) as unknown as ReturnType<typeof useRunBacktest>
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    const chip = screen.getByTestId('agent-mode-live-cost-chip')
    expect(chip).toBeInTheDocument()
    expect(chip).toHaveTextContent(/charges to your account/i)
  })

  it('submits with the selected agent_invocation_mode in the payload', () => {
    const mutate = vi.fn()
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({
        mutate,
      }) as unknown as ReturnType<typeof useRunBacktest>
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    // Strategy is required for the submit to fire — pick one.
    fireEvent.change(screen.getByTestId('backtest-strategy-select'), {
      target: { value: 'strategy-1' },
    })
    fireEvent.change(screen.getByTestId('backtest-name-input'), {
      target: { value: 'agent run' },
    })
    // Default date range is exactly 3 years which trips the
    // "Date range cannot exceed 3 years" validator on the edge; set
    // an explicit narrow range to keep the validator happy.
    fireEvent.change(screen.getByTestId('backtest-start-date-input'), {
      target: { value: '2024-01-01' },
    })
    fireEvent.change(screen.getByTestId('backtest-end-date-input'), {
      target: { value: '2024-12-31' },
    })

    // Select MOCK.
    fireEvent.click(screen.getByTestId('agent-mode-radio-mock'))

    // fireEvent.submit on the form bypasses any quirks around clicking a
    // submit button.
    fireEvent.submit(screen.getByTestId('run-backtest-form'))

    expect(mutate).toHaveBeenCalledTimes(1)
    const payload = mutate.mock.calls[0][0] as { agent_invocation_mode: string }
    expect(payload.agent_invocation_mode).toBe('mock')
  })

  it('submits with NONE in the payload when the operator does not pick a mode', () => {
    const mutate = vi.fn()
    vi.mocked(useRunBacktest).mockReturnValue(
      makeRunBacktestMock({
        mutate,
      }) as unknown as ReturnType<typeof useRunBacktest>
    )

    renderWithProviders(
      <RunBacktestForm onSuccess={vi.fn()} onCancel={vi.fn()} />
    )

    fireEvent.change(screen.getByTestId('backtest-strategy-select'), {
      target: { value: 'strategy-1' },
    })
    fireEvent.change(screen.getByTestId('backtest-name-input'), {
      target: { value: 'default-mode run' },
    })
    fireEvent.change(screen.getByTestId('backtest-start-date-input'), {
      target: { value: '2024-01-01' },
    })
    fireEvent.change(screen.getByTestId('backtest-end-date-input'), {
      target: { value: '2024-12-31' },
    })

    fireEvent.submit(screen.getByTestId('run-backtest-form'))

    expect(mutate).toHaveBeenCalledTimes(1)
    const payload = mutate.mock.calls[0][0] as { agent_invocation_mode: string }
    expect(payload.agent_invocation_mode).toBe('none')
  })
})
