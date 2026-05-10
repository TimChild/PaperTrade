/**
 * Tests for StrategyCard component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { StrategyCard } from '../StrategyCard'
import type { StrategyResponse } from '@/services/api/types'
import * as strategiesApi from '@/services/api/strategies'
import { strategyActivationsApi } from '@/services/api/strategyActivations'
import { portfoliosApi } from '@/services/api/portfolios'
import { activityApi } from '@/services/api/activity'
import { explorationTasksApi } from '@/services/api/explorationTasks'

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/services/api/strategyActivations', () => ({
  strategyActivationsApi: {
    activate: vi.fn(),
    getByStrategy: vi.fn(),
    list: vi.fn(),
    deactivate: vi.fn(),
    runNow: vi.fn(),
  },
}))

vi.mock('@/services/api/portfolios', () => ({
  portfoliosApi: {
    list: vi.fn(),
    getById: vi.fn(),
  },
}))

// Provenance hook touches the activity + exploration-tasks APIs. Default
// to "no agent activity, no recommending task" so the StrategyCard tests
// see the human-authored case (no chip rendered).
vi.mock('@/services/api/activity', () => ({
  activityApi: {
    list: vi.fn(),
  },
}))

vi.mock('@/services/api/explorationTasks', () => ({
  explorationTasksApi: {
    list: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    abandon: vi.fn(),
  },
}))

beforeEach(() => {
  vi.clearAllMocks()
  // Default: no activation exists for the strategy under test, and portfolios
  // list returns an empty page. Each test can override before render() if it
  // needs other behaviour.
  vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValue(null)
  vi.mocked(portfoliosApi.list).mockResolvedValue({
    items: [],
    total: 0,
    limit: 20,
    offset: 0,
    has_more: false,
  })
  // Provenance probes — empty by default so the chip renders nothing.
  vi.mocked(activityApi.list).mockResolvedValue({
    items: [],
    total: 0,
    limit: 100,
    offset: 0,
    has_more: false,
  })
  vi.mocked(explorationTasksApi.list).mockResolvedValue({
    items: [],
    total: 0,
    limit: 100,
    offset: 0,
    has_more: false,
  })
})

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

const mockStrategy: StrategyResponse = {
  id: 'strategy-abc',
  user_id: 'user-1',
  name: 'My Buy & Hold',
  strategy_type: 'BUY_AND_HOLD',
  tickers: ['AAPL', 'MSFT', 'GOOG'],
  parameters: { allocation: { AAPL: 0.4, MSFT: 0.4, GOOG: 0.2 } },
  created_at: '2024-01-15T10:00:00Z',
}

describe('StrategyCard', () => {
  it('renders strategy name', () => {
    const Wrapper = createWrapper()
    render(<StrategyCard strategy={mockStrategy} />, { wrapper: Wrapper })

    expect(screen.getByText('My Buy & Hold')).toBeInTheDocument()
  })

  it('renders strategy type badge', () => {
    const Wrapper = createWrapper()
    render(<StrategyCard strategy={mockStrategy} />, { wrapper: Wrapper })

    expect(screen.getByTestId('strategy-type-badge')).toHaveTextContent(
      'Buy & Hold'
    )
  })

  it('renders all tickers', () => {
    const Wrapper = createWrapper()
    render(<StrategyCard strategy={mockStrategy} />, { wrapper: Wrapper })

    expect(screen.getByText('AAPL')).toBeInTheDocument()
    expect(screen.getByText('MSFT')).toBeInTheDocument()
    expect(screen.getByText('GOOG')).toBeInTheDocument()
  })

  it('renders the correct test id', () => {
    const Wrapper = createWrapper()
    render(<StrategyCard strategy={mockStrategy} />, { wrapper: Wrapper })

    expect(screen.getByTestId('strategy-card-strategy-abc')).toBeInTheDocument()
  })

  it('shows confirm dialog when delete button is clicked', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<StrategyCard strategy={mockStrategy} />, { wrapper: Wrapper })

    const deleteBtn = screen.getByTestId('strategy-delete-button')
    await user.click(deleteBtn)

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()
    expect(screen.getByText(/delete strategy/i)).toBeInTheDocument()
  })

  it('hides confirm dialog when cancel is clicked', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<StrategyCard strategy={mockStrategy} />, { wrapper: Wrapper })

    await user.click(screen.getByTestId('strategy-delete-button'))
    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()

    await user.click(screen.getByTestId('confirm-dialog-cancel'))
    expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument()
  })

  it('calls delete API when confirm is clicked', async () => {
    const user = userEvent.setup()
    vi.spyOn(strategiesApi.strategiesApi, 'delete').mockResolvedValueOnce(
      undefined
    )

    const Wrapper = createWrapper()
    render(<StrategyCard strategy={mockStrategy} />, { wrapper: Wrapper })

    await user.click(screen.getByTestId('strategy-delete-button'))
    await user.click(screen.getByTestId('confirm-dialog-confirm'))

    await waitFor(() => {
      expect(strategiesApi.strategiesApi.delete).toHaveBeenCalledWith(
        'strategy-abc'
      )
    })
  })

  it('renders DOLLAR_COST_AVERAGING type badge correctly', () => {
    const Wrapper = createWrapper()
    const dcaStrategy: StrategyResponse = {
      ...mockStrategy,
      strategy_type: 'DOLLAR_COST_AVERAGING',
    }
    render(<StrategyCard strategy={dcaStrategy} />, { wrapper: Wrapper })

    expect(screen.getByTestId('strategy-type-badge')).toHaveTextContent(
      'Dollar Cost Averaging'
    )
  })

  it('renders MOVING_AVERAGE_CROSSOVER type badge correctly', () => {
    const Wrapper = createWrapper()
    const macStrategy: StrategyResponse = {
      ...mockStrategy,
      strategy_type: 'MOVING_AVERAGE_CROSSOVER',
    }
    render(<StrategyCard strategy={macStrategy} />, { wrapper: Wrapper })

    expect(screen.getByTestId('strategy-type-badge')).toHaveTextContent(
      'Moving Average Crossover'
    )
  })
})
