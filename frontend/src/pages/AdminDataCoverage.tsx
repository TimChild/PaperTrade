/**
 * Admin data-coverage page (Phase J / Task #212 Layer 4).
 *
 * Operator view of per-ticker price-history coverage. Surface goals:
 *
 * - "Healthy" tickers — coverage is current and contiguous — should
 *   visually fade so the operator's eye lands on what's broken.
 * - "Stale" tickers — last_refresh > 48h — and "Gaps" tickers —
 *   gap_days_count > 0 — pop with the editorial amber and loss tones.
 * - One-click backfill action per row opens a date-range modal; the
 *   modal POSTs and the underlying query re-fetches via mutation
 *   invalidation. Pollwise the query refetches every 30 seconds.
 *
 * Status pill rules (per §"Layer 4 — UI"):
 *
 * - `gap_days_count > 0`              → Gaps (loss)
 * - else if last_refresh older than 48h → Stale (amber)
 * - else                                → Healthy (subtle)
 *
 * The operator can backfill any ticker, including healthy ones (no
 * client-side gating) — the backend de-dupes on (ticker, start, end).
 */
import { useState } from 'react'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { Caption } from '@/components/ui/Caption'
import {
  DataCell,
  DataHeaderCell,
  DataRow,
  DataTable,
  DataTableBody,
  DataTableHead,
} from '@/components/ui/DataRow'
import { Dialog } from '@/components/ui/Dialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import {
  DATA_COVERAGE_POLL_INTERVAL_MS,
  useBackfillTicker,
  useDataCoverage,
} from '@/hooks/useDataCoverage'
import type { TickerCoverageEntry } from '@/services/api/types'
import { formatRelativeTime } from '@/utils/formatters'

/** Threshold (ms) above which a ticker's last_refresh is considered "Stale". */
const STALE_THRESHOLD_MS = 48 * 60 * 60 * 1000

/** Status pill discriminator. Computed in one place so the table + pill agree. */
type CoverageStatus = 'healthy' | 'stale' | 'gaps' | 'no-data'

interface CoverageStatusInfo {
  status: CoverageStatus
  label: string
}

function computeStatus(
  entry: TickerCoverageEntry,
  now: Date
): CoverageStatusInfo {
  if (entry.coverage_start === null || entry.last_refresh === null) {
    return { status: 'no-data', label: 'No data' }
  }
  if (entry.gap_days_count > 0) {
    return { status: 'gaps', label: 'Gaps' }
  }
  const lastRefreshMs = new Date(entry.last_refresh).getTime()
  if (now.getTime() - lastRefreshMs > STALE_THRESHOLD_MS) {
    return { status: 'stale', label: 'Stale' }
  }
  return { status: 'healthy', label: 'Healthy' }
}

const STATUS_PILL_CLASSES: Record<CoverageStatus, string> = {
  healthy:
    'inline-flex items-center bg-canvas-raised/60 text-ink-muted px-2 py-1 rounded-editorial font-eyebrow',
  stale:
    'inline-flex items-center bg-amber-soft text-amber px-2 py-1 rounded-editorial font-eyebrow',
  gaps: 'inline-flex items-center bg-loss-soft text-loss px-2 py-1 rounded-editorial font-eyebrow',
  'no-data':
    'inline-flex items-center bg-canvas-sunken text-ink-subtle px-2 py-1 rounded-editorial font-eyebrow',
}

export function AdminDataCoverage(): React.JSX.Element {
  const { data, isLoading, error } = useDataCoverage()
  const [activeTicker, setActiveTicker] = useState<TickerCoverageEntry | null>(
    null
  )
  const now = new Date()

  const rows = data?.tickers ?? []

  return (
    <div data-testid="admin-data-coverage-page">
      <header className="mb-6">
        <Eyebrow>Admin · Operations</Eyebrow>
        <h1 className="mt-1.5 font-display text-display-md tracking-tight text-ink">
          Data coverage
        </h1>
        <Caption className="mt-2 block text-ink-muted">
          Per-ticker price-history coverage. Refreshes every{' '}
          {Math.round(DATA_COVERAGE_POLL_INTERVAL_MS / 1000)} seconds while this
          page is open.
        </Caption>
      </header>

      {isLoading && !data && (
        <div data-testid="admin-data-coverage-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {error && !data && (
        <div
          data-testid="admin-data-coverage-error"
          className="rounded-editorial border border-hairline bg-loss-soft/40 p-6"
        >
          <Eyebrow tone="accent">Error</Eyebrow>
          <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
            {isAxiosError(error) && error.response?.status === 403
              ? 'Admin privileges required'
              : 'Failed to load coverage data'}
          </h2>
          <p className="mt-2 text-body-sm text-ink-muted">
            {isAxiosError(error) && error.response?.status === 403
              ? 'This page is admin-only. Contact an administrator if you believe this is an error.'
              : 'Try refreshing the page. If the problem persists the backend may be unreachable.'}
          </p>
        </div>
      )}

      {data && rows.length === 0 && (
        <div data-testid="admin-data-coverage-empty">
          <EmptyState
            eyebrow="No tickers tracked"
            title="No coverage data yet"
            description="Add tickers to the watchlist or execute a trade to begin populating coverage."
          />
        </div>
      )}

      {data && rows.length > 0 && (
        <DataTable testId="admin-data-coverage-table">
          <DataTableHead>
            <DataHeaderCell>Ticker</DataHeaderCell>
            <DataHeaderCell hideOnMobile>Coverage range</DataHeaderCell>
            <DataHeaderCell>Last refresh</DataHeaderCell>
            <DataHeaderCell align="right" hideOnMobile>
              Gap days
            </DataHeaderCell>
            <DataHeaderCell>Status</DataHeaderCell>
            <DataHeaderCell align="right">Action</DataHeaderCell>
          </DataTableHead>
          <DataTableBody>
            {rows.map((row) => {
              const status = computeStatus(row, now)
              return (
                <DataRow key={row.ticker} testId={`coverage-row-${row.ticker}`}>
                  <DataCell
                    emphasis="primary"
                    testId={`coverage-ticker-${row.ticker}`}
                  >
                    <span className="font-tabular">{row.ticker}</span>
                  </DataCell>
                  <DataCell tone="muted" hideOnMobile>
                    {row.coverage_start && row.coverage_end ? (
                      <span className="font-tabular text-body-sm">
                        {row.coverage_start} → {row.coverage_end}
                      </span>
                    ) : (
                      <span className="text-ink-subtle">—</span>
                    )}
                  </DataCell>
                  <DataCell tone="muted">
                    {row.last_refresh ? (
                      <span
                        title={row.last_refresh}
                        data-testid={`coverage-last-refresh-${row.ticker}`}
                      >
                        {formatRelativeTime(row.last_refresh, now)}
                      </span>
                    ) : (
                      <span className="text-ink-subtle">—</span>
                    )}
                  </DataCell>
                  <DataCell numeric align="right" hideOnMobile>
                    <span
                      data-testid={`coverage-gap-${row.ticker}`}
                      className={
                        row.gap_days_count > 0 ? 'text-loss' : 'text-ink'
                      }
                    >
                      {row.gap_days_count}
                    </span>
                  </DataCell>
                  <DataCell>
                    <span
                      className={STATUS_PILL_CLASSES[status.status]}
                      data-testid={`coverage-status-${row.ticker}`}
                      data-status={status.status}
                    >
                      {status.label}
                    </span>
                  </DataCell>
                  <DataCell align="right">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setActiveTicker(row)}
                      data-testid={`coverage-backfill-btn-${row.ticker}`}
                    >
                      Backfill
                    </Button>
                  </DataCell>
                </DataRow>
              )
            })}
          </DataTableBody>
        </DataTable>
      )}

      <BackfillDialog
        entry={activeTicker}
        onClose={() => setActiveTicker(null)}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Backfill dialog
// ---------------------------------------------------------------------------

interface BackfillDialogProps {
  entry: TickerCoverageEntry | null
  onClose: () => void
}

/**
 * Determine the date-input defaults for the backfill modal.
 *
 * - Tickers with existing coverage: prefill `[coverage_end, today]` so
 *   the operator is targeting "catch up to today" by default.
 * - Tickers with no coverage: prefill the trailing 30-day window.
 */
function defaultRangeFor(entry: TickerCoverageEntry): {
  start: string
  end: string
} {
  const today = new Date().toISOString().slice(0, 10)
  if (entry.coverage_end) {
    return { start: entry.coverage_end, end: today }
  }
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10)
  return { start: thirtyDaysAgo, end: today }
}

function BackfillDialog({
  entry,
  onClose,
}: BackfillDialogProps): React.JSX.Element {
  // The dialog stays mounted while closed (`Dialog` requires it for native
  // close + focus-trap mechanics); render an empty form when entry is null
  // to keep the hook tree stable.
  const fallbackKey = 'no-ticker'
  const dialogKey = entry?.ticker ?? fallbackKey

  return (
    <Dialog
      isOpen={entry !== null}
      onClose={onClose}
      eyebrow="Backfill"
      title={entry ? `Backfill ${entry.ticker}` : ''}
      className="w-full max-w-md"
    >
      {entry && (
        <BackfillForm
          key={dialogKey /* remount on ticker change → fresh defaults */}
          entry={entry}
          onClose={onClose}
        />
      )}
    </Dialog>
  )
}

interface BackfillFormProps {
  entry: TickerCoverageEntry
  onClose: () => void
}

function BackfillForm({
  entry,
  onClose,
}: BackfillFormProps): React.JSX.Element {
  const defaults = defaultRangeFor(entry)
  const [startDate, setStartDate] = useState<string>(defaults.start)
  const [endDate, setEndDate] = useState<string>(defaults.end)
  const backfill = useBackfillTicker()

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    if (!startDate || !endDate) {
      toast.error('Both start and end dates are required.')
      return
    }
    if (endDate < startDate) {
      toast.error('End date must be on or after the start date.')
      return
    }
    backfill.mutate(
      {
        ticker: entry.ticker,
        start_date: startDate,
        end_date: endDate,
      },
      {
        onSuccess: (response) => {
          if (response.existing) {
            toast.success(
              `Backfill already queued for ${entry.ticker} — using existing task.`
            )
          } else {
            toast.success(`Backfill queued for ${entry.ticker}.`)
          }
          onClose()
        },
        onError: (err: Error) => {
          if (isAxiosError(err) && err.response?.status === 403) {
            toast.error('Admin privileges required.')
            return
          }
          const message =
            isAxiosError(err) && err.response?.data?.detail
              ? String(err.response.data.detail)
              : 'Failed to queue backfill.'
          toast.error(message)
        },
      }
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="backfill-form"
      className="space-y-5"
    >
      <p className="text-body-sm text-ink-muted">
        Operator-driven backfill takes priority over scheduled refreshes.
        Idempotent — if a task is already running for this range nothing new is
        enqueued.
      </p>
      <div className="grid grid-cols-2 gap-4">
        <label className="block">
          <span className="block font-eyebrow text-ink-muted mb-1.5">
            Start date
          </span>
          <Input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            data-testid="backfill-start-date"
            required
          />
        </label>
        <label className="block">
          <span className="block font-eyebrow text-ink-muted mb-1.5">
            End date
          </span>
          <Input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            data-testid="backfill-end-date"
            required
          />
        </label>
      </div>
      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          onClick={onClose}
          data-testid="backfill-cancel-btn"
        >
          Cancel
        </Button>
        <Button
          type="submit"
          variant="default"
          disabled={backfill.isPending}
          data-testid="backfill-submit-btn"
        >
          {backfill.isPending ? 'Queueing…' : 'Queue backfill'}
        </Button>
      </div>
    </form>
  )
}
