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

/**
 * Helper to build a `findings` block. Every Phase E2 field defaults to
 * the v1 (no structured data) shape so individual tests can opt-in.
 */
function makeFindings(
  overrides: Partial<NonNullable<ExplorationTaskResponse['findings']>> = {}
): NonNullable<ExplorationTaskResponse['findings']> {
  return {
    summary: 'Found a winning variant. Sharpe 1.4, max drawdown 8%.',
    backtest_run_ids: ['bt-1', 'bt-2'],
    strategy_ids: ['s-1'],
    notes: ['Tried 5 parameter sweeps', 'Best one was #3'],
    recommended_strategy_id: null,
    recommended_parameters: null,
    metrics: null,
    comparison_to_baseline: null,
    confidence: null,
    ...overrides,
  }
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
      findings: makeFindings(),
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

  it('does not render structured blocks when fields are null', async () => {
    renderDetail({
      ...baseTask,
      status: 'DONE',
      claimed_by: 'agent-a',
      claimed_at: '2026-05-09T13:00:00Z',
      findings: makeFindings(),
    })

    // Wait for the page to load.
    await screen.findByTestId('exploration-task-detail-findings-summary')

    // Structured E2 sections must NOT render when their fields are null —
    // backward compatibility with v1 narrative-only findings.
    expect(
      screen.queryByTestId('exploration-task-detail-recommended')
    ).toBeNull()
    expect(screen.queryByTestId('exploration-task-detail-metrics')).toBeNull()
    expect(
      screen.queryByTestId('exploration-task-detail-comparison')
    ).toBeNull()
    expect(
      screen.queryByTestId('exploration-task-detail-confidence')
    ).toBeNull()
  })
})

describe('ExplorationTaskDetail (DONE, structured E2 payload)', () => {
  it('renders the recommended-strategy banner with parameters', async () => {
    renderDetail({
      ...baseTask,
      status: 'DONE',
      claimed_by: 'agent-a',
      claimed_at: '2026-05-09T13:00:00Z',
      findings: makeFindings({
        recommended_strategy_id: 's-1',
        recommended_parameters: {
          fast_window: 20,
          slow_window: 50,
          invest_fraction: '1.0',
        },
      }),
    })

    const banner = await screen.findByTestId(
      'exploration-task-detail-recommended'
    )
    expect(banner).toBeInTheDocument()
    expect(
      screen.getByTestId('exploration-task-detail-recommended-strategy-id')
    ).toHaveTextContent('s-1')

    // Parameter list renders one row per key.
    const params = screen.getByTestId('exploration-task-detail-parameters')
    expect(params).toHaveTextContent('fast_window')
    expect(params).toHaveTextContent('20')
    expect(params).toHaveTextContent('slow_window')
    expect(params).toHaveTextContent('50')
    expect(params).toHaveTextContent('invest_fraction')
    expect(params).toHaveTextContent('1.0')
  })

  it('renders the metrics block with gain/loss tones', async () => {
    renderDetail({
      ...baseTask,
      status: 'DONE',
      claimed_by: 'agent-a',
      claimed_at: '2026-05-09T13:00:00Z',
      findings: makeFindings({
        metrics: {
          total_return_pct: '24.4',
          sharpe_ratio: '1.32',
          max_drawdown_pct: '-11.7',
          n_trades: 14,
          annualized_return_pct: '12.5',
        },
      }),
    })

    const metrics = await screen.findByTestId('exploration-task-detail-metrics')
    expect(metrics).toBeInTheDocument()

    const totalReturn = screen.getByTestId('metric-finding-total-return-value')
    expect(totalReturn).toHaveClass('text-gain')
    expect(totalReturn).toHaveTextContent('24.40%')

    const sharpe = screen.getByTestId('metric-finding-sharpe-value')
    expect(sharpe).toHaveTextContent('1.32')

    const maxDrawdown = screen.getByTestId('metric-finding-max-drawdown-value')
    // Max drawdown is negative — displays in loss tone.
    expect(maxDrawdown).toHaveClass('text-loss')

    expect(
      screen.getByTestId('metric-finding-n-trades-value')
    ).toHaveTextContent('14')
    expect(
      screen.getByTestId('metric-finding-annualized-value')
    ).toHaveTextContent('12.50%')
  })

  it('omits optional metric tiles when their values are null', async () => {
    renderDetail({
      ...baseTask,
      status: 'DONE',
      claimed_by: 'agent-a',
      claimed_at: '2026-05-09T13:00:00Z',
      findings: makeFindings({
        metrics: {
          total_return_pct: '5.0',
          sharpe_ratio: null,
          max_drawdown_pct: null,
          n_trades: null,
          annualized_return_pct: null,
        },
      }),
    })

    await screen.findByTestId('exploration-task-detail-metrics')
    expect(
      screen.getByTestId('metric-finding-total-return')
    ).toBeInTheDocument()
    // Optional tiles are absent when their underlying value is null.
    expect(screen.queryByTestId('metric-finding-sharpe')).toBeNull()
    expect(screen.queryByTestId('metric-finding-max-drawdown')).toBeNull()
    expect(screen.queryByTestId('metric-finding-n-trades')).toBeNull()
    expect(screen.queryByTestId('metric-finding-annualized')).toBeNull()
  })

  it('renders the comparison-to-baseline table with delta tones', async () => {
    renderDetail({
      ...baseTask,
      status: 'DONE',
      claimed_by: 'agent-a',
      claimed_at: '2026-05-09T13:00:00Z',
      findings: makeFindings({
        comparison_to_baseline: {
          baseline_strategy_id: 'baseline-strategy-uuid',
          baseline_total_return_pct: '18.1',
          delta_total_return_pct: '6.3',
          delta_sharpe: '0.38',
        },
      }),
    })

    await screen.findByTestId('exploration-task-detail-comparison')

    const deltaReturn = screen.getByTestId(
      'exploration-task-detail-comparison-delta-return'
    )
    // Positive delta -> gain tone.
    expect(deltaReturn).toHaveClass('text-gain')

    const deltaSharpe = screen.getByTestId(
      'exploration-task-detail-comparison-delta-sharpe'
    )
    expect(deltaSharpe).toHaveClass('text-gain')

    expect(
      screen.getByTestId('exploration-task-detail-comparison-baseline-id')
    ).toHaveTextContent('baseline-strategy-uuid')
  })

  it('renders the confidence bar with correct width', async () => {
    renderDetail({
      ...baseTask,
      status: 'DONE',
      claimed_by: 'agent-a',
      claimed_at: '2026-05-09T13:00:00Z',
      findings: makeFindings({ confidence: 0.72 }),
    })

    await screen.findByTestId('exploration-task-detail-confidence')
    expect(
      screen.getByTestId('exploration-task-detail-confidence-label')
    ).toHaveTextContent('72%')

    // The fill bar has a style attribute reflecting the percentage width.
    const fill = screen.getByTestId('exploration-task-detail-confidence-fill')
    expect(fill).toHaveAttribute('style', expect.stringContaining('72%'))
  })

  it('renders confidence of 0 without crashing', async () => {
    renderDetail({
      ...baseTask,
      status: 'DONE',
      claimed_by: 'agent-a',
      claimed_at: '2026-05-09T13:00:00Z',
      findings: makeFindings({ confidence: 0.0 }),
    })

    await screen.findByTestId('exploration-task-detail-confidence')
    expect(
      screen.getByTestId('exploration-task-detail-confidence-label')
    ).toHaveTextContent('0%')
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
