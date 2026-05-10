/**
 * Tests for StrategyActivationPanel — the per-strategy activation surface.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrategyActivationPanel } from '../StrategyActivationPanel'
import { strategyActivationsApi } from '@/services/api/strategyActivations'
import { portfoliosApi } from '@/services/api/portfolios'
import type {
  PortfolioDTO,
  StrategyActivationResponse,
  StrategyResponse,
} from '@/services/api/types'

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

const mockStrategy: StrategyResponse = {
  id: 'strategy-1',
  user_id: 'user-1',
  name: 'My Strategy',
  strategy_type: 'BUY_AND_HOLD',
  tickers: ['AAPL'],
  parameters: {},
  created_at: '2026-05-09T00:00:00Z',
}

const mockPortfolio: PortfolioDTO = {
  id: 'portfolio-1',
  user_id: 'user-1',
  name: 'Paper Trading Portfolio',
  created_at: '2026-05-01T00:00:00Z',
  portfolio_type: 'PAPER_TRADING',
}

const mockActivation: StrategyActivationResponse = {
  id: 'activation-1',
  user_id: 'user-1',
  strategy_id: 'strategy-1',
  portfolio_id: 'portfolio-1',
  status: 'ACTIVE',
  frequency: 'DAILY_MARKET_CLOSE',
  last_executed_at: null,
  last_error: null,
  created_at: '2026-05-09T00:00:00Z',
  updated_at: '2026-05-09T00:00:00Z',
}

function createWrapper(): ({
  children,
}: {
  children: React.ReactNode
}) => React.JSX.Element {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }): React.JSX.Element => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(portfoliosApi.list).mockResolvedValue({
    items: [mockPortfolio],
    total: 1,
    limit: 20,
    offset: 0,
    has_more: false,
  })
})

describe('StrategyActivationPanel — no activation', () => {
  it('renders an Activate button when no activation exists', async () => {
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValueOnce(null)

    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(
        screen.getByTestId('strategy-activate-button-strategy-1')
      ).toBeInTheDocument()
    })
  })

  it('opens the activation dialog when Activate is clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValueOnce(null)

    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(
        screen.getByTestId('strategy-activate-button-strategy-1')
      ).toBeInTheDocument()
    )
    await user.click(screen.getByTestId('strategy-activate-button-strategy-1'))

    expect(screen.getByTestId('activate-strategy-dialog')).toBeInTheDocument()
  })

  it('submits the form and calls activate', async () => {
    const user = userEvent.setup()
    // Use mockResolvedValue (not mockResolvedValueOnce) — the activate
    // mutation invalidates the by-strategy query, which refetches.
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValue(null)
    vi.mocked(strategyActivationsApi.activate).mockResolvedValueOnce(
      mockActivation
    )

    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(
        screen.getByTestId('strategy-activate-button-strategy-1')
      ).toBeInTheDocument()
    )
    await user.click(screen.getByTestId('strategy-activate-button-strategy-1'))
    // Wait for portfolios to populate the select.
    await waitFor(() =>
      expect(
        screen.getByTestId('activate-portfolio-select')
      ).toBeInTheDocument()
    )
    await user.selectOptions(
      screen.getByTestId('activate-portfolio-select'),
      'portfolio-1'
    )
    await user.click(screen.getByTestId('activate-strategy-submit'))

    await waitFor(() => {
      expect(strategyActivationsApi.activate).toHaveBeenCalledWith(
        'strategy-1',
        { portfolio_id: 'portfolio-1' }
      )
    })
  })

  it('shows validation error when no portfolio is selected', async () => {
    const user = userEvent.setup()
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValueOnce(null)

    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(
        screen.getByTestId('strategy-activate-button-strategy-1')
      ).toBeInTheDocument()
    )
    await user.click(screen.getByTestId('strategy-activate-button-strategy-1'))
    await waitFor(() =>
      expect(
        screen.getByTestId('activate-portfolio-select')
      ).toBeInTheDocument()
    )
    await user.click(screen.getByTestId('activate-strategy-submit'))

    expect(screen.getByTestId('activate-strategy-error')).toHaveTextContent(
      /please select a portfolio/i
    )
    expect(strategyActivationsApi.activate).not.toHaveBeenCalled()
  })

  it('shows guidance when the user has no paper-trading portfolios', async () => {
    vi.mocked(portfoliosApi.list).mockResolvedValueOnce({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
      has_more: false,
    })
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValueOnce(null)
    const user = userEvent.setup()

    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(
        screen.getByTestId('strategy-activate-button-strategy-1')
      ).toBeInTheDocument()
    )
    await user.click(screen.getByTestId('strategy-activate-button-strategy-1'))

    await waitFor(() =>
      expect(
        screen.getByTestId('activate-strategy-no-portfolios')
      ).toBeInTheDocument()
    )
    expect(screen.getByTestId('activate-strategy-submit')).toBeDisabled()
  })
})

describe('StrategyActivationPanel — with active activation', () => {
  beforeEach(() => {
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValue(
      mockActivation
    )
  })

  it('renders status badge, portfolio name, and Last Run = Never', async () => {
    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(screen.getByTestId('activation-status-ACTIVE')).toBeInTheDocument()
    )
    await waitFor(() =>
      expect(
        screen.getByTestId('strategy-activation-portfolio-strategy-1')
      ).toHaveTextContent('Paper Trading Portfolio')
    )
    expect(
      screen.getByTestId('strategy-activation-last-run-strategy-1')
    ).toHaveTextContent('Never')
  })

  it('shows Run Now and Deactivate buttons for ACTIVE status', async () => {
    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(
        screen.getByTestId('strategy-run-now-button-strategy-1')
      ).toBeInTheDocument()
    )
    expect(
      screen.getByTestId('strategy-deactivate-button-strategy-1')
    ).toBeInTheDocument()
  })

  it('runs the activation when Run Now is confirmed', async () => {
    const user = userEvent.setup()
    vi.mocked(strategyActivationsApi.runNow).mockResolvedValueOnce({
      activation: mockActivation,
      succeeded: true,
      trades: 1,
      error: null,
    })

    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(
        screen.getByTestId('strategy-run-now-button-strategy-1')
      ).toBeInTheDocument()
    )
    await user.click(screen.getByTestId('strategy-run-now-button-strategy-1'))

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()
    await user.click(screen.getByTestId('confirm-dialog-confirm'))

    await waitFor(() =>
      expect(strategyActivationsApi.runNow).toHaveBeenCalledWith('activation-1')
    )
  })

  it('deactivates when the deactivate confirm is clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(strategyActivationsApi.deactivate).mockResolvedValueOnce({
      ...mockActivation,
      status: 'PAUSED',
    })

    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(
        screen.getByTestId('strategy-deactivate-button-strategy-1')
      ).toBeInTheDocument()
    )
    await user.click(
      screen.getByTestId('strategy-deactivate-button-strategy-1')
    )
    await user.click(screen.getByTestId('confirm-dialog-confirm'))

    await waitFor(() =>
      expect(strategyActivationsApi.deactivate).toHaveBeenCalledWith(
        'activation-1',
        undefined
      )
    )
  })
})

describe('StrategyActivationPanel — error status', () => {
  it('renders the last_error message when status is ERROR', async () => {
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValueOnce({
      ...mockActivation,
      status: 'ERROR',
      last_error: 'Market data unavailable for AAPL',
    })

    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(screen.getByTestId('activation-status-ERROR')).toBeInTheDocument()
    )
    expect(
      screen.getByTestId('strategy-activation-last-error-strategy-1')
    ).toHaveTextContent('Market data unavailable for AAPL')
  })
})

describe('StrategyActivationPanel — stopped status', () => {
  it('disables Run Now and hides Deactivate when status is STOPPED', async () => {
    vi.mocked(strategyActivationsApi.getByStrategy).mockResolvedValueOnce({
      ...mockActivation,
      status: 'STOPPED',
    })

    render(<StrategyActivationPanel strategy={mockStrategy} />, {
      wrapper: createWrapper(),
    })

    await waitFor(() =>
      expect(
        screen.getByTestId('activation-status-STOPPED')
      ).toBeInTheDocument()
    )
    expect(
      screen.getByTestId('strategy-run-now-button-strategy-1')
    ).toBeDisabled()
    expect(
      screen.queryByTestId('strategy-deactivate-button-strategy-1')
    ).not.toBeInTheDocument()
  })
})
