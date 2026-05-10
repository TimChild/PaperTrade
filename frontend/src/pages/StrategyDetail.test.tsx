/**
 * Tests for the strategy detail page.
 *
 * Covers: page renders for a known strategy, the provenance section
 * mounts with the strategy id, the Ask-an-Agent button surfaces with the
 * strategy's tickers, and an error state is shown on fetch failure.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { StrategyDetail } from './StrategyDetail'
import { strategiesApi } from '@/services/api/strategies'
import { strategyActivationsApi } from '@/services/api/strategyActivations'
import { portfoliosApi } from '@/services/api/portfolios'
import { activityApi } from '@/services/api/activity'
import { explorationTasksApi } from '@/services/api/explorationTasks'
import type { StrategyResponse } from '@/services/api/types'

vi.mock('@/services/api/strategies', () => ({
  strategiesApi: {
    list: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    delete: vi.fn(),
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
    getBalance: vi.fn(),
    getHoldings: vi.fn(),
    create: vi.fn(),
    deposit: vi.fn(),
    withdraw: vi.fn(),
    executeTrade: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('@/services/api/activity', () => ({
  activityApi: { list: vi.fn() },
}))

vi.mock('@/services/api/explorationTasks', () => ({
  explorationTasksApi: {
    list: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    abandon: vi.fn(),
  },
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    dismiss: vi.fn(),
  },
}))

const mockStrategy: StrategyResponse = {
  id: 'strat-1',
  user_id: 'user-1',
  name: 'AAPL Mean Reversion',
  strategy_type: 'MOVING_AVERAGE_CROSSOVER',
  tickers: ['AAPL', 'MSFT'],
  parameters: { fast_window: 10, slow_window: 30, invest_fraction: 0.5 },
  created_at: '2026-04-01T10:00:00Z',
}

function renderPage(strategyId: string = 'strat-1'): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/strategies/${strategyId}`]}>
        <Routes>
          <Route path="/strategies/:id" element={<StrategyDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(strategiesApi.getById).mockResolvedValue(mockStrategy)
  vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValue(null)
  vi.mocked(portfoliosApi.list).mockResolvedValue({
    items: [],
    total: 0,
    limit: 20,
    offset: 0,
    has_more: false,
  })
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
  HTMLDialogElement.prototype.showModal = vi.fn(function (
    this: HTMLDialogElement
  ) {
    this.setAttribute('open', '')
  })
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    this.removeAttribute('open')
  })
})

describe('StrategyDetail page', () => {
  it('renders the strategy name when loaded', async () => {
    renderPage()
    expect(await screen.findByTestId('strategy-detail-name')).toHaveTextContent(
      'AAPL Mean Reversion'
    )
  })

  it('renders the strategy type badge', async () => {
    renderPage()
    expect(
      await screen.findByTestId('strategy-detail-type-badge')
    ).toHaveTextContent('Moving Average Crossover')
  })

  it('renders the provenance section', async () => {
    renderPage()
    expect(
      await screen.findByTestId('strategy-provenance-section-strat-1')
    ).toBeInTheDocument()
  })

  it('renders the Ask-an-Agent button in the header', async () => {
    renderPage()
    expect(
      await screen.findByTestId('ask-an-agent-strategy-btn')
    ).toBeInTheDocument()
  })

  it('renders all of the strategy tickers', async () => {
    renderPage()
    const tickers = await screen.findByTestId('strategy-detail-tickers')
    // Scope to the strategy-detail tickers panel — AAPL / MSFT also
    // appear inside the AskAnAgent dialog form (which is mounted but
    // closed) as pre-fill chips.
    expect(within(tickers).getByText('AAPL')).toBeInTheDocument()
    expect(within(tickers).getByText('MSFT')).toBeInTheDocument()
  })

  it('renders the parameters block', async () => {
    renderPage()
    const params = await screen.findByTestId('strategy-detail-parameters')
    expect(params).toHaveTextContent('fast_window')
    expect(params).toHaveTextContent('10')
    expect(params).toHaveTextContent('slow_window')
    expect(params).toHaveTextContent('30')
  })

  it('renders an error state when the strategy fails to load', async () => {
    vi.mocked(strategiesApi.getById).mockRejectedValue(
      new Error('Network error')
    )
    renderPage()
    expect(
      await screen.findByTestId('strategy-detail-error')
    ).toBeInTheDocument()
  })
})
