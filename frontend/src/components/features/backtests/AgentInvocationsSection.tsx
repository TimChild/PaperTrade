/**
 * AgentInvocationsSection — per-run audit log of simulated agent decisions.
 *
 * Phase L-4 (Task #220). Rendered on the backtest result page below the
 * performance chart, but only when the parent run's
 * `agent_invocation_mode` is not `"none"`.
 *
 * Visual parity: matches `TriggerFireLog` table conventions —
 * editorial palette, font-eyebrow column heads, hairline DataTable.
 * The decision-pill component is reused (`AgentDecisionBadge`) so the
 * symbology is identical between live trigger fires and simulated
 * backtest fires.
 *
 * Empty state: rendered when the API returns `items.length === 0`.
 * That happens in three real cases:
 *   - MOCK-mode run with no triggers attached to the strategy.
 *   - LIVE-mode run where no triggers fired in the simulated window.
 *   - NONE-mode runs never reach here — the parent page short-circuits.
 *
 * Pagination — offset-based accumulation. Each "Load more" press
 * advances `offset` by `PAGE_SIZE`; the hook fetches one page at a
 * time with a fixed `limit = PAGE_SIZE`. We concatenate pages in
 * component state so the table grows monotonically. Growing the
 * server-side `limit` directly would breach the backend's
 * `MAX_PAGE_LIMIT = 100` cap after two clicks and surface as 422.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataRow,
  DataCell,
  DataHeaderCell,
} from '@/components/ui/DataRow'
import { AgentDecisionBadge } from '@/components/features/triggers/AgentDecisionBadge'
import { useBacktestAgentInvocations } from '@/hooks/useBacktests'
import { formatSimulatedDate } from '@/utils/formatters'
import type {
  BacktestAgentInvocationMode,
  BacktestAgentInvocationResponse,
} from '@/services/api/types'

const PAGE_SIZE = 50
const RATIONALE_PREVIEW_CHARS = 200

interface AgentInvocationsSectionProps {
  backtestId: string
  agentInvocationMode: BacktestAgentInvocationMode
}

export function AgentInvocationsSection({
  backtestId,
  agentInvocationMode,
}: AgentInvocationsSectionProps): React.JSX.Element | null {
  // Offset-based pagination — limit is fixed at PAGE_SIZE per request
  // so we never breach the backend's MAX_PAGE_LIMIT=100 cap. Each
  // "Load more" press advances offset by PAGE_SIZE. We keep the
  // *previous* pages in `previousPages` so they remain visible while
  // the next page fetches. The current page is read directly from
  // `data?.items` to avoid an extra render where rows disappear.
  const [offset, setOffset] = useState(0)
  const [previousPages, setPreviousPages] = useState<
    BacktestAgentInvocationResponse[]
  >([])

  // The result page already gates this section on
  // `agentInvocationMode !== 'none'`, but the prop is plumbed through
  // anyway so the component is self-contained in tests.
  const enabled = agentInvocationMode !== 'none'

  const { data, isLoading, error } = useBacktestAgentInvocations(
    backtestId,
    { limit: PAGE_SIZE, offset },
    { enabled }
  )

  // NB: when the parent backtest id changes the React Router route
  // remounts this component (each backtest result lives at a
  // distinct path), so we don't need a `useEffect` here to reset
  // `offset` / `previousPages`. If a future single-page navigation
  // changes that contract, give this component a `key={backtestId}`
  // from the parent so the natural remount continues to reset state
  // — DO NOT add a `useEffect(... [backtestId])` to sync props to
  // state (see `.claude/agents/frontend-swe.md`).

  if (!enabled) {
    // Defensive — the parent page should never render us in NONE mode.
    return null
  }

  // Stitch: prior pages + the freshly-fetched current page, deduped
  // by id so a TanStack refetch / strict-mode double-invoke can't
  // double-render any row.
  const currentPage = data?.items ?? []
  const seenIds = new Set(previousPages.map((row) => row.id))
  const items = [
    ...previousPages,
    ...currentPage.filter((row) => !seenIds.has(row.id)),
  ]
  const total = data?.total ?? items.length
  const hasMore = data?.has_more ?? false
  // Show the initial loading state only on the FIRST page fetch.
  // Subsequent Load-more fetches keep the existing table rendered;
  // we surface their pending state via the button's `disabled` and
  // copy below instead.
  const showInitialLoading = isLoading && items.length === 0
  const loadingMore = isLoading && items.length > 0

  const handleLoadMore = (): void => {
    // Move the current page into `previousPages` and bump offset so
    // the next fetch returns the page after.
    setPreviousPages((prev) => {
      const seen = new Set(prev.map((row) => row.id))
      return [...prev, ...currentPage.filter((row) => !seen.has(row.id))]
    })
    setOffset((current) => current + PAGE_SIZE)
  }

  return (
    <section
      className="mt-12 sm:mt-16 reveal"
      style={{ ['--reveal-delay' as string]: '300ms' }}
      data-testid="agent-invocations-section"
    >
      <SectionHeader
        eyebrow="Agent decisions"
        title="Agent invocations"
        size="sm"
        description={
          agentInvocationMode === 'mock'
            ? 'Trigger fires recorded during the simulated run. Mock mode returns HOLD on every fire — useful for previewing what live mode would have done.'
            : 'Real Anthropic decisions recorded during the simulated run. Each row carries the agent rationale and whether the decision was applied to the simulated trade book.'
        }
      />

      {showInitialLoading && (
        <div data-testid="agent-invocations-loading" className="mt-6 py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {error && !showInitialLoading && items.length === 0 && (
        <div
          data-testid="agent-invocations-error"
          className="mt-6 rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-center"
        >
          <p className="text-body-md text-ink">
            Failed to load agent invocations. Please try again.
          </p>
        </div>
      )}

      {!showInitialLoading && !error && items.length === 0 && (
        <div className="mt-6" data-testid="agent-invocations-empty">
          <EmptyState
            eyebrow="No invocations"
            title="No triggers fired during this run"
            description={
              agentInvocationMode === 'mock'
                ? 'No triggers attached to this strategy were evaluable during the simulated window, or none of them met their condition. Mock mode would have invoked the agent on every fire — none happened.'
                : 'No triggers attached to this strategy were evaluable during the simulated window, or none of them met their condition. No Anthropic calls were made.'
            }
          />
        </div>
      )}

      {items.length > 0 && (
        <div className="mt-5">
          <p
            className="font-tabular text-body-sm text-ink-muted mb-3"
            data-testid="agent-invocations-count"
          >
            {total} {total === 1 ? 'invocation' : 'invocations'}
          </p>
          <DataTable testId="agent-invocations-table">
            <DataTableHead>
              <DataHeaderCell>Simulated date</DataHeaderCell>
              <DataHeaderCell>Trigger</DataHeaderCell>
              <DataHeaderCell>Decision</DataHeaderCell>
              <DataHeaderCell hideUntilMd>Rationale</DataHeaderCell>
              <DataHeaderCell hideOnMobile>Executed</DataHeaderCell>
              <DataHeaderCell align="right" hideOnMobile>
                Latency
              </DataHeaderCell>
            </DataTableHead>
            <DataTableBody>
              {items.map((invocation) => (
                <InvocationRow key={invocation.id} invocation={invocation} />
              ))}
            </DataTableBody>
          </DataTable>

          {/* Load-more advances `offset` by PAGE_SIZE — limit stays
              fixed at PAGE_SIZE so the server-side `ge=1, le=100`
              bounds never trip. */}
          {hasMore && (
            <div className="mt-4 flex justify-center">
              <Button
                type="button"
                variant="secondary"
                data-testid="agent-invocations-load-more"
                onClick={handleLoadMore}
                disabled={loadingMore}
              >
                {loadingMore ? 'Loading…' : 'Load more'}
              </Button>
            </div>
          )}

          {/* If a Load-more page fetch failed, show the error block
              alongside the existing accumulated rows so the operator
              can see what they already have plus a clear retry signal. */}
          {error && !showInitialLoading && (
            <div
              data-testid="agent-invocations-error"
              className="mt-4 rounded-editorial border border-hairline bg-loss-soft/40 p-4 text-center"
            >
              <p className="text-body-sm text-ink">
                Failed to load more invocations. Please try again.
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

interface InvocationRowProps {
  invocation: BacktestAgentInvocationResponse
}

/**
 * Truncate by Unicode code points, not UTF-16 code units. A raw
 * `str.slice(0, N)` may split a surrogate pair (emoji, non-BMP char)
 * and produce a U+FFFD replacement character at the boundary. Agent
 * rationale rarely contains emoji today, but trading the cheap spread
 * for the bug-free version is worth it.
 */
function truncateByCodePoints(value: string, maxCodePoints: number): string {
  // Spread iterates over code points (handles surrogates correctly).
  const codePoints = [...value]
  if (codePoints.length <= maxCodePoints) {
    return value
  }
  return codePoints.slice(0, maxCodePoints).join('') + '…'
}

function InvocationRow({ invocation }: InvocationRowProps): React.JSX.Element {
  const [expanded, setExpanded] = useState(false)
  // Comparing code-point count matches what `truncateByCodePoints`
  // returns; using `.length` (code units) would over-show the toggle
  // for strings whose UTF-16 length exceeds N while their code-point
  // count is within N (rare but possible with non-BMP chars).
  const rationaleCodePoints = [...invocation.rationale].length
  const showExpandToggle = rationaleCodePoints > RATIONALE_PREVIEW_CHARS
  const visibleRationale =
    expanded || !showExpandToggle
      ? invocation.rationale
      : truncateByCodePoints(invocation.rationale, RATIONALE_PREVIEW_CHARS)

  return (
    <DataRow testId={`agent-invocation-row-${invocation.id}`}>
      {/* Simulated date — the in-simulation calendar day. Use the
          timezone-safe formatter so the rendered day matches the
          YYYY-MM-DD wire value in every viewer timezone (a raw
          `new Date('YYYY-MM-DD')` would shift in non-UTC zones). */}
      <DataCell tone="muted" emphasis="primary">
        <span
          className="font-tabular"
          data-testid={`agent-invocation-sim-date-${invocation.id}`}
        >
          {formatSimulatedDate(invocation.simulated_date, 'short')}
        </span>
      </DataCell>

      {/* Trigger label. Null `trigger_id` reflects the SET-NULL FK —
          the parent trigger was deleted after the backtest ran. */}
      <DataCell>
        {invocation.trigger_id !== null ? (
          <Link
            to={`/triggers/${invocation.trigger_id}/fires`}
            className="font-tabular text-body-sm text-amber underline-offset-4 hover:underline"
            data-testid={`agent-invocation-trigger-link-${invocation.id}`}
          >
            {invocation.trigger_id.slice(0, 8)}
          </Link>
        ) : (
          <span
            className="font-eyebrow text-ink-subtle italic"
            data-testid={`agent-invocation-trigger-deleted-${invocation.id}`}
            title="The originating trigger was deleted after the backtest ran."
          >
            trigger deleted
          </span>
        )}
      </DataCell>

      {/* Decision pill — reuses AgentDecisionBadge for symbol parity
          with the live trigger fire log. NULL only for MOCK-mode rows
          where the adapter chose not to write a synthetic decision. */}
      <DataCell>
        {invocation.agent_decision !== null ? (
          <AgentDecisionBadge decision={invocation.agent_decision} />
        ) : (
          <span
            className="font-eyebrow text-ink-subtle"
            data-testid={`agent-invocation-decision-none-${invocation.id}`}
          >
            —
          </span>
        )}
      </DataCell>

      {/* Rationale — truncated to ~200 chars by default with an
          inline "Show more" toggle. Empty for MOCK rows and for LIVE
          rows whose decision is INVOCATION_FAILED (entity invariant). */}
      <DataCell tone="muted" hideUntilMd className="max-w-[26rem]">
        {invocation.rationale ? (
          <div className="space-y-1.5">
            <p
              className="text-body-sm leading-relaxed whitespace-pre-wrap"
              data-testid={`agent-invocation-rationale-${invocation.id}`}
            >
              {visibleRationale}
            </p>
            {showExpandToggle && (
              <button
                type="button"
                onClick={() => setExpanded((prev) => !prev)}
                data-testid={`agent-invocation-rationale-toggle-${invocation.id}`}
                className="font-eyebrow text-amber hover:underline underline-offset-4"
              >
                {expanded ? 'Show less' : 'Show more'}
              </button>
            )}
          </div>
        ) : (
          <span className="font-eyebrow text-ink-subtle">—</span>
        )}
      </DataCell>

      {/* "Executed" badge — true only when the decision actually
          mutated the simulated trade book (BUY / SELL / MODIFY_STRATEGY
          plus LIVE mode). HOLD, NEEDS_HUMAN, INVOCATION_FAILED, MOCK
          rows: always false. */}
      <DataCell hideOnMobile>
        {invocation.decision_executed ? (
          <span
            className="inline-flex items-center bg-gain-soft text-gain px-2 py-1 rounded-editorial font-eyebrow"
            data-testid={`agent-invocation-executed-${invocation.id}`}
            title="The simulated trade book was mutated."
          >
            Executed
          </span>
        ) : (
          <span
            className="font-eyebrow text-ink-subtle"
            data-testid={`agent-invocation-not-executed-${invocation.id}`}
          >
            —
          </span>
        )}
      </DataCell>

      {/* Latency — zero for MOCK rows; agent round-trip in ms for LIVE. */}
      <DataCell tone="muted" align="right" numeric hideOnMobile>
        <span
          className="font-tabular"
          data-testid={`agent-invocation-latency-${invocation.id}`}
        >
          {invocation.latency_ms}ms
        </span>
      </DataCell>
    </DataRow>
  )
}
