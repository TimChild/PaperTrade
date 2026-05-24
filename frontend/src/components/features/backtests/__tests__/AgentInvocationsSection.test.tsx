/**
 * Tests for the AgentInvocationsSection component (Phase L-4, Task #220).
 *
 * Asserts the visible behaviour the prompt calls out:
 *
 * - Renders the list when invocations exist; rows carry decision pill,
 *   simulated date, latency, "executed" badge, rationale.
 * - Empty state when the API returns zero rows.
 * - Pagination — "Load more" button when `has_more === true`; pressing
 *   it grows the requested window.
 * - Defensive guard: when `agentInvocationMode === 'none'`, the
 *   component renders nothing (the parent page should already gate on
 *   this, but the component is self-defending in tests).
 *
 * The hook is mocked at module boundary; we only exercise UI shapes.
 */

import type { ReactElement } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AgentInvocationsSection } from '../AgentInvocationsSection'
import { useBacktestAgentInvocations } from '@/hooks/useBacktests'
import type {
  BacktestAgentInvocationResponse,
  PaginatedResponse,
} from '@/services/api/types'

vi.mock('@/hooks/useBacktests', () => ({
  useBacktestAgentInvocations: vi.fn(),
}))

function renderWithProviders(ui: ReactElement): void {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

function makeInvocation(
  overrides: Partial<BacktestAgentInvocationResponse> = {}
): BacktestAgentInvocationResponse {
  return {
    id: 'inv-1',
    backtest_run_id: 'bt-1',
    simulated_date: '2024-06-15',
    trigger_id: '0011aabb-aaaa-bbbb-cccc-000011112222',
    invocation_mode: 'live',
    agent_decision: 'BUY',
    rationale: 'Strong dip signal — buying back on simulated weakness.',
    decision_payload: { ticker: 'AAPL', notes: 'scale-in' },
    decision_executed: true,
    simulated_trade_id: null,
    agent_invocation_id: 'msg_xyz',
    latency_ms: 980,
    model: 'claude-haiku-4-5-20251001',
    condition_evaluation_data: { schema_version: 1 },
    created_at: '2024-06-15T15:30:00Z',
    ...overrides,
  }
}

function makePage(
  items: BacktestAgentInvocationResponse[],
  overrides: Partial<PaginatedResponse<BacktestAgentInvocationResponse>> = {}
): PaginatedResponse<BacktestAgentInvocationResponse> {
  return {
    items,
    total: items.length,
    limit: 50,
    offset: 0,
    has_more: false,
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AgentInvocationsSection', () => {
  it('renders the section header with the right copy in MOCK mode', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([makeInvocation()]),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="mock" />
    )

    const section = screen.getByTestId('agent-invocations-section')
    expect(section).toBeInTheDocument()
    expect(section).toHaveTextContent(/agent invocations/i)
    expect(section).toHaveTextContent(/mock mode returns HOLD/i)
  })

  it('renders the section header with the right copy in LIVE mode', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([makeInvocation()]),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    const section = screen.getByTestId('agent-invocations-section')
    expect(section).toHaveTextContent(/real anthropic decisions/i)
  })

  it('renders one row per invocation with the right testids', () => {
    const inv = makeInvocation({ id: 'inv-42' })
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([inv]),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    expect(
      screen.getByTestId('agent-invocation-row-inv-42')
    ).toBeInTheDocument()
    // `formatSimulatedDate` parses the YYYY-MM-DD wire value via the
    // local-tz Date constructor so the rendered day matches the wire
    // value in every viewer timezone. The fixture's simulated_date is
    // '2024-06-15' → 'Jun 15'.
    expect(
      screen.getByTestId('agent-invocation-sim-date-inv-42')
    ).toHaveTextContent('Jun 15')
    expect(
      screen.getByTestId('agent-invocation-latency-inv-42')
    ).toHaveTextContent('980ms')
    expect(
      screen.getByTestId('agent-invocation-executed-inv-42')
    ).toHaveTextContent(/executed/i)
  })

  it('renders "trigger deleted" placeholder when trigger_id is null', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([makeInvocation({ id: 'inv-99', trigger_id: null })]),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    const placeholder = screen.getByTestId(
      'agent-invocation-trigger-deleted-inv-99'
    )
    expect(placeholder).toBeInTheDocument()
    expect(placeholder).toHaveTextContent(/trigger deleted/i)
  })

  it('renders the empty state when the page is empty', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([]),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="mock" />
    )

    const empty = screen.getByTestId('agent-invocations-empty')
    expect(empty).toBeInTheDocument()
    expect(empty).toHaveTextContent(/no triggers fired/i)
  })

  it('renders the loading spinner while the query is pending', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    expect(screen.getByTestId('agent-invocations-loading')).toBeInTheDocument()
  })

  it('renders the error state when the query fails', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('boom'),
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    expect(screen.getByTestId('agent-invocations-error')).toBeInTheDocument()
  })

  it('renders a Load more button when has_more is true', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([makeInvocation()], { has_more: true, total: 100 }),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    const button = screen.getByTestId('agent-invocations-load-more')
    expect(button).toBeInTheDocument()
    fireEvent.click(button)
    // After clicking, the hook is invoked again with a bigger offset;
    // we just need to verify the click doesn't throw.
    expect(useBacktestAgentInvocations).toHaveBeenCalled()
  })

  it('paginates via offset (not by growing the request limit)', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([makeInvocation({ id: 'inv-1' })], {
        has_more: true,
        total: 200,
      }),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    // Initial render: limit=PAGE_SIZE, offset=0.
    const initialCall = vi.mocked(useBacktestAgentInvocations).mock.calls[0]
    expect(initialCall[1]).toEqual({ limit: 50, offset: 0 })

    // First Load-more press: offset advances to PAGE_SIZE; limit
    // STAYS at PAGE_SIZE so we never exceed MAX_PAGE_LIMIT=100.
    fireEvent.click(screen.getByTestId('agent-invocations-load-more'))
    const secondCall = vi.mocked(useBacktestAgentInvocations).mock.calls[
      vi.mocked(useBacktestAgentInvocations).mock.calls.length - 1
    ]
    expect(secondCall[1]).toEqual({ limit: 50, offset: 50 })
  })

  it('appends new pages onto the existing rendered rows', () => {
    // First render: a single row.
    const page1 = makePage([makeInvocation({ id: 'inv-1' })], {
      has_more: true,
      total: 3,
    })
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: page1,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    const { rerender } = render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <AgentInvocationsSection
            backtestId="bt-1"
            agentInvocationMode="live"
          />
        </MemoryRouter>
      </QueryClientProvider>
    )

    expect(screen.getByTestId('agent-invocation-row-inv-1')).toBeInTheDocument()

    // Second page: mock returns a different row. The component must
    // append, not replace.
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([makeInvocation({ id: 'inv-2' })], {
        has_more: false,
        total: 3,
      }),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    // Trigger a Load-more click and a rerender to pick up the new
    // mock return value.
    fireEvent.click(screen.getByTestId('agent-invocations-load-more'))
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <AgentInvocationsSection
            backtestId="bt-1"
            agentInvocationMode="live"
          />
        </MemoryRouter>
      </QueryClientProvider>
    )

    // Both rows must be in the DOM — accumulation, not replacement.
    expect(screen.getByTestId('agent-invocation-row-inv-1')).toBeInTheDocument()
    expect(screen.getByTestId('agent-invocation-row-inv-2')).toBeInTheDocument()
  })

  it('does not render a Load more button when has_more is false', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([makeInvocation()]),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    expect(
      screen.queryByTestId('agent-invocations-load-more')
    ).not.toBeInTheDocument()
  })

  it('returns null when agentInvocationMode is none (defensive guard)', () => {
    // The hook is disabled in this branch; calling the mock still
    // returns the canned shape but the component renders nothing.
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    const { container } = render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <AgentInvocationsSection
            backtestId="bt-1"
            agentInvocationMode="none"
          />
        </MemoryRouter>
      </QueryClientProvider>
    )

    expect(container.firstChild).toBeNull()
  })

  it('truncates long rationale and exposes a Show more toggle', () => {
    const longRationale = 'x'.repeat(500)
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([
        makeInvocation({ id: 'inv-long', rationale: longRationale }),
      ]),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    const rationale = screen.getByTestId('agent-invocation-rationale-inv-long')
    // Initial render — 200 chars + ellipsis.
    expect(rationale.textContent?.length).toBeLessThan(longRationale.length)

    const toggle = screen.getByTestId(
      'agent-invocation-rationale-toggle-inv-long'
    )
    expect(toggle).toHaveTextContent(/show more/i)

    fireEvent.click(toggle)
    expect(toggle).toHaveTextContent(/show less/i)
    expect(rationale).toHaveTextContent(longRationale)
  })

  it('renders the row count', () => {
    vi.mocked(useBacktestAgentInvocations).mockReturnValue({
      data: makePage([makeInvocation()], { total: 5, has_more: true }),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useBacktestAgentInvocations>)

    renderWithProviders(
      <AgentInvocationsSection backtestId="bt-1" agentInvocationMode="live" />
    )

    expect(screen.getByTestId('agent-invocations-count')).toHaveTextContent(
      '5 invocations'
    )
  })
})
