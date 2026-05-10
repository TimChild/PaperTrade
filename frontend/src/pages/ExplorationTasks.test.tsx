/**
 * Unit tests for the ExplorationTasks list page.
 *
 * These mock at the API-client boundary (`@/services/api/explorationTasks`
 * and `@/services/api/portfolios`) so the entire page renders end-to-end
 * with real query wiring. We assert on what the user sees, not internal
 * state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ExplorationTasks } from './ExplorationTasks'
import { explorationTasksApi } from '@/services/api/explorationTasks'
import { portfoliosApi } from '@/services/api/portfolios'
import type {
  ExplorationTaskResponse,
  PaginatedResponse,
  PortfolioDTO,
} from '@/services/api/types'

vi.mock('@/services/api/explorationTasks', () => ({
  explorationTasksApi: {
    list: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    abandon: vi.fn(),
  },
}))

vi.mock('@/services/api/portfolios', () => ({
  portfoliosApi: {
    list: vi.fn(),
    getById: vi.fn(),
    getBalance: vi.fn(),
    getHoldings: vi.fn(),
    create: vi.fn(),
    deposit: vi.fn(),
    withdraw: vi.fn(),
    executeTrade: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockPortfolios: PortfolioDTO[] = [
  {
    id: 'portfolio-1',
    user_id: 'user-1',
    name: 'Research Portfolio',
    created_at: '2026-01-01T00:00:00Z',
  },
]

const tasksFixture: ExplorationTaskResponse[] = [
  {
    id: 'task-open',
    created_by: 'user-1',
    prompt: 'Mean reversion on AAPL\n\nFocus on the last quarter.',
    status: 'OPEN',
    target_portfolio_id: 'portfolio-1',
    tickers: ['AAPL', 'MSFT'],
    constraints: null,
    claimed_by: null,
    claimed_at: null,
    findings: null,
    created_at: '2026-05-09T12:00:00Z',
    updated_at: '2026-05-09T12:00:00Z',
  },
  {
    id: 'task-claimed',
    created_by: 'user-1',
    prompt: 'Trend following sweep\n\nBacktest 5 candidates.',
    status: 'IN_PROGRESS',
    target_portfolio_id: null,
    tickers: ['SPY'],
    constraints: null,
    claimed_by: 'claude-code-laptop-explorer',
    claimed_at: '2026-05-09T13:00:00Z',
    findings: null,
    created_at: '2026-05-08T08:00:00Z',
    updated_at: '2026-05-09T13:00:00Z',
  },
  {
    id: 'task-done',
    created_by: 'user-1',
    prompt: 'Done task',
    status: 'DONE',
    target_portfolio_id: null,
    tickers: null,
    constraints: null,
    claimed_by: 'agent-a',
    claimed_at: '2026-05-07T08:00:00Z',
    findings: {
      summary: 'Found a winning variant.',
      backtest_run_ids: [],
      strategy_ids: [],
      notes: null,
      recommended_strategy_id: null,
      recommended_parameters: null,
      metrics: null,
      comparison_to_baseline: null,
      confidence: null,
    },
    created_at: '2026-05-06T08:00:00Z',
    updated_at: '2026-05-07T10:00:00Z',
  },
]

function paged<T>(items: T[]): PaginatedResponse<T> {
  return { items, total: items.length, limit: 20, offset: 0, has_more: false }
}

function renderPage(): { user: ReturnType<typeof userEvent.setup> } {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/exploration-tasks']}>
        <Routes>
          <Route path="/exploration-tasks" element={<ExplorationTasks />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { user: userEvent.setup() }
}

describe('ExplorationTasks (list view)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(portfoliosApi.list).mockResolvedValue(paged(mockPortfolios))
  })

  it('renders the page header and the New task CTA', async () => {
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged(tasksFixture))
    renderPage()

    expect(
      await screen.findByRole('heading', { name: /Exploration tasks/i })
    ).toBeInTheDocument()
    expect(screen.getByTestId('exploration-task-new-btn')).toBeInTheDocument()
  })

  it('renders a row per task with status badges and titles', async () => {
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged(tasksFixture))
    renderPage()

    await waitFor(() =>
      expect(
        screen.getByTestId('exploration-task-list-row-task-open')
      ).toBeInTheDocument()
    )

    // Each row carries a status badge.
    expect(
      screen.getByTestId('exploration-task-status-OPEN')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('exploration-task-status-IN_PROGRESS')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('exploration-task-status-DONE')
    ).toBeInTheDocument()

    // Titles render from the prompt's first line.
    expect(screen.getByText(/Mean reversion on AAPL/)).toBeInTheDocument()
    expect(screen.getByText(/Trend following sweep/)).toBeInTheDocument()

    // The IN_PROGRESS row surfaces the claimed agent label.
    expect(screen.getByText('claude-code-laptop-explorer')).toBeInTheDocument()
  })

  it('orders rows newest-first', async () => {
    vi.mocked(explorationTasksApi.list).mockResolvedValue(
      // Deliberately scramble order — the page should sort.
      paged([tasksFixture[2], tasksFixture[0], tasksFixture[1]])
    )
    renderPage()

    const rows = await screen.findAllByTestId(/^exploration-task-list-row-/)
    expect(rows).toHaveLength(3)
    expect(rows[0]).toHaveAttribute(
      'data-testid',
      'exploration-task-list-row-task-open'
    )
    expect(rows[1]).toHaveAttribute(
      'data-testid',
      'exploration-task-list-row-task-claimed'
    )
    expect(rows[2]).toHaveAttribute(
      'data-testid',
      'exploration-task-list-row-task-done'
    )
  })

  it('shows the empty state on a fresh queue', async () => {
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged([]))
    renderPage()

    expect(
      await screen.findByText(/Queue your first exploration task/i)
    ).toBeInTheDocument()
  })

  it('renders queue stats once there are tasks', async () => {
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged(tasksFixture))
    renderPage()

    await screen.findByTestId('exploration-tasks-stats')

    expect(
      screen.getByTestId('exploration-tasks-stat-open-value')
    ).toHaveTextContent('1')
    expect(
      screen.getByTestId('exploration-tasks-stat-claimed-value')
    ).toHaveTextContent('1')
    expect(
      screen.getByTestId('exploration-tasks-stat-done-value')
    ).toHaveTextContent('1')
  })

  it('passes status filter to the list query when a pill is clicked', async () => {
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged(tasksFixture))
    const { user } = renderPage()

    await screen.findByTestId('exploration-tasks-filter-OPEN')
    await user.click(screen.getByTestId('exploration-tasks-filter-OPEN'))

    await waitFor(() => {
      expect(explorationTasksApi.list).toHaveBeenCalledWith({
        scope: 'mine',
        status: 'OPEN',
      })
    })
  })

  it('opens the create form when New task is clicked', async () => {
    vi.mocked(explorationTasksApi.list).mockResolvedValue(paged(tasksFixture))
    const { user } = renderPage()

    await user.click(await screen.findByTestId('exploration-task-new-btn'))
    expect(
      screen.getByTestId('exploration-task-create-form')
    ).toBeInTheDocument()
  })

  it('renders an error block if the list query fails', async () => {
    vi.mocked(explorationTasksApi.list).mockRejectedValue(new Error('boom'))
    renderPage()

    expect(
      await screen.findByTestId('exploration-tasks-error')
    ).toBeInTheDocument()
  })
})
