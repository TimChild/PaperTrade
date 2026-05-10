/**
 * Tests for the exploration task create form. Mocks the API client so we
 * exercise the validation, payload composition, and success/cancel
 * callbacks without hitting the network.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { CreateExplorationTaskForm } from './CreateExplorationTaskForm'
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

function buildCreatedTask(): ExplorationTaskResponse {
  return {
    id: 'created-id',
    created_by: 'user-1',
    prompt: 'Mean reversion on AAPL\n\nFocus on Q1.',
    status: 'OPEN',
    target_portfolio_id: 'portfolio-1',
    tickers: ['AAPL'],
    constraints: null,
    claimed_by: null,
    claimed_at: null,
    findings: null,
    created_at: '2026-05-09T12:00:00Z',
    updated_at: '2026-05-09T12:00:00Z',
  }
}

function renderForm(): {
  user: ReturnType<typeof userEvent.setup>
  onCancel: ReturnType<typeof vi.fn>
} {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  const onCancel = vi.fn()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/exploration-tasks']}>
        <Routes>
          <Route
            path="/exploration-tasks"
            element={<CreateExplorationTaskForm onCancel={onCancel} />}
          />
          <Route
            path="/exploration-tasks/:id"
            element={<div data-testid="detail-view-stub">Detail</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), onCancel }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(portfoliosApi.list).mockResolvedValue(paged(mockPortfolios))
})

describe('CreateExplorationTaskForm', () => {
  it('rejects submission when the prompt is empty', async () => {
    const { user } = renderForm()
    await user.click(screen.getByTestId('exploration-task-create-submit-btn'))

    expect(
      await screen.findByTestId('exploration-task-create-prompt-error')
    ).toHaveTextContent(/Prompt is required/i)
    expect(explorationTasksApi.create).not.toHaveBeenCalled()
  })

  it('folds the title into the prompt as a leading line', async () => {
    vi.mocked(explorationTasksApi.create).mockResolvedValue(buildCreatedTask())
    const { user } = renderForm()

    await user.type(
      screen.getByTestId('exploration-task-create-title-input'),
      'Mean reversion on AAPL'
    )
    await user.type(
      screen.getByTestId('exploration-task-create-prompt-input'),
      'Focus on Q1.'
    )
    await user.click(screen.getByTestId('exploration-task-create-submit-btn'))

    await waitFor(() =>
      expect(explorationTasksApi.create).toHaveBeenCalledTimes(1)
    )
    const payload = vi.mocked(explorationTasksApi.create).mock.calls[0][0]
    expect(payload.prompt).toBe('Mean reversion on AAPL\n\nFocus on Q1.')
  })

  it('parses comma-separated tickers and uppercases them', async () => {
    vi.mocked(explorationTasksApi.create).mockResolvedValue(buildCreatedTask())
    const { user } = renderForm()

    await user.type(
      screen.getByTestId('exploration-task-create-prompt-input'),
      'Explore.'
    )
    await user.type(
      screen.getByTestId('exploration-task-create-tickers-input'),
      'aapl, msft, , goog'
    )

    // Chips render from the parsed tickers.
    expect(
      screen.getByTestId('exploration-task-create-tickers-chips')
    ).toHaveTextContent(/AAPLMSFTGOOG/)

    await user.click(screen.getByTestId('exploration-task-create-submit-btn'))

    await waitFor(() =>
      expect(explorationTasksApi.create).toHaveBeenCalledTimes(1)
    )
    const payload = vi.mocked(explorationTasksApi.create).mock.calls[0][0]
    expect(payload.tickers).toEqual(['AAPL', 'MSFT', 'GOOG'])
  })

  it('submits the selected target portfolio', async () => {
    vi.mocked(explorationTasksApi.create).mockResolvedValue(buildCreatedTask())
    const { user } = renderForm()

    await user.type(
      screen.getByTestId('exploration-task-create-prompt-input'),
      'Explore.'
    )

    // Wait for the portfolios option to be rendered.
    await waitFor(() => {
      const select = screen.getByTestId(
        'exploration-task-create-portfolio-select'
      )
      expect(select.querySelector('option[value="portfolio-1"]')).toBeTruthy()
    })

    await user.selectOptions(
      screen.getByTestId('exploration-task-create-portfolio-select'),
      'portfolio-1'
    )

    await user.click(screen.getByTestId('exploration-task-create-submit-btn'))
    await waitFor(() =>
      expect(explorationTasksApi.create).toHaveBeenCalledTimes(1)
    )
    expect(
      vi.mocked(explorationTasksApi.create).mock.calls[0][0].target_portfolio_id
    ).toBe('portfolio-1')
  })

  it('omits target_portfolio_id when no portfolio is selected', async () => {
    vi.mocked(explorationTasksApi.create).mockResolvedValue(buildCreatedTask())
    const { user } = renderForm()

    await user.type(
      screen.getByTestId('exploration-task-create-prompt-input'),
      'Explore.'
    )
    await user.click(screen.getByTestId('exploration-task-create-submit-btn'))

    await waitFor(() =>
      expect(explorationTasksApi.create).toHaveBeenCalledTimes(1)
    )
    const payload = vi.mocked(explorationTasksApi.create).mock.calls[0][0]
    expect(payload.target_portfolio_id).toBeUndefined()
    expect(payload.tickers).toBeUndefined()
  })

  it('navigates to the detail view on success', async () => {
    vi.mocked(explorationTasksApi.create).mockResolvedValue(buildCreatedTask())
    const { user } = renderForm()

    await user.type(
      screen.getByTestId('exploration-task-create-prompt-input'),
      'Explore.'
    )
    await user.click(screen.getByTestId('exploration-task-create-submit-btn'))

    await waitFor(() =>
      expect(screen.getByTestId('detail-view-stub')).toBeInTheDocument()
    )
  })

  it('calls onCancel when the cancel button is clicked', async () => {
    const { user, onCancel } = renderForm()
    await user.click(screen.getByTestId('exploration-task-create-cancel-btn'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })
})
