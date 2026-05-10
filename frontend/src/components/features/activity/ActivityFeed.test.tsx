import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { ActivityFeed } from './ActivityFeed'
import { useActivity } from '@/hooks/useActivity'
import type {
  ActivityEventResponse,
  PaginatedResponse,
} from '@/services/api/types'

// Mock the hook so the component can be tested without a real backend.
vi.mock('@/hooks/useActivity', () => ({
  useActivity: vi.fn(),
}))

const mockedUseActivity = vi.mocked(useActivity)

// Avoid coupling to react-router-dom's `useNavigate` in test scope.
const navigateSpy = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual =
    await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateSpy,
  }
})

const userEvt: ActivityEventResponse = {
  type: 'trade',
  // ~30 minutes ago, so formatRelativeTime renders "30m ago" — no
  // dependency on the live clock for the test assertions.
  occurred_at: new Date(Date.now() - 30 * 60_000).toISOString(),
  actor_kind: 'user',
  actor_label: null,
  actor_user_id: 'user-1',
  subject_type: 'portfolio',
  subject_id: 'portfolio-aaa',
  subject_name: 'Mar 2026',
  summary: 'Bought 10 AAPL @ $200.00',
}

const agentEvt: ActivityEventResponse = {
  type: 'task_filed',
  occurred_at: new Date(Date.now() - 5 * 60_000).toISOString(),
  actor_kind: 'api_key',
  actor_label: 'claude-laptop',
  actor_user_id: 'user-1',
  subject_type: 'task',
  subject_id: 'task-bbb',
  subject_name: 'Investigate AAPL drift',
  summary: 'Filed task: Investigate AAPL drift',
}

function buildPage(
  items: ActivityEventResponse[]
): PaginatedResponse<ActivityEventResponse> {
  return {
    items,
    total: items.length,
    limit: 50,
    offset: 0,
    has_more: false,
  }
}

function renderFeed(actorLabel?: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ActivityFeed actorLabel={actorLabel} />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

beforeEach(() => {
  navigateSpy.mockClear()
  mockedUseActivity.mockReset()
})

describe('ActivityFeed', () => {
  it('renders a row for each activity event', () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([agentEvt, userEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    renderFeed()

    expect(screen.getByTestId('activity-feed-row-0')).toBeInTheDocument()
    expect(screen.getByTestId('activity-feed-row-1')).toBeInTheDocument()
    expect(screen.getByText(agentEvt.summary)).toBeInTheDocument()
    expect(screen.getByText(userEvt.summary)).toBeInTheDocument()
  })

  it('shows API-key label for agent-authored rows and "you" for user rows', () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([agentEvt, userEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    renderFeed()

    // Agent row carries the explicit API-key label as a clickable link
    // (the G-2.2 drill-down affordance).
    expect(
      screen.getByTestId('activity-actor-link-claude-laptop')
    ).toHaveTextContent('claude-laptop')
    // User row says "you".
    expect(screen.getByText('you')).toBeInTheDocument()
  })

  it('renders relative time labels (e.g., "30m ago")', () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([userEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    renderFeed()

    // The user event was 30 minutes ago — accept "29m" or "30m" depending
    // on test-run timing slop.
    const timeText = screen.getByTestId('activity-feed-row-time-0').textContent
    expect(timeText).toMatch(/(29|30)m ago/)
  })

  it('navigates when a portfolio row is clicked', async () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([userEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    const user = userEvent.setup()
    renderFeed()

    // Click the summary cell — that's the row's primary affordance.
    await user.click(screen.getByTestId('activity-feed-row-summary-0'))

    expect(navigateSpy).toHaveBeenCalledWith('/portfolio/portfolio-aaa')
  })

  it('does not navigate when subject has no detail page (task)', async () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([agentEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    renderFeed()

    // The task button is disabled — clicking does nothing. userEvent
    // refuses to click disabled buttons, so we assert that.
    const summaryButton = screen.getByTestId('activity-feed-row-summary-0')
    expect(summaryButton).toBeDisabled()
    expect(navigateSpy).not.toHaveBeenCalled()
  })

  it('shows skeleton while loading', () => {
    mockedUseActivity.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useActivity>)

    renderFeed()

    expect(screen.getByTestId('activity-feed-loading')).toBeInTheDocument()
  })

  it('shows error state on fetch failure', () => {
    mockedUseActivity.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useActivity>)

    renderFeed()

    expect(screen.getByTestId('activity-feed-error')).toBeInTheDocument()
  })

  it('shows empty state when there are no events', () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    renderFeed()

    // The shared EmptyState renders the message text.
    expect(
      screen.getByText(
        /No activity yet\. Trades, strategies, and tasks will show up here\./i
      )
    ).toBeInTheDocument()
  })

  it('toggles event-type filter chips and clears them with the Clear button', async () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([userEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    const user = userEvent.setup()
    renderFeed()

    // First call from initial render — no event_type filter, no actor
    // label.
    expect(mockedUseActivity).toHaveBeenLastCalledWith({
      limit: 50,
      event_type: undefined,
      actor_label: undefined,
    })

    // Activate the "Trades" chip.
    await user.click(
      screen.getByTestId('activity-feed-filter-event-type-trade')
    )
    expect(mockedUseActivity).toHaveBeenLastCalledWith({
      limit: 50,
      event_type: ['trade'],
      actor_label: undefined,
    })

    // Clear button surfaces only after at least one chip is active.
    const clear = screen.getByTestId('activity-feed-filter-clear')
    await user.click(clear)
    expect(mockedUseActivity).toHaveBeenLastCalledWith({
      limit: 50,
      event_type: undefined,
      actor_label: undefined,
    })
  })

  it('header row contains "When", "Actor", "What happened" columns', () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([userEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    renderFeed()

    const table = screen.getByTestId('activity-feed-table')
    expect(within(table).getByText('When')).toBeInTheDocument()
    expect(within(table).getByText('Actor')).toBeInTheDocument()
    expect(within(table).getByText('What happened')).toBeInTheDocument()
  })

  it('navigates to the actor drill-down when an actor link is clicked', async () => {
    // Stub window.scrollTo — jsdom doesn't implement it.
    const scrollSpy = vi
      .spyOn(window, 'scrollTo')
      .mockImplementation(() => undefined)

    mockedUseActivity.mockReturnValue({
      data: buildPage([agentEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    const user = userEvent.setup()
    renderFeed()

    await user.click(screen.getByTestId('activity-actor-link-claude-laptop'))

    expect(navigateSpy).toHaveBeenCalledWith(
      '/activity?actor_label=claude-laptop'
    )
    expect(scrollSpy).toHaveBeenCalled()
    scrollSpy.mockRestore()
  })

  it('renders the actor as a plain span (non-interactive) when already filtered', () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([agentEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    renderFeed('claude-laptop')

    // When filtered, the actor cell renders as the non-clickable
    // testid (the click handler is suppressed).
    expect(
      screen.queryByTestId('activity-actor-link-claude-laptop')
    ).not.toBeInTheDocument()
    expect(
      screen.getByTestId('activity-feed-actor-label-claude-laptop')
    ).toBeInTheDocument()
  })

  it('passes the actor_label filter through to the hook', () => {
    mockedUseActivity.mockReturnValue({
      data: buildPage([agentEvt]),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useActivity>)

    renderFeed('claude-laptop')

    expect(mockedUseActivity).toHaveBeenLastCalledWith({
      limit: 50,
      event_type: undefined,
      actor_label: 'claude-laptop',
    })
  })
})
