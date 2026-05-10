/**
 * Trigger fire log page — Phase G-1.
 *
 * Dedicated view of one trigger's fire history. Reached from the "View
 * fires" action on the activation detail page.
 *
 * Layout:
 *
 *   - Back link to the parent activation detail.
 *   - Hero: eyebrow + condition summary headline + status badge.
 *   - Caption: trigger metadata (cooldown, last_fired_at, created_at).
 *   - Fire log table: one row per `TriggerFireRecord` (newest-first).
 *
 * Empty state explains the trigger is active but its condition hasn't been
 * met — the most common "no fires yet" interpretation.
 */
import { Link, useParams } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { Caption } from '@/components/ui/Caption'
import { Panel } from '@/components/ui/Panel'
import { EmptyState } from '@/components/ui/EmptyState'
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataRow,
  DataCell,
  DataHeaderCell,
} from '@/components/ui/DataRow'
import { TriggerStatusBadge } from '@/components/features/triggers/TriggerStatusBadge'
import { AgentDecisionBadge } from '@/components/features/triggers/AgentDecisionBadge'
import { useTrigger, useTriggerFires } from '@/hooks/useTriggers'
import { formatRelativeTime, formatDate } from '@/utils/formatters'
import {
  formatConditionSummary,
  formatCooldown,
  formatFireSnapshot,
} from '@/utils/triggerFormatters'

function truncate(text: string, max: number): string {
  if (text.length <= max) return text
  return text.slice(0, max - 1) + '…'
}

export function TriggerFireLog(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const triggerId = id ?? ''

  const {
    data: trigger,
    isLoading: triggerLoading,
    error: triggerError,
  } = useTrigger(triggerId)

  const {
    data: firesPage,
    isLoading: firesLoading,
    error: firesError,
  } = useTriggerFires(triggerId, { limit: 50 })

  if (triggerLoading) {
    return (
      <PageFrame>
        <div data-testid="trigger-fire-log-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      </PageFrame>
    )
  }

  if (triggerError || !trigger) {
    const isNotFound =
      isAxiosError(triggerError) && triggerError.response?.status === 404
    return (
      <PageFrame>
        <BackLink activationId={null} />
        <div
          data-testid="trigger-fire-log-error"
          className="mt-6 rounded-editorial border border-hairline bg-loss-soft/40 p-6"
        >
          <Eyebrow tone="accent">{isNotFound ? 'Not found' : 'Error'}</Eyebrow>
          <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
            {isNotFound
              ? 'This trigger could not be found'
              : 'Failed to load this trigger'}
          </h2>
          <p className="mt-2 text-body-sm text-ink-muted">
            {isNotFound
              ? 'It may have been deleted. Try heading back to the activation.'
              : 'Try refreshing the page. If the problem persists the backend may be unreachable.'}
          </p>
        </div>
      </PageFrame>
    )
  }

  const conditionSummary = formatConditionSummary(
    trigger.condition_type,
    trigger.condition_params
  )
  const fires = firesPage?.items ?? []

  return (
    <PageFrame>
      <BackLink activationId={trigger.activation_id} />

      {/* Hero */}
      <header
        className="mt-4 reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="trigger-fire-log-page"
      >
        <Eyebrow>Trigger · Fire log</Eyebrow>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <h1
            className="font-display text-display-md sm:text-display-lg tracking-tight text-ink max-w-3xl"
            data-testid="trigger-fire-log-title"
          >
            {conditionSummary}
          </h1>
          <div className="flex-shrink-0">
            <TriggerStatusBadge status={trigger.status} />
          </div>
        </div>
        <Caption className="mt-3 block text-ink-subtle">
          Cooldown {formatCooldown(trigger.cooldown_seconds)}
          {' · '}
          {trigger.last_fired_at
            ? `Last fired ${formatRelativeTime(trigger.last_fired_at)}`
            : 'Never fired'}
          {' · Created '}
          {formatDate(trigger.created_at, true)}
        </Caption>
      </header>

      {/* Agent prompt */}
      <section
        className="mt-8 reveal"
        style={{ ['--reveal-delay' as string]: '60ms' }}
      >
        <Panel>
          <Eyebrow>Operator instruction</Eyebrow>
          <p
            className="mt-3 font-sans text-body-md text-ink whitespace-pre-wrap leading-relaxed"
            data-testid="trigger-fire-log-agent-prompt"
          >
            {trigger.agent_prompt}
          </p>
        </Panel>
      </section>

      {/* Fires */}
      <section
        className="mt-8 reveal"
        style={{ ['--reveal-delay' as string]: '120ms' }}
      >
        <Eyebrow>Fires</Eyebrow>
        <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
          {fires.length === 0
            ? 'No fires yet'
            : `${firesPage?.total ?? fires.length} fires`}
        </h2>

        {firesLoading && (
          <div data-testid="trigger-fires-loading" className="mt-4 py-12">
            <LoadingSpinner size="lg" />
          </div>
        )}

        {firesError && !firesLoading && (
          <div
            data-testid="trigger-fires-error"
            className="mt-4 rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-center"
          >
            <p className="text-body-md text-ink">
              Failed to load fires. Please try again.
            </p>
          </div>
        )}

        {!firesLoading && !firesError && fires.length === 0 && (
          <div data-testid="trigger-fires-empty">
            <EmptyState
              eyebrow="No fires yet"
              title="The trigger is waiting"
              description="The trigger is active but its condition hasn't been met yet. The platform evaluates conditions on a market-hours cadence."
            />
          </div>
        )}

        {!firesLoading && !firesError && fires.length > 0 && (
          <div className="mt-5">
            <DataTable testId="trigger-fires-table">
              <DataTableHead>
                <DataHeaderCell>Time</DataHeaderCell>
                <DataHeaderCell>Decision</DataHeaderCell>
                <DataHeaderCell hideOnMobile>Snapshot</DataHeaderCell>
                <DataHeaderCell hideUntilMd>Rationale</DataHeaderCell>
                <DataHeaderCell hideOnMobile>Trade</DataHeaderCell>
                <DataHeaderCell align="right" hideOnMobile>
                  Latency
                </DataHeaderCell>
              </DataTableHead>
              <DataTableBody>
                {fires.map((f) => (
                  <DataRow
                    key={f.id}
                    testId={`trigger-fire-row-${f.id}`}
                    interactive
                  >
                    <DataCell tone="muted" emphasis="primary">
                      <span title={formatDate(f.fired_at, true)}>
                        {formatRelativeTime(f.fired_at)}
                      </span>
                    </DataCell>
                    <DataCell>
                      <AgentDecisionBadge decision={f.agent_response} />
                    </DataCell>
                    <DataCell tone="muted" hideOnMobile>
                      <span
                        className="font-tabular text-body-sm"
                        data-testid={`trigger-fire-snapshot-${f.id}`}
                      >
                        {formatFireSnapshot(f)}
                      </span>
                    </DataCell>
                    <DataCell
                      tone="muted"
                      hideUntilMd
                      className="max-w-[20rem]"
                    >
                      <span
                        className="block truncate"
                        title={f.agent_response_raw}
                        data-testid={`trigger-fire-rationale-${f.id}`}
                      >
                        {truncate(f.agent_response_raw, 80) || '—'}
                      </span>
                    </DataCell>
                    <DataCell tone="muted" hideOnMobile>
                      {f.resulting_trade_id ? (
                        <span
                          className="font-tabular text-body-sm text-ink"
                          data-testid={`trigger-fire-trade-${f.id}`}
                        >
                          {f.resulting_trade_id.slice(0, 8)}
                        </span>
                      ) : f.resulting_exploration_task_id ? (
                        <Link
                          to={`/exploration-tasks/${f.resulting_exploration_task_id}`}
                          className="font-tabular text-body-sm text-amber underline-offset-4 hover:underline"
                          data-testid={`trigger-fire-task-${f.id}`}
                        >
                          task
                        </Link>
                      ) : (
                        '—'
                      )}
                    </DataCell>
                    <DataCell tone="muted" align="right" numeric hideOnMobile>
                      {f.latency_ms}ms
                    </DataCell>
                  </DataRow>
                ))}
              </DataTableBody>
            </DataTable>
          </div>
        )}
      </section>
    </PageFrame>
  )
}

function BackLink({
  activationId,
}: {
  activationId: string | null
}): React.JSX.Element {
  return (
    <Link
      to={activationId ? `/activations/${activationId}` : '/activations'}
      data-testid="trigger-fire-log-back-link"
      className="font-eyebrow text-ink-muted hover:text-amber"
    >
      ← Back to activation
    </Link>
  )
}

function PageFrame({
  children,
}: {
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div className="min-h-screen bg-canvas">
      <div className="mx-auto max-w-[1240px] px-5 sm:px-8 lg:px-12 py-8 sm:py-12 lg:py-16">
        {children}
      </div>
    </div>
  )
}
