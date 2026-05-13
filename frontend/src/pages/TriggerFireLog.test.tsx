/**
 * Tests for the TriggerFireLog page.
 *
 * Mocks at the API-client boundary so the full page renders end-to-end with
 * real query wiring. Asserts on what the user sees: title, captions, empty
 * state, and the per-fire row carrying the decision badge.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TriggerFireLog } from './TriggerFireLog'
import { triggersApi } from '@/services/api/triggers'
import type {
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

const trigger: TriggerResponse = {
  id: 'trigger-1',
  activation_id: 'activation-1',
  user_id: 'user-1',
  condition_type: 'DRAWDOWN_THRESHOLD',
  condition_params: {
    threshold_pct: '5',
    lookback_days: 3,
    metric: 'PORTFOLIO_TOTAL',
  },
  agent_prompt: 'Investigate the drawdown carefully.',
  cooldown_seconds: 21_600,
  last_fired_at: '2026-05-09T13:00:00Z',
  status: 'ACTIVE',
  priority: 0,
  default_api_key_id: null,
  expires_at: null,
  created_at: '2026-05-09T12:00:00Z',
  created_by: 'user-1',
  updated_at: '2026-05-09T12:00:00Z',
  mode: 'direct',
}

const fire: TriggerFireResponse = {
  id: 'fire-1',
  trigger_id: 'trigger-1',
  activation_id: 'activation-1',
  fired_at: '2026-05-09T13:00:00Z',
  condition_evaluation_data: { drawdown_pct: '6.0', peak_value: '10000' },
  agent_invocation_id: 'inv-1',
  agent_response: 'HOLD',
  agent_response_raw: 'Conditions look like noise; holding.',
  resulting_trade_id: null,
  resulting_modify_payload: null,
  resulting_exploration_task_id: null,
  latency_ms: 1234,
  api_key_id_used: 'key-1',
}

function paged<T>(items: T[]): PaginatedResponse<T> {
  return { items, total: items.length, limit: 50, offset: 0, has_more: false }
}

function renderPage(): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/triggers/trigger-1/fires']}>
        <Routes>
          <Route path="/triggers/:id/fires" element={<TriggerFireLog />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('TriggerFireLog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the condition summary as the page title', async () => {
    vi.mocked(triggersApi.getById).mockResolvedValueOnce(trigger)
    vi.mocked(triggersApi.listFires).mockResolvedValueOnce(paged([]))

    renderPage()

    expect(
      await screen.findByTestId('trigger-fire-log-title')
    ).toHaveTextContent('Drawdown > 5% over 3d (portfolio)')
  })

  it('renders the agent prompt panel', async () => {
    vi.mocked(triggersApi.getById).mockResolvedValueOnce(trigger)
    vi.mocked(triggersApi.listFires).mockResolvedValueOnce(paged([]))

    renderPage()

    expect(
      await screen.findByTestId('trigger-fire-log-agent-prompt')
    ).toHaveTextContent('Investigate the drawdown carefully.')
  })

  it('renders the empty state when there are no fires', async () => {
    vi.mocked(triggersApi.getById).mockResolvedValueOnce(trigger)
    vi.mocked(triggersApi.listFires).mockResolvedValueOnce(paged([]))

    renderPage()

    expect(await screen.findByTestId('trigger-fires-empty')).toBeInTheDocument()
    expect(screen.getByText('The trigger is waiting')).toBeInTheDocument()
  })

  it('renders one row per fire with decision badge', async () => {
    vi.mocked(triggersApi.getById).mockResolvedValueOnce(trigger)
    vi.mocked(triggersApi.listFires).mockResolvedValueOnce(paged([fire]))

    renderPage()

    await waitFor(() =>
      expect(screen.getByTestId('trigger-fire-row-fire-1')).toBeInTheDocument()
    )
    expect(screen.getByTestId('agent-decision-HOLD')).toBeInTheDocument()
    expect(
      screen.getByTestId('trigger-fire-snapshot-fire-1')
    ).toHaveTextContent('Drawdown 6.0%')
  })

  it('renders a trade reference when the fire produced one', async () => {
    vi.mocked(triggersApi.getById).mockResolvedValueOnce(trigger)
    vi.mocked(triggersApi.listFires).mockResolvedValueOnce(
      paged([
        {
          ...fire,
          agent_response: 'BUY',
          resulting_trade_id: 'abcdef01-2345-6789-abcd-ef0123456789',
        },
      ])
    )

    renderPage()

    await waitFor(() =>
      expect(
        screen.getByTestId('trigger-fire-trade-fire-1')
      ).toBeInTheDocument()
    )
    expect(screen.getByTestId('agent-decision-BUY')).toBeInTheDocument()
  })

  it('renders a task link when the fire produced an exploration task', async () => {
    vi.mocked(triggersApi.getById).mockResolvedValueOnce(trigger)
    vi.mocked(triggersApi.listFires).mockResolvedValueOnce(
      paged([
        {
          ...fire,
          agent_response: 'NEEDS_HUMAN',
          resulting_exploration_task_id: 'task-1',
        },
      ])
    )

    renderPage()

    await waitFor(() =>
      expect(screen.getByTestId('trigger-fire-task-fire-1')).toBeInTheDocument()
    )
    expect(screen.getByTestId('trigger-fire-task-fire-1')).toHaveAttribute(
      'href',
      '/exploration-tasks/task-1'
    )
  })

  it('renders an error block when the trigger fetch fails', async () => {
    vi.mocked(triggersApi.getById).mockRejectedValueOnce(new Error('boom'))

    renderPage()

    expect(
      await screen.findByTestId('trigger-fire-log-error')
    ).toBeInTheDocument()
  })

  // Phase J / Task #213 — fire-mode pill rendering.
  it('renders the Inline pill for a direct-mode fire', async () => {
    vi.mocked(triggersApi.getById).mockResolvedValueOnce(trigger)
    vi.mocked(triggersApi.listFires).mockResolvedValueOnce(paged([fire]))

    renderPage()

    await waitFor(() =>
      expect(screen.getByTestId('trigger-fire-row-fire-1')).toBeInTheDocument()
    )
    // A direct-mode rationale lacks the queue marker → "Inline" pill.
    expect(screen.getByTestId('fire-mode-pill-inline')).toHaveTextContent(
      'Inline'
    )
    expect(
      screen.queryByTestId('fire-mode-pill-queued')
    ).not.toBeInTheDocument()
  })

  it('renders the Queued pill for a queue-mode fire', async () => {
    vi.mocked(triggersApi.getById).mockResolvedValueOnce({
      ...trigger,
      mode: 'queue',
    })
    vi.mocked(triggersApi.listFires).mockResolvedValueOnce(
      paged([
        {
          ...fire,
          agent_response: 'NEEDS_HUMAN',
          agent_response_raw:
            '{"queued_task_id":"task-queued-1","mode":"queue"}',
          resulting_exploration_task_id: 'task-queued-1',
        },
      ])
    )

    renderPage()

    await waitFor(() =>
      expect(screen.getByTestId('trigger-fire-row-fire-1')).toBeInTheDocument()
    )
    expect(screen.getByTestId('fire-mode-pill-queued')).toHaveTextContent(
      'Queued'
    )
    expect(
      screen.queryByTestId('fire-mode-pill-inline')
    ).not.toBeInTheDocument()
  })
})
