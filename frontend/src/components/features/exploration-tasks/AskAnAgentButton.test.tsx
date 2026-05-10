/**
 * Tests for the "Ask an agent" CTA — verifies pre-fill propagation,
 * dialog open/close, and the post-submit toast + remount flow.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AskAnAgentButton } from './AskAnAgentButton'
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

// Stub out react-hot-toast so the JSX-toast rendering doesn't interfere
// with the test container. We still verify success was called.
//
// vi.mock factories are hoisted to the top of the file; closing over a
// regular const breaks at runtime ("Cannot access 'X' before
// initialization"). Use vi.hoisted() to publish the spies in the same
// hoisted scope as the mock factory.
const { toastSuccess, toastDismiss, toastError } = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastDismiss: vi.fn(),
  toastError: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: toastSuccess,
    error: toastError,
    dismiss: toastDismiss,
  },
}))

const mockPortfolios: PortfolioDTO[] = [
  {
    id: 'portfolio-research',
    user_id: 'user-1',
    name: 'Research Portfolio',
    created_at: '2026-01-01T00:00:00Z',
  },
]

function paged<T>(items: T[]): PaginatedResponse<T> {
  return { items, total: items.length, limit: 20, offset: 0, has_more: false }
}

function buildCreatedTask(
  overrides: Partial<ExplorationTaskResponse> = {}
): ExplorationTaskResponse {
  return {
    id: 'new-task-id',
    created_by: 'user-1',
    prompt: 'Ask',
    status: 'OPEN',
    target_portfolio_id: null,
    tickers: null,
    constraints: null,
    claimed_by: null,
    claimed_at: null,
    findings: null,
    created_at: '2026-05-10T12:00:00Z',
    updated_at: '2026-05-10T12:00:00Z',
    ...overrides,
  }
}

interface RenderResult {
  user: ReturnType<typeof userEvent.setup>
  onSubmitted: ReturnType<typeof vi.fn>
}

function renderButton(props: {
  triggerContext: 'portfolio' | 'strategy'
  initialPortfolioId?: string
  initialTickers?: string[]
}): RenderResult {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  const onSubmitted = vi.fn()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AskAnAgentButton {...props} onSubmitted={onSubmitted} />
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), onSubmitted }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(portfoliosApi.list).mockResolvedValue(paged(mockPortfolios))
  // jsdom's HTMLDialogElement implementation lacks `showModal()` and
  // `close()` by default — stub them so the Dialog component's
  // imperative API doesn't throw in tests.
  HTMLDialogElement.prototype.showModal = vi.fn(function (
    this: HTMLDialogElement
  ) {
    this.setAttribute('open', '')
  })
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    this.removeAttribute('open')
  })
})

describe('AskAnAgentButton', () => {
  it('uses the portfolio-context data-testid by default', () => {
    renderButton({ triggerContext: 'portfolio' })
    expect(screen.getByTestId('ask-an-agent-portfolio-btn')).toBeInTheDocument()
  })

  it('uses the strategy-context data-testid for strategy pages', () => {
    renderButton({ triggerContext: 'strategy' })
    expect(screen.getByTestId('ask-an-agent-strategy-btn')).toBeInTheDocument()
  })

  it('does not open the dialog by default', () => {
    renderButton({ triggerContext: 'portfolio' })
    // The Dialog component renders its <dialog> element unconditionally
    // (it uses the native <dialog>'s showModal/close imperative API).
    // Verify the dialog is *not* open by checking the `open` attribute.
    const dialog = document.querySelector('dialog')
    expect(dialog).toBeTruthy()
    expect(dialog!.hasAttribute('open')).toBe(false)
  })

  it('opens the form dialog when the button is clicked', async () => {
    const { user } = renderButton({ triggerContext: 'portfolio' })

    await user.click(screen.getByTestId('ask-an-agent-portfolio-btn'))

    expect(
      screen.getByTestId('ask-an-agent-dialog-portfolio')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('exploration-task-create-form')
    ).toBeInTheDocument()
  })

  it('pre-fills the target portfolio when initialPortfolioId is provided', async () => {
    const { user } = renderButton({
      triggerContext: 'portfolio',
      initialPortfolioId: 'portfolio-research',
    })

    await user.click(screen.getByTestId('ask-an-agent-portfolio-btn'))

    await waitFor(() => {
      const select = screen.getByTestId(
        'exploration-task-create-portfolio-select'
      ) as HTMLSelectElement
      expect(select.value).toBe('portfolio-research')
    })
  })

  it('pre-fills the tickers input when initialTickers is provided', async () => {
    const { user } = renderButton({
      triggerContext: 'strategy',
      initialTickers: ['AAPL', 'MSFT'],
    })

    await user.click(screen.getByTestId('ask-an-agent-strategy-btn'))

    const tickersInput = (await screen.findByTestId(
      'exploration-task-create-tickers-input'
    )) as HTMLInputElement
    expect(tickersInput.value).toBe('AAPL, MSFT')
  })

  it('passes the pre-filled portfolio through to the create-task payload on submit', async () => {
    const created = buildCreatedTask({
      target_portfolio_id: 'portfolio-research',
    })
    vi.mocked(explorationTasksApi.create).mockResolvedValue(created)

    const { user, onSubmitted } = renderButton({
      triggerContext: 'portfolio',
      initialPortfolioId: 'portfolio-research',
    })

    await user.click(screen.getByTestId('ask-an-agent-portfolio-btn'))
    await user.type(
      screen.getByTestId('exploration-task-create-prompt-input'),
      'Run a mean-reversion sweep.'
    )
    await user.click(screen.getByTestId('exploration-task-create-submit-btn'))

    await waitFor(() =>
      expect(explorationTasksApi.create).toHaveBeenCalledTimes(1)
    )
    const payload = vi.mocked(explorationTasksApi.create).mock.calls[0][0]
    expect(payload.target_portfolio_id).toBe('portfolio-research')
    expect(payload.prompt).toBe('Run a mean-reversion sweep.')
    // The host should be notified with the created task.
    expect(onSubmitted).toHaveBeenCalledWith(created)
  })

  it('passes pre-filled tickers through to the create-task payload', async () => {
    vi.mocked(explorationTasksApi.create).mockResolvedValue(
      buildCreatedTask({ tickers: ['AAPL', 'MSFT'] })
    )

    const { user } = renderButton({
      triggerContext: 'strategy',
      initialTickers: ['AAPL', 'MSFT'],
    })

    await user.click(screen.getByTestId('ask-an-agent-strategy-btn'))
    await user.type(
      screen.getByTestId('exploration-task-create-prompt-input'),
      'Investigate this strategy.'
    )
    await user.click(screen.getByTestId('exploration-task-create-submit-btn'))

    await waitFor(() =>
      expect(explorationTasksApi.create).toHaveBeenCalledTimes(1)
    )
    expect(
      vi.mocked(explorationTasksApi.create).mock.calls[0][0].tickers
    ).toEqual(['AAPL', 'MSFT'])
  })

  it('surfaces a toast on success', async () => {
    vi.mocked(explorationTasksApi.create).mockResolvedValue(buildCreatedTask())
    const { user } = renderButton({ triggerContext: 'strategy' })

    await user.click(screen.getByTestId('ask-an-agent-strategy-btn'))
    await user.type(
      screen.getByTestId('exploration-task-create-prompt-input'),
      'Explore.'
    )
    await user.click(screen.getByTestId('exploration-task-create-submit-btn'))

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledTimes(1))
  })

  it('closes the dialog when the form Cancel button is clicked', async () => {
    const { user } = renderButton({ triggerContext: 'portfolio' })

    await user.click(screen.getByTestId('ask-an-agent-portfolio-btn'))
    expect(
      screen.getByTestId('ask-an-agent-dialog-portfolio')
    ).toBeInTheDocument()

    await user.click(screen.getByTestId('exploration-task-create-cancel-btn'))

    // After Cancel, the underlying dialog element is still in the tree
    // (jsdom keeps it mounted), but the `open` attribute is removed.
    const dialog = document.querySelector('dialog')
    expect(dialog).toBeTruthy()
    expect(dialog!.hasAttribute('open')).toBe(false)
  })
})
