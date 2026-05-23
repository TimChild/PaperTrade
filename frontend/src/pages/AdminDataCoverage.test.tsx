/**
 * Component tests for the AdminDataCoverage page (Phase J / Task #212 L4 + Task #215).
 *
 * Coverage:
 *
 * - Renders one row per ticker in the response.
 * - Status pill colour matches `gap_days_count` + `last_refresh` rules.
 * - `backfill_status` overrides the steady-state pill (queued / catching-up /
 *   caught-up / failed).
 * - "Catch up" button click POSTs `{ ticker }` with no date payload.
 * - Catch-up button is disabled while a non-terminal task is active.
 * - Target epoch is surfaced on the page header.
 * - Empty / error states render.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { server } from '../../tests/setup'
import { AdminDataCoverage } from './AdminDataCoverage'
import type {
  BackfillResponse,
  BackfillStatusInfo,
  DataCoverageResponse,
  TickerCoverageEntry,
} from '@/services/api/types'

const API_BASE_URL = 'http://localhost:8000/api/v1'
const DEFAULT_EPOCH = '2015-01-01'

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
    coverage_start: '2015-01-06',
    coverage_end: '2025-01-10',
    last_refresh: new Date().toISOString(),
    gap_days_count: 0,
    target_epoch: DEFAULT_EPOCH,
    is_active: true,
    backfill_status: null,
    ...overrides,
  }
}

function makeBackfillStatus(
  overrides: Partial<BackfillStatusInfo> = {}
): BackfillStatusInfo {
  return {
    task_id: '00000000-0000-0000-0000-00000000abcd',
    status: 'pending',
    enqueued_at: new Date().toISOString(),
    error_message: null,
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

  it('surfaces the target epoch on the header when rows exist', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [makeEntry({ target_epoch: '2020-06-15' })],
        })
      )
    )

    renderPage()

    const caption = await screen.findByTestId(
      'admin-data-coverage-target-epoch'
    )
    expect(caption).toHaveTextContent(/target epoch/i)
    expect(caption).toHaveTextContent('2020-06-15')
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
              target_epoch: DEFAULT_EPOCH,
              is_active: true,
              backfill_status: null,
            },
          ],
        })
      )
    )

    renderPage()

    const statusPill = await screen.findByTestId('coverage-status-TSLA')
    expect(statusPill).toHaveAttribute('data-status', 'no-data')
  })

  it('renders "Queued" pill when backfill_status.status is pending', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({
              ticker: 'AAPL',
              backfill_status: makeBackfillStatus({ status: 'pending' }),
            }),
          ],
        })
      )
    )

    renderPage()

    const statusPill = await screen.findByTestId('coverage-status-AAPL')
    expect(statusPill).toHaveAttribute('data-status', 'queued')
    expect(statusPill).toHaveTextContent(/queued/i)
  })

  it('renders "Catching up…" pill when backfill_status.status is running', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({
              ticker: 'AAPL',
              backfill_status: makeBackfillStatus({ status: 'running' }),
            }),
          ],
        })
      )
    )

    renderPage()

    const statusPill = await screen.findByTestId('coverage-status-AAPL')
    expect(statusPill).toHaveAttribute('data-status', 'catching-up')
    expect(statusPill).toHaveTextContent(/catching up/i)
  })

  it('renders "Caught up" pill when backfill_status.status is succeeded', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({
              ticker: 'AAPL',
              backfill_status: makeBackfillStatus({ status: 'succeeded' }),
            }),
          ],
        })
      )
    )

    renderPage()

    const statusPill = await screen.findByTestId('coverage-status-AAPL')
    expect(statusPill).toHaveAttribute('data-status', 'caught-up')
    expect(statusPill).toHaveTextContent(/caught up/i)
  })

  it('renders "Failed" pill with error message in title attr when backfill failed', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({
              ticker: 'AAPL',
              backfill_status: makeBackfillStatus({
                status: 'failed',
                error_message: 'Rate limit hit',
              }),
            }),
          ],
        })
      )
    )

    renderPage()

    const statusPill = await screen.findByTestId('coverage-status-AAPL')
    expect(statusPill).toHaveAttribute('data-status', 'failed')
    expect(statusPill).toHaveTextContent(/failed/i)
    expect(statusPill).toHaveAttribute('title', 'Rate limit hit')
  })

  it('disables the Catch-up button while a non-terminal task is active', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({
              ticker: 'AAPL',
              backfill_status: makeBackfillStatus({ status: 'running' }),
            }),
          ],
        })
      )
    )

    renderPage()

    const button = await screen.findByTestId('coverage-catch-up-btn-AAPL')
    expect(button).toBeDisabled()
  })

  it('keeps the Catch-up button enabled when no task is active', async () => {
    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [makeEntry({ ticker: 'AAPL', backfill_status: null })],
        })
      )
    )

    renderPage()

    const button = await screen.findByTestId('coverage-catch-up-btn-AAPL')
    expect(button).not.toBeDisabled()
  })

  it('POSTs only the ticker payload when Catch up is clicked', async () => {
    const user = userEvent.setup()
    let receivedBody: unknown = null

    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [makeEntry({ ticker: 'AAPL' })],
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
              start_date: DEFAULT_EPOCH,
              end_date: '2025-01-10',
            },
            { status: 201 }
          )
        }
      )
    )

    renderPage()

    await user.click(await screen.findByTestId('coverage-catch-up-btn-AAPL'))

    await waitFor(() => {
      const body = receivedBody as Record<string, unknown> | null
      expect(body).not.toBeNull()
      expect(body?.ticker).toBe('AAPL')
      // Task #215: no start_date / end_date / priority in the payload.
      expect(body?.start_date).toBeUndefined()
      expect(body?.end_date).toBeUndefined()
      expect(body?.priority).toBeUndefined()
    })
  })

  it('only disables the clicked row while its catch-up mutation is in flight', async () => {
    const user = userEvent.setup()

    server.use(
      http.get(`${API_BASE_URL}/admin/data-coverage`, () =>
        HttpResponse.json<DataCoverageResponse>({
          tickers: [
            makeEntry({ ticker: 'AAPL', backfill_status: null }),
            makeEntry({ ticker: 'TSLA', backfill_status: null }),
          ],
        })
      ),
      // Hold the response open so the mutation stays `isPending`.
      http.post(
        `${API_BASE_URL}/admin/data-coverage/backfill`,
        async () =>
          new Promise<Response>((resolve) => {
            setTimeout(
              () =>
                resolve(
                  HttpResponse.json<BackfillResponse>(
                    {
                      task_id: '00000000-0000-0000-0000-00000000abcd',
                      status: 'pending',
                      existing: false,
                      start_date: DEFAULT_EPOCH,
                      end_date: '2025-01-10',
                    },
                    { status: 201 }
                  )
                ),
              300
            )
          })
      )
    )

    renderPage()

    const aaplBtn = await screen.findByTestId('coverage-catch-up-btn-AAPL')
    const tslaBtn = await screen.findByTestId('coverage-catch-up-btn-TSLA')

    await user.click(aaplBtn)

    // While the AAPL mutation is in flight, the AAPL button is disabled
    // but TSLA's stays enabled (regression test for the shared-isPending
    // bug — Task #215 follow-up).
    await waitFor(() => {
      expect(aaplBtn).toBeDisabled()
    })
    expect(tslaBtn).not.toBeDisabled()
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
