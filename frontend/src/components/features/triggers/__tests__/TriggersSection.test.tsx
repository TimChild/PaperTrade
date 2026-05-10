/**
 * Tests for TriggersSection — the embedded section on the activation detail page.
 *
 * Renders the section through the real TanStack Query wiring and asserts on
 * what the user sees + how actions invoke the API client. Mocks at the
 * service-client boundary so query keys / invalidation flow naturally.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { TriggersSection } from '../TriggersSection'
import { triggersApi } from '@/services/api/triggers'
import { apiKeysApi } from '@/services/api/apiKeys'
import type { PaginatedResponse, TriggerResponse } from '@/services/api/types'

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

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

vi.mock('@/services/api/apiKeys', () => ({
  apiKeysApi: {
    list: vi.fn(),
    create: vi.fn(),
    revoke: vi.fn(),
  },
}))

function paged<T>(items: T[]): PaginatedResponse<T> {
  return { items, total: items.length, limit: 20, offset: 0, has_more: false }
}

const activeTrigger: TriggerResponse = {
  id: 'trigger-active',
  activation_id: 'activation-1',
  user_id: 'user-1',
  condition_type: 'DRAWDOWN_THRESHOLD',
  condition_params: {
    threshold_pct: '5',
    lookback_days: 3,
    metric: 'PORTFOLIO_TOTAL',
  },
  agent_prompt: 'Investigate the drawdown.',
  cooldown_seconds: 3600,
  last_fired_at: null,
  status: 'ACTIVE',
  priority: 0,
  default_api_key_id: null,
  expires_at: null,
  created_at: '2026-05-09T12:00:00Z',
  created_by: 'user-1',
  updated_at: '2026-05-09T12:00:00Z',
}

const pausedTrigger: TriggerResponse = {
  ...activeTrigger,
  id: 'trigger-paused',
  status: 'PAUSED',
}

const disabledTrigger: TriggerResponse = {
  ...activeTrigger,
  id: 'trigger-disabled',
  status: 'MANUALLY_DISABLED',
}

const expiredTrigger: TriggerResponse = {
  ...activeTrigger,
  id: 'trigger-expired',
  status: 'EXPIRED',
}

function renderSection(): { user: ReturnType<typeof userEvent.setup> } {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <TriggersSection activationId="activation-1" />
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { user: userEvent.setup() }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(apiKeysApi.list).mockResolvedValue({ items: [], total: 0 })
})

describe('TriggersSection — empty', () => {
  it('renders the editorial empty state with an attach CTA', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(paged([]))
    renderSection()

    expect(
      await screen.findByText(
        /Attach a trigger to make this activation reactive/i
      )
    ).toBeInTheDocument()
    expect(screen.getByTestId('trigger-empty-attach-btn')).toBeInTheDocument()
  })
})

describe('TriggersSection — list', () => {
  it('renders rows for each trigger and a status badge per row', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(
      paged([activeTrigger, pausedTrigger, disabledTrigger, expiredTrigger])
    )
    renderSection()

    await screen.findByTestId('trigger-list-row-trigger-active')
    expect(
      screen.getByTestId('trigger-list-row-trigger-paused')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('trigger-list-row-trigger-disabled')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('trigger-list-row-trigger-expired')
    ).toBeInTheDocument()

    expect(screen.getByTestId('trigger-status-ACTIVE')).toBeInTheDocument()
    expect(screen.getByTestId('trigger-status-PAUSED')).toBeInTheDocument()
    expect(
      screen.getByTestId('trigger-status-MANUALLY_DISABLED')
    ).toBeInTheDocument()
    expect(screen.getByTestId('trigger-status-EXPIRED')).toBeInTheDocument()
  })

  it('renders the formatted condition summary', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(
      paged([activeTrigger])
    )
    renderSection()

    expect(
      await screen.findByText('Drawdown > 5% over 3d (portfolio)')
    ).toBeInTheDocument()
  })

  it('exposes pause + edit + delete actions on a non-terminal trigger', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(
      paged([activeTrigger])
    )
    renderSection()

    await screen.findByTestId('trigger-list-row-trigger-active')
    expect(
      screen.getByTestId('trigger-pause-btn-trigger-active')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('trigger-edit-btn-trigger-active')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('trigger-delete-btn-trigger-active')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('trigger-view-fires-btn-trigger-active')
    ).toBeInTheDocument()
  })

  it('exposes resume action when status is PAUSED', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(
      paged([pausedTrigger])
    )
    renderSection()

    await screen.findByTestId('trigger-list-row-trigger-paused')
    expect(
      screen.getByTestId('trigger-resume-btn-trigger-paused')
    ).toBeInTheDocument()
  })

  it('shows Recreate CTA on a MANUALLY_DISABLED trigger (per Phase F Q3)', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(
      paged([disabledTrigger])
    )
    renderSection()

    await screen.findByTestId('trigger-list-row-trigger-disabled')
    expect(
      screen.getByTestId('trigger-recreate-btn-trigger-disabled')
    ).toBeInTheDocument()
    // No pause / edit / delete on terminal-state rows — those would 422
    // on the backend.
    expect(
      screen.queryByTestId('trigger-pause-btn-trigger-disabled')
    ).not.toBeInTheDocument()
    expect(
      screen.queryByTestId('trigger-edit-btn-trigger-disabled')
    ).not.toBeInTheDocument()
    expect(
      screen.queryByTestId('trigger-delete-btn-trigger-disabled')
    ).not.toBeInTheDocument()
  })
})

describe('TriggersSection — actions', () => {
  it('PATCHes status to PAUSED when the user clicks pause', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(
      paged([activeTrigger])
    )
    vi.mocked(triggersApi.update).mockResolvedValueOnce({
      ...activeTrigger,
      status: 'PAUSED',
    })
    const { user } = renderSection()

    await screen.findByTestId('trigger-list-row-trigger-active')
    await user.click(screen.getByTestId('trigger-pause-btn-trigger-active'))

    await waitFor(() => {
      expect(triggersApi.update).toHaveBeenCalledWith('trigger-active', {
        status: 'PAUSED',
      })
    })
  })

  it('PATCHes status to ACTIVE when the user clicks resume', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(
      paged([pausedTrigger])
    )
    vi.mocked(triggersApi.update).mockResolvedValueOnce({
      ...pausedTrigger,
      status: 'ACTIVE',
    })
    const { user } = renderSection()

    await screen.findByTestId('trigger-list-row-trigger-paused')
    await user.click(screen.getByTestId('trigger-resume-btn-trigger-paused'))

    await waitFor(() => {
      expect(triggersApi.update).toHaveBeenCalledWith('trigger-paused', {
        status: 'ACTIVE',
      })
    })
  })

  it('confirms before deleting and DELETEs on confirm', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(
      paged([activeTrigger])
    )
    vi.mocked(triggersApi.delete).mockResolvedValueOnce(undefined)
    const { user } = renderSection()

    await screen.findByTestId('trigger-list-row-trigger-active')
    await user.click(screen.getByTestId('trigger-delete-btn-trigger-active'))

    // Confirm dialog is rendered.
    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()
    expect(screen.getByTestId('confirm-dialog')).toHaveTextContent(
      /Expire this trigger/i
    )

    await user.click(screen.getByTestId('confirm-dialog-confirm'))

    await waitFor(() => {
      expect(triggersApi.delete).toHaveBeenCalledWith('trigger-active')
    })
  })

  it('opens the attach dialog from the section header CTA', async () => {
    vi.mocked(triggersApi.listForActivation).mockResolvedValue(paged([]))
    const { user } = renderSection()

    await screen.findByTestId('trigger-empty-attach-btn')
    await user.click(screen.getByTestId('trigger-attach-btn'))

    expect(screen.getByTestId('trigger-create-dialog')).toBeInTheDocument()
  })
})

describe('TriggersSection — error', () => {
  it('renders an error block when the list query fails', async () => {
    vi.mocked(triggersApi.listForActivation).mockRejectedValue(
      new Error('boom')
    )
    renderSection()

    expect(await screen.findByTestId('triggers-error')).toBeInTheDocument()
  })
})
