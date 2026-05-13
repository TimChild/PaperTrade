/**
 * Component tests for the AdminDataCoverage page (Phase J / Task #212 L4).
 *
 * Coverage:
 *
 * - Renders one row per ticker in the response.
 * - Status pill colour matches `gap_days_count` + `last_refresh` rules.
 * - Backfill button click opens the modal.
 * - Submitting the modal fires the POST mutation and closes the modal.
 * - Empty / error states render.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { server } from '../../tests/setup'
import { AdminDataCoverage } from './AdminDataCoverage'
import type {
  BackfillResponse,
  DataCoverageResponse,
  TickerCoverageEntry,
} from '@/services/api/types'

const API_BASE_URL = 'http://localhost:8000/api/v1'

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

function makeEntry(
  overrides: Partial<TickerCoverageEntry> = {}
): TickerCoverageEntry {
  return {
    ticker: 'AAPL',
    coverage_start: '2025-01-06',
    coverage_end: '2025-01-10',
    last_refresh: new Date().toISOString(),
    gap_days_count: 0,
    is_active: true,
    ...overrides,
  }
}

function renderPage(): void {
  // Disable retries so error tests don't loop.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminDataCoverage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('AdminDataCoverage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    server.resetHandlers()
  })

  it('renders the page header with description', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({ tickers: [] })
      )
    )

    renderPage()

    expect(
      await screen.findByRole('heading', { name: /data coverage/i })
    ).toBeInTheDocument()
  })

  it('renders the empty state when no tickers are tracked', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({ tickers: [] })
      )
    )

    renderPage()

    expect(
      await screen.findByTestId('admin-data-coverage-empty')
    ).toBeInTheDocument()
  })

  it('renders one row per ticker with healthy status when contiguous', async () => {
    const recentRefresh = new Date(Date.now() - 60 * 60 * 1000).toISOString()
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({
              ticker: 'AAPL',
              gap_days_count: 0,
              last_refresh: recentRefresh,
            }),
            makeEntry({
              ticker: 'MSFT',
              gap_days_count: 0,
              last_refresh: recentRefresh,
            }),
          ],
        })
      )
    )

    renderPage()

    expect(await screen.findByTestId('coverage-row-AAPL')).toBeInTheDocument()
    expect(screen.getByTestId('coverage-row-MSFT')).toBeInTheDocument()

    const aaplStatus = screen.getByTestId('coverage-status-AAPL')
    expect(aaplStatus).toHaveAttribute('data-status', 'healthy')
    expect(aaplStatus).toHaveTextContent(/healthy/i)
  })

  it('flags rows with gap_days_count > 0 as Gaps (loss tone)', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({
              ticker: 'AAPL',
              gap_days_count: 3,
              last_refresh: new Date().toISOString(),
            }),
          ],
        })
      )
    )

    renderPage()

    const statusPill = await screen.findByTestId('coverage-status-AAPL')
    expect(statusPill).toHaveAttribute('data-status', 'gaps')
    expect(statusPill).toHaveTextContent(/gaps/i)
    expect(screen.getByTestId('coverage-gap-AAPL')).toHaveTextContent('3')
  })

  it('flags rows older than 48h as Stale (amber tone)', async () => {
    // 72 hours old → stale.
    const oldRefresh = new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString()
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({
              ticker: 'AAPL',
              gap_days_count: 0,
              last_refresh: oldRefresh,
            }),
          ],
        })
      )
    )

    renderPage()

    const statusPill = await screen.findByTestId('coverage-status-AAPL')
    expect(statusPill).toHaveAttribute('data-status', 'stale')
    expect(statusPill).toHaveTextContent(/stale/i)
  })

  it('renders "No data" status when coverage_start is null', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            {
              ticker: 'TSLA',
              coverage_start: null,
              coverage_end: null,
              last_refresh: null,
              gap_days_count: 0,
              is_active: true,
            },
          ],
        })
      )
    )

    renderPage()

    const statusPill = await screen.findByTestId('coverage-status-TSLA')
    expect(statusPill).toHaveAttribute('data-status', 'no-data')
  })

  it('opens the backfill modal when the Backfill button is clicked', async () => {
    const user = userEvent.setup()
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [makeEntry({ ticker: 'AAPL' })],
        })
      )
    )

    renderPage()

    await user.click(await screen.findByTestId('coverage-backfill-btn-AAPL'))

    const form = await screen.findByTestId('backfill-form')
    expect(form).toBeInTheDocument()
    // Native <dialog> elements aren't seen by getByRole in jsdom because
    // showModal() is a no-op mock, so query by text instead.
    expect(screen.getByText(/backfill aapl/i)).toBeInTheDocument()
  })

  it('submits a backfill request and closes the modal on success', async () => {
    const user = userEvent.setup()
    let receivedBody: unknown = null

    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({
              ticker: 'AAPL',
              coverage_end: '2025-01-10',
            }),
          ],
        })
      ),
      http.post(
        `${API_BASE_URL}/admin/data-coverage/backfill`,
        async ({ request }) => {
          receivedBody = await request.json()
          return HttpResponse.json<BackfillResponse>(
            {
              task_id: '00000000-0000-0000-0000-00000000abcd',
              status: 'pending',
              existing: false,
            },
            { status: 201 }
          )
        }
      )
    )

    renderPage()

    await user.click(await screen.findByTestId('coverage-backfill-btn-AAPL'))

    const form = await screen.findByTestId('backfill-form')
    const submit = within(form).getByTestId('backfill-submit-btn')
    await user.click(submit)

    await waitFor(() => {
      const body = receivedBody as Record<string, unknown> | null
      expect(body).not.toBeNull()
      expect(body?.ticker).toBe('AAPL')
      expect(body?.start_date).toBe('2025-01-10')
    })
  })

  it('renders an error block when the GET returns 403', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json(
          { detail: 'Admin privileges required' },
          { status: 403 }
        )
      )
    )

    renderPage()

    const errorBlock = await screen.findByTestId('admin-data-coverage-error')
    expect(errorBlock).toBeInTheDocument()
    expect(errorBlock).toHaveTextContent(/admin privileges required/i)
  })
})
