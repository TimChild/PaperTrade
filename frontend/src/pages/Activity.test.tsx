/**
 * Tests for the Activity standalone page.
 *
 * Covers the URL ↔ filter wiring: when the route mounts with
 * `?actor_label=<label>`, the embedded `ActivityFeed` receives the
 * filter; the actor rail surfaces all known API-key labels; and toggling
 * a rail chip updates the URL.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { Activity } from './Activity'
import { useActivity } from '@/hooks/useActivity'
import { apiKeysApi } from '@/services/api/apiKeys'
import type { ApiKeyListResponse } from '@/services/api/types'

vi.mock('@/hooks/useActivity', () => ({
  useActivity: vi.fn(),
}))

vi.mock('@/services/api/apiKeys', () => ({
  apiKeysApi: {
    list: vi.fn(),
    create: vi.fn(),
    revoke: vi.fn(),
  },
}))

function buildEmptyActivity(): ReturnType<typeof useActivity> {
  // The full UseQueryResult type has ~30 fields. We only consume `data`,
  // `isLoading`, and `isError` in the component — a `unknown` cast is the
  // cleanest way to express "this is a partial stub" without enumerating
  // every field. The runtime shape matches the consumer's expectations.
  return {
    data: {
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
      has_more: false,
    },
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useActivity>
}

function buildKeys(labels: string[]): ApiKeyListResponse {
  return {
    items: labels.map((label, i) => ({
      id: `key-${i}`,
      label,
      scopes: ['read'],
      created_at: '2026-04-01T00:00:00Z',
      last_used_at: null,
      revoked_at: null,
      expires_at: null,
      is_active: true,
    })),
    total: labels.length,
  }
}

function renderPage(initialPath = '/activity'): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/activity" element={<Activity />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(apiKeysApi.list).mockResolvedValue(buildKeys([]))
  vi.mocked(useActivity).mockReturnValue(buildEmptyActivity())
})

describe('Activity page', () => {
  it('renders the default heading with no actor_label search param', () => {
    renderPage('/activity')

    expect(screen.getByTestId('activity-page')).toBeInTheDocument()
    expect(screen.getByText('Recent activity')).toBeInTheDocument()
  })

  it('renders the drill-down heading when actor_label is present', () => {
    renderPage('/activity?actor_label=claude-laptop')

    expect(screen.getByText('Activity by claude-laptop')).toBeInTheDocument()
  })

  it('passes the actor_label search param to the embedded feed', () => {
    renderPage('/activity?actor_label=claude-laptop')

    expect(vi.mocked(useActivity)).toHaveBeenCalledWith(
      expect.objectContaining({ actor_label: 'claude-laptop' })
    )
  })

  it('omits the actor_label arg when no search param is set', () => {
    renderPage('/activity')

    expect(vi.mocked(useActivity)).toHaveBeenCalledWith(
      expect.objectContaining({ actor_label: undefined })
    )
  })

  it('renders an actor chip rail when API keys exist', async () => {
    vi.mocked(apiKeysApi.list).mockResolvedValue(
      buildKeys(['claude-explorer', 'claude-strategist'])
    )

    renderPage('/activity')

    // The keys query is async; wait for the rail to render.
    expect(
      await screen.findByTestId('activity-page-actor-rail')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('activity-page-actor-chip-claude-explorer')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('activity-page-actor-chip-claude-strategist')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('activity-page-actor-chip-all')
    ).toBeInTheDocument()
  })

  it('updates the URL when an actor chip is clicked', async () => {
    vi.mocked(apiKeysApi.list).mockResolvedValue(buildKeys(['claude-explorer']))

    const user = userEvent.setup()
    renderPage('/activity')

    const chip = await screen.findByTestId(
      'activity-page-actor-chip-claude-explorer'
    )
    await user.click(chip)

    // After the click, the useActivity hook re-renders with the new
    // actor_label.
    expect(vi.mocked(useActivity)).toHaveBeenLastCalledWith(
      expect.objectContaining({ actor_label: 'claude-explorer' })
    )
  })

  it('clears the filter when the "Everyone" chip is clicked', async () => {
    vi.mocked(apiKeysApi.list).mockResolvedValue(buildKeys(['claude-explorer']))

    const user = userEvent.setup()
    renderPage('/activity?actor_label=claude-explorer')

    const everyone = await screen.findByTestId('activity-page-actor-chip-all')
    await user.click(everyone)

    expect(vi.mocked(useActivity)).toHaveBeenLastCalledWith(
      expect.objectContaining({ actor_label: undefined })
    )
  })
})
