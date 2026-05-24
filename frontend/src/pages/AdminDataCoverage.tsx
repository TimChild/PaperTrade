/**
 * Admin data-coverage page (Phase J / Task #212 Layer 4 + Task #215 + Task #220).
 *
 * Operator view of per-ticker price-history coverage.
 *
 * Task #215 rework: no date-range picker. The operator presses a single
 * "Catch up" button per ticker; the backend fills `[ZEBU_HISTORY_EPOCH,
 * today]` and the page surfaces real `BackfillTask` state (pending /
 * running / succeeded / failed) so the operator sees progress on the
 * next 30 s poll.
 *
 * Task #220 add: a "Pin" column + Pin / Unpin action button alongside
 * Catch up. Pin/Unpin edits `ticker_watchlist` so the operator can
 * keep a ticker in the scheduler's refresh set after the 30-day trade
 * window lapses. Pin is additive — it doesn't trigger a backfill and
 * doesn't change scheduler semantics.
 *
 * Surface goals:
 *
 * - "Healthy" tickers — coverage current and contiguous — fade so the
 *   operator's eye lands on what's broken.
 * - "Stale" tickers — last_refresh > 48 h — and "Gaps" tickers —
 *   gap_days_count > 0 — pop with the editorial amber and loss tones.
 * - Active backfill tasks for a ticker show a "Queued" / "Catching up…"
 *   / "Caught up" / "Failed" pill driven by the backend's
 *   `backfill_status`. The Catch-up button disables while the task is
 *   non-terminal.
 * - Watchlisted (pinned) tickers show a small "Pinned" pill in the new
 *   Pin column; the operator can click Unpin to remove them.
 *
 * The Catch-up button is idempotent server-side — if the operator
 * clicks it twice we get the existing task back. Pin is similarly
 * idempotent; Unpin returns 404 if the ticker isn't pinned (surfaced
 * as a "not pinned" toast).
 */
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
import { EmptyState } from '@/components/ui/EmptyState'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import {
  DATA_COVERAGE_POLL_INTERVAL_MS,
  useBackfillTicker,
  useDataCoverage,
  usePinTicker,
  useUnpinTicker,
} from '@/hooks/useDataCoverage'
import type {
  BackfillTaskStatus,
  TickerCoverageEntry,
} from '@/services/api/types'
import { formatRelativeTime } from '@/utils/formatters'

/** Threshold (ms) above which a ticker's last_refresh is considered "Stale". */
const STALE_THRESHOLD_MS = 48 * 60 * 60 * 1000

/**
 * Status pill discriminator. Backfill states take precedence over the
 * derived coverage state (healthy/stale/gaps/no-data) so the operator
 * always sees the most-current signal.
 */
type CoverageStatus =
  | 'healthy'
  | 'stale'
  | 'gaps'
  | 'no-data'
  | 'queued'
  | 'catching-up'
  | 'caught-up'
  | 'failed'

interface CoverageStatusInfo {
  status: CoverageStatus
  label: string
  /** Used as a hover-tooltip when the backfill failed. */
  detail?: string
}

const STATUS_PILL_CLASSES: Record<CoverageStatus, string> = {
  healthy:
    'inline-flex items-center bg-canvas-raised/60 text-ink-muted px-2 py-1 rounded-editorial font-eyebrow',
  stale:
    'inline-flex items-center bg-amber-soft text-amber px-2 py-1 rounded-editorial font-eyebrow',
  gaps: 'inline-flex items-center bg-loss-soft text-loss px-2 py-1 rounded-editorial font-eyebrow',
  'no-data':
    'inline-flex items-center bg-canvas-sunken text-ink-subtle px-2 py-1 rounded-editorial font-eyebrow',
  queued:
    'inline-flex items-center bg-amber-soft/70 text-amber px-2 py-1 rounded-editorial font-eyebrow',
  'catching-up':
    'inline-flex items-center bg-amber-soft text-amber px-2 py-1 rounded-editorial font-eyebrow animate-pulse',
  'caught-up':
    'inline-flex items-center bg-gain-soft text-gain px-2 py-1 rounded-editorial font-eyebrow',
  failed:
    'inline-flex items-center bg-loss-soft text-loss px-2 py-1 rounded-editorial font-eyebrow',
}

function backfillStatusToCoverageStatus(
  status: BackfillTaskStatus,
  errorMessage: string | null
): CoverageStatusInfo {
  switch (status) {
    case 'pending':
      return { status: 'queued', label: 'Queued' }
    case 'running':
      return { status: 'catching-up', label: 'Catching up…' }
    case 'succeeded':
      return { status: 'caught-up', label: 'Caught up' }
    case 'failed':
      return {
        status: 'failed',
        label: 'Failed',
        detail: errorMessage ?? undefined,
      }
  }
}

function computeStatus(
  entry: TickerCoverageEntry,
  now: Date
): CoverageStatusInfo {
  // Backfill task state takes priority — if there's an active or recent
  // task, surface that instead of the steady-state pill.
  if (entry.backfill_status !== null) {
    return backfillStatusToCoverageStatus(
      entry.backfill_status.status,
      entry.backfill_status.error_message
    )
  }
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

function isBackfillInFlight(entry: TickerCoverageEntry): boolean {
  return (
    entry.backfill_status !== null &&
    (entry.backfill_status.status === 'pending' ||
      entry.backfill_status.status === 'running')
  )
}

export function AdminDataCoverage(): React.JSX.Element {
  const { data, isLoading, error } = useDataCoverage()
  const backfill = useBackfillTicker()
  const pin = usePinTicker()
  const unpin = useUnpinTicker()
  const now = new Date()

  const rows = data?.tickers ?? []
  // Every row carries the same target_epoch — read it from the first row
  // for the header, fall back to a placeholder when the table is empty.
  const targetEpoch = rows.length > 0 ? rows[0].target_epoch : null

  const handleCatchUp = (entry: TickerCoverageEntry): void => {
    backfill.mutate(
      { ticker: entry.ticker },
      {
        onSuccess: (response) => {
          if (response.existing) {
            toast.success(
              `Catch-up already in progress for ${entry.ticker} — using existing task.`
            )
          } else {
            toast.success(
              `Catching ${entry.ticker} up to ${response.end_date}.`
            )
          }
        },
        onError: (err: Error) => {
          if (isAxiosError(err) && err.response?.status === 403) {
            toast.error('Admin privileges required.')
            return
          }
          const message =
            isAxiosError(err) && err.response?.data?.detail
              ? String(err.response.data.detail)
              : 'Failed to enqueue catch-up.'
          toast.error(message)
        },
      }
    )
  }

  const handlePin = (entry: TickerCoverageEntry): void => {
    pin.mutate(
      { ticker: entry.ticker },
      {
        onSuccess: () => {
          toast.success(`Pinned ${entry.ticker} to the watchlist.`)
        },
        onError: (err: Error) => {
          if (isAxiosError(err) && err.response?.status === 403) {
            toast.error('Admin privileges required.')
            return
          }
          const message =
            isAxiosError(err) && err.response?.data?.detail
              ? String(err.response.data.detail)
              : `Failed to pin ${entry.ticker}.`
          toast.error(message)
        },
      }
    )
  }

  const handleUnpin = (entry: TickerCoverageEntry): void => {
    unpin.mutate(entry.ticker, {
      onSuccess: () => {
        toast.success(`Unpinned ${entry.ticker} from the watchlist.`)
      },
      onError: (err: Error) => {
        if (isAxiosError(err) && err.response?.status === 403) {
          toast.error('Admin privileges required.')
          return
        }
        if (isAxiosError(err) && err.response?.status === 404) {
          toast.error(`${entry.ticker} is not pinned.`)
          return
        }
        const message =
          isAxiosError(err) && err.response?.data?.detail
            ? String(err.response.data.detail)
            : `Failed to unpin ${entry.ticker}.`
        toast.error(message)
      },
    })
  }

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
        {targetEpoch !== null && (
          <Caption
            className="mt-1 block text-ink-subtle"
            data-testid="admin-data-coverage-target-epoch"
          >
            Target epoch: <span className="font-tabular">{targetEpoch}</span>
          </Caption>
        )}
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
            <DataHeaderCell>Pin</DataHeaderCell>
            <DataHeaderCell align="right">Action</DataHeaderCell>
          </DataTableHead>
          <DataTableBody>
            {rows.map((row) => {
              const status = computeStatus(row, now)
              const inFlight = isBackfillInFlight(row)
              const isPinMutating =
                (pin.isPending && pin.variables?.ticker === row.ticker) ||
                (unpin.isPending && unpin.variables === row.ticker)
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
                      title={status.detail}
                    >
                      {status.label}
                    </span>
                  </DataCell>
                  <DataCell>
                    {row.is_watchlisted ? (
                      <span
                        className="inline-flex items-center bg-canvas-raised/60 text-ink px-2 py-1 rounded-editorial font-eyebrow"
                        data-testid={`coverage-pinned-indicator-${row.ticker}`}
                      >
                        Pinned
                      </span>
                    ) : (
                      <span
                        className="text-ink-subtle"
                        data-testid={`coverage-unpinned-indicator-${row.ticker}`}
                      >
                        —
                      </span>
                    )}
                  </DataCell>
                  <DataCell align="right">
                    <div className="flex items-center justify-end gap-2">
                      {row.is_watchlisted ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleUnpin(row)}
                          disabled={isPinMutating}
                          data-testid={`coverage-unpin-btn-${row.ticker}`}
                        >
                          Unpin
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handlePin(row)}
                          disabled={isPinMutating}
                          data-testid={`coverage-pin-btn-${row.ticker}`}
                        >
                          Pin
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleCatchUp(row)}
                        disabled={
                          inFlight ||
                          (backfill.isPending &&
                            backfill.variables?.ticker === row.ticker)
                        }
                        data-testid={`coverage-catch-up-btn-${row.ticker}`}
                      >
                        {inFlight ? 'Catching up…' : 'Catch up'}
                      </Button>
                    </div>
                  </DataCell>
                </DataRow>
              )
            })}
          </DataTableBody>
        </DataTable>
      )}
    </div>
  )
}
