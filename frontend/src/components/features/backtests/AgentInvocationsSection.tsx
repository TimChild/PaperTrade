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
 * Pagination: a single "Load more" button when `has_more === true`,
 * mirroring the simplest of the existing list patterns. The hook
 * re-fetches with `limit*N` so the resulting render is one contiguous
 * list, not a page-by-page swap.
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
import { formatDate } from '@/utils/formatters'
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
  // Track the current top of the requested window. Initial PAGE_SIZE
  // rows; "Load more" grows by PAGE_SIZE each press. The grown window
  // is the single TanStack Query key the hook uses — no manual array
  // concatenation needed.
  const [limit, setLimit] = useState(PAGE_SIZE)

  // The result page already gates this section on
  // `agentInvocationMode !== 'none'`, but the prop is plumbed through
  // anyway so the component is self-contained in tests.
  const enabled = agentInvocationMode !== 'none'

  const { data, isLoading, error } = useBacktestAgentInvocations(
    backtestId,
    { limit, offset: 0 },
    { enabled }
  )

  if (!enabled) {
    // Defensive — the parent page should never render us in NONE mode.
    return null
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const hasMore = data?.has_more ?? false

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

      {isLoading && (
        <div data-testid="agent-invocations-loading" className="mt-6 py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {error && !isLoading && (
        <div
          data-testid="agent-invocations-error"
          className="mt-6 rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-center"
        >
          <p className="text-body-md text-ink">
            Failed to load agent invocations. Please try again.
          </p>
        </div>
      )}

      {!isLoading && !error && items.length === 0 && (
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

      {!isLoading && !error && items.length > 0 && (
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

          {hasMore && (
            <div className="mt-4 flex justify-center">
              <Button
                type="button"
                variant="secondary"
                data-testid="agent-invocations-load-more"
                onClick={() => setLimit((current) => current + PAGE_SIZE)}
              >
                Load more
              </Button>
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

function InvocationRow({ invocation }: InvocationRowProps): React.JSX.Element {
  const [expanded, setExpanded] = useState(false)
  const showExpandToggle = invocation.rationale.length > RATIONALE_PREVIEW_CHARS
  const visibleRationale =
    expanded || !showExpandToggle
      ? invocation.rationale
      : invocation.rationale.slice(0, RATIONALE_PREVIEW_CHARS) + '…'

  return (
    <DataRow testId={`agent-invocation-row-${invocation.id}`}>
      {/* Simulated date — the in-simulation calendar day. Not wall-clock. */}
      <DataCell tone="muted" emphasis="primary">
        <span
          className="font-tabular"
          data-testid={`agent-invocation-sim-date-${invocation.id}`}
        >
          {formatDate(invocation.simulated_date, 'short')}
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
