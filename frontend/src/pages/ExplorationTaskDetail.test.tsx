/**
 * Unit tests for the ExplorationTaskDetail page. Mocks the API client so
 * we can verify the detail layout for every status (OPEN / IN_PROGRESS /
 * DONE / ABANDONED) and the abandon flow without hitting the network.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ExplorationTaskDetail } from './ExplorationTaskDetail'
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

function paged<T>(items: T[]): PaginatedResponse<T> {
  return { items, total: items.length, limit: 20, offset: 0, has_more: false }
}

const baseTask: ExplorationTaskResponse = {
  id: 'task-1',
  created_by: 'user-1',
  prompt:
    'Mean reversion on AAPL\n\nFocus on Q1, watch FOMC reactions, surface the strongest variant.',
  status: 'OPEN',
  target_portfolio_id: 'portfolio-1',
  tickers: ['AAPL', 'MSFT'],
  constraints: null,
  claimed_by: null,
  claimed_at: null,
  findings: null,
  created_at: '2026-05-09T12:00:00Z',
  updated_at: '2026-05-09T12:00:00Z',
}

function renderDetail(task: ExplorationTaskResponse): {
  user: ReturnType<typeof userEvent.setup>
} {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  vi.mocked(explorationTasksApi.getById).mockResolvedValue(task)

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/exploration-tasks/${task.id}`]}>
        <Routes>
          <Route
            path="/exploration-tasks/:id"
            element={<ExplorationTaskDetail />}
          />
          <Route
            path="/exploration-tasks"
            element={<div data-testid="list-view-stub">List</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { user: userEvent.setup() }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(portfoliosApi.list).mockResolvedValue(paged(mockPortfolios))
})

describe('ExplorationTaskDetail (OPEN)', () => {
  it('renders the title, prompt body, and metadata', async () => {
    renderDetail(baseTask)

    expect(
      await screen.findByTestId('exploration-task-detail-title')
    ).toHaveTextContent('Mean reversion on AAPL')

    expect(
      screen.getByTestId('exploration-task-detail-prompt')
    ).toHaveTextContent(/Focus on Q1, watch FOMC reactions/)

    // Status badge.
    expect(
      screen.getByTestId('exploration-task-status-OPEN')
    ).toBeInTheDocument()

    // Tickers chips.
    const tickers = screen.getByTestId('exploration-task-detail-tickers')
    expect(tickers).toHaveTextContent('AAPL')
    expect(tickers).toHaveTextContent('MSFT')

    // Linked portfolio.
    const portfolioLink = screen.getByTestId(
      'exploration-task-detail-portfolio-link'
    )
    expect(portfolioLink).toHaveTextContent('Research Portfolio')
    expect(portfolioLink).toHaveAttribute('href', '/portfolio/portfolio-1')
  })

  it('shows the abandon CTA only for OPEN tasks', async () => {
    renderDetail(baseTask)
    expect(
      await screen.findByTestId('exploration-task-detail-abandon-btn')
    ).toBeInTheDocument()
  })

  it('renders the "not yet claimed" claim summary', async () => {
    renderDetail(baseTask)
    expect(
      await screen.findByTestId('exploration-task-detail-claim-open')
    ).toHaveTextContent(/Not yet claimed/)
  })
})

describe('ExplorationTaskDetail (IN_PROGRESS)', () => {
  it('shows the claimed-by agent label and timestamp', async () => {
    renderDetail({
      ...baseTask,
      status: 'IN_PROGRESS',
      claimed_by: 'claude-code-laptop-explorer',
      claimed_at: '2026-05-09T13:00:00Z',
    })

    expect(
      await screen.findByTestId('exploration-task-detail-claimed-by')
    ).toHaveTextContent('claude-code-laptop-explorer')

    // Abandon CTA hidden for non-OPEN tasks.
    expect(
      screen.queryByTestId('exploration-task-detail-abandon-btn')
    ).toBeNull()
  })
})

describe('ExplorationTaskDetail (DONE)', () => {
  it('renders the findings summary and notes', async () => {
    renderDetail({
      ...baseTask,
      status: 'DONE',
      claimed_by: 'agent-a',
      claimed_at: '2026-05-09T13:00:00Z',
      findings: {
        summary: 'Found a winning variant. Sharpe 1.4, max drawdown 8%.',
        backtest_run_ids: ['bt-1', 'bt-2'],
        strategy_ids: ['s-1'],
        notes: ['Tried 5 parameter sweeps', 'Best one was #3'],
      },
    })

    expect(
      await screen.findByTestId('exploration-task-detail-findings-summary')
    ).toHaveTextContent(/Sharpe 1.4/)

    // Notes render as a list.
    const notes = screen.getByTestId('exploration-task-detail-findings-notes')
    expect(notes).toHaveTextContent('Tried 5 parameter sweeps')
    expect(notes).toHaveTextContent('Best one was #3')

    // Backtest IDs render as links to the detail pages.
    const backtests = screen.getByTestId(
      'exploration-task-detail-findings-backtests'
    )
    expect(
      screen.getByTestId('exploration-task-detail-backtest-link-bt-1')
    ).toHaveAttribute('href', '/backtests/bt-1')
    expect(backtests).toHaveTextContent('bt-2')

    // Strategy IDs render as plain mono text (no detail page yet).
    expect(
      screen.getByTestId('exploration-task-detail-strategy-id-s-1')
    ).toBeInTheDocument()
  })
})

describe('ExplorationTaskDetail (ABANDONED)', () => {
  it('renders the status badge and hides the abandon CTA', async () => {
    renderDetail({
      ...baseTask,
      status: 'ABANDONED',
    })
    expect(
      await screen.findByTestId('exploration-task-status-ABANDONED')
    ).toBeInTheDocument()
    expect(
      screen.queryByTestId('exploration-task-detail-abandon-btn')
    ).toBeNull()
  })
})

describe('ExplorationTaskDetail abandon flow', () => {
  it('opens a confirm dialog and abandons on confirmation', async () => {
    vi.mocked(explorationTasksApi.abandon).mockResolvedValue(undefined)
    const { user } = renderDetail(baseTask)

    await user.click(
      await screen.findByTestId('exploration-task-detail-abandon-btn')
    )

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()

    await user.click(screen.getByTestId('confirm-dialog-confirm'))

    await waitFor(() =>
      expect(explorationTasksApi.abandon).toHaveBeenCalledWith('task-1')
    )

    // After abandoning, the page navigates to the list stub.
    await waitFor(() =>
      expect(screen.getByTestId('list-view-stub')).toBeInTheDocument()
    )
  })

  it('cancels without abandoning', async () => {
    const { user } = renderDetail(baseTask)
    await user.click(
      await screen.findByTestId('exploration-task-detail-abandon-btn')
    )
    await user.click(screen.getByTestId('confirm-dialog-cancel'))

    expect(explorationTasksApi.abandon).not.toHaveBeenCalled()
    expect(screen.queryByTestId('confirm-dialog')).toBeNull()
  })
})
