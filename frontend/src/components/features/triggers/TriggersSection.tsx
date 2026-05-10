/**
 * TriggersSection — embedded section on the activation detail page.
 *
 * Shows the list of triggers attached to one activation as a hairline data
 * table, plus an "Attach trigger" CTA that opens the create dialog. Each
 * row exposes pause/resume, edit, and delete affordances inline; the
 * fire-log view lives on a separate route (`/triggers/:id/fires`).
 *
 * Empty state mirrors the editorial pattern from the rest of the app
 * (eyebrow + serif heading + amber CTA).
 *
 * Per Phase F design Q3, MANUALLY_DISABLED is terminal — its row gets a
 * "Recreate" CTA (which opens the create dialog with that trigger's
 * config prefilled is a future enhancement; for now it just opens an
 * empty form). The row also hides pause/edit because PATCH would 422 on
 * a terminal-state trigger.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataRow,
  DataCell,
  DataHeaderCell,
} from '@/components/ui/DataRow'
import { TriggerStatusBadge } from './TriggerStatusBadge'
import { CreateTriggerDialog } from './CreateTriggerDialog'
import { EditTriggerDialog } from './EditTriggerDialog'
import {
  useTriggers,
  useUpdateTrigger,
  useDeleteTrigger,
} from '@/hooks/useTriggers'
import { formatRelativeTime } from '@/utils/formatters'
import {
  formatConditionSummary,
  formatCooldown,
} from '@/utils/triggerFormatters'
import type { TriggerResponse, TriggerStatus } from '@/services/api/types'

interface TriggersSectionProps {
  activationId: string
}

const TERMINAL_STATUSES: ReadonlySet<TriggerStatus> = new Set([
  'EXPIRED',
  'MANUALLY_DISABLED',
])

function truncate(text: string, max: number): string {
  if (text.length <= max) return text
  return text.slice(0, max - 1) + '…'
}

export function TriggersSection({
  activationId,
}: TriggersSectionProps): React.JSX.Element {
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<TriggerResponse | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<TriggerResponse | null>(null)

  const { data: triggersPage, isLoading, error } = useTriggers(activationId)
  const updateTrigger = useUpdateTrigger()
  const deleteTrigger = useDeleteTrigger()

  const triggers = triggersPage?.items ?? []

  const handlePauseResume = (trigger: TriggerResponse): void => {
    const nextStatus: 'ACTIVE' | 'PAUSED' =
      trigger.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE'
    updateTrigger.mutate(
      { triggerId: trigger.id, body: { status: nextStatus } },
      {
        onSuccess: () => {
          toast.success(
            nextStatus === 'PAUSED' ? 'Trigger paused' : 'Trigger resumed'
          )
        },
        onError: () => {
          toast.error('Failed to update trigger status')
        },
      }
    )
  }

  const handleDeleteConfirm = (): void => {
    if (deleteTarget === null) return
    const target = deleteTarget
    deleteTrigger.mutate(target.id, {
      onSuccess: () => {
        toast.success('Trigger expired')
        setDeleteTarget(null)
      },
      onError: () => {
        toast.error('Failed to expire trigger')
      },
    })
  }

  return (
    <section
      className="mt-8 reveal"
      style={{ ['--reveal-delay' as string]: '180ms' }}
      data-testid="activation-triggers-section"
    >
      <SectionHeader
        eyebrow="Reactive"
        title="Triggers"
        size="sm"
        description="When a condition fires, the platform wakes an agent with the portfolio context and the prompt below. The agent returns a decision and the platform executes it (subject to daily caps)."
        trailing={
          <Button
            data-testid="trigger-attach-btn"
            onClick={() => setShowCreate(true)}
            size="sm"
          >
            Attach trigger
          </Button>
        }
        withRule
      />

      {isLoading && (
        <div data-testid="triggers-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {error && !isLoading && (
        <div
          data-testid="triggers-error"
          className="rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-center"
        >
          <p className="text-body-md text-ink">
            Failed to load triggers. Please try again.
          </p>
        </div>
      )}

      {!isLoading && !error && triggers.length === 0 && (
        <EmptyState
          eyebrow="No triggers"
          title="Attach a trigger to make this activation reactive"
          description="Today the activation runs on its daily schedule. With a trigger attached, the platform also wakes an agent when a condition fires — drawdown thresholds, volatility spikes, or earnings proximity."
          action={
            <Button
              data-testid="trigger-empty-attach-btn"
              onClick={() => setShowCreate(true)}
            >
              Attach trigger
            </Button>
          }
        />
      )}

      {!isLoading && !error && triggers.length > 0 && (
        <DataTable testId="triggers-table">
          <DataTableHead>
            <DataHeaderCell>Status</DataHeaderCell>
            <DataHeaderCell>Condition</DataHeaderCell>
            <DataHeaderCell hideOnMobile>Cooldown</DataHeaderCell>
            <DataHeaderCell hideUntilMd>Agent prompt</DataHeaderCell>
            <DataHeaderCell hideOnMobile>Last fired</DataHeaderCell>
            <DataHeaderCell align="right">Actions</DataHeaderCell>
          </DataTableHead>
          <DataTableBody>
            {triggers.map((t) => {
              const isTerminal = TERMINAL_STATUSES.has(t.status)
              const isDisabled = t.status === 'MANUALLY_DISABLED'
              return (
                <DataRow
                  key={t.id}
                  testId={`trigger-list-row-${t.id}`}
                  interactive
                >
                  <DataCell>
                    <TriggerStatusBadge status={t.status} />
                  </DataCell>
                  <DataCell emphasis="primary">
                    <span className="block max-w-[18rem] truncate">
                      {formatConditionSummary(
                        t.condition_type,
                        t.condition_params
                      )}
                    </span>
                  </DataCell>
                  <DataCell tone="muted" hideOnMobile numeric>
                    {formatCooldown(t.cooldown_seconds)}
                  </DataCell>
                  <DataCell tone="muted" hideUntilMd className="max-w-[20rem]">
                    <span
                      className="block truncate"
                      title={t.agent_prompt}
                      data-testid={`trigger-list-prompt-${t.id}`}
                    >
                      {truncate(t.agent_prompt, 80)}
                    </span>
                  </DataCell>
                  <DataCell tone="muted" hideOnMobile numeric>
                    {t.last_fired_at
                      ? formatRelativeTime(t.last_fired_at)
                      : '—'}
                  </DataCell>
                  <DataCell align="right">
                    <div className="flex justify-end gap-2">
                      <Link
                        to={`/triggers/${t.id}/fires`}
                        data-testid={`trigger-view-fires-btn-${t.id}`}
                      >
                        <Button variant="ghost" size="sm">
                          View fires
                        </Button>
                      </Link>
                      {!isTerminal && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handlePauseResume(t)}
                          data-testid={
                            t.status === 'ACTIVE'
                              ? `trigger-pause-btn-${t.id}`
                              : `trigger-resume-btn-${t.id}`
                          }
                          disabled={updateTrigger.isPending}
                        >
                          {t.status === 'ACTIVE' ? 'Pause' : 'Resume'}
                        </Button>
                      )}
                      {!isTerminal && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditTarget(t)}
                          data-testid={`trigger-edit-btn-${t.id}`}
                        >
                          Edit
                        </Button>
                      )}
                      {isDisabled && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowCreate(true)}
                          data-testid={`trigger-recreate-btn-${t.id}`}
                          title="MANUALLY_DISABLED is terminal — open the attach dialog to recreate."
                        >
                          Recreate
                        </Button>
                      )}
                      {!isTerminal && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteTarget(t)}
                          data-testid={`trigger-delete-btn-${t.id}`}
                          className="hover:text-loss"
                        >
                          Delete
                        </Button>
                      )}
                    </div>
                  </DataCell>
                </DataRow>
              )
            })}
          </DataTableBody>
        </DataTable>
      )}

      <CreateTriggerDialog
        isOpen={showCreate}
        activationId={activationId}
        onClose={() => setShowCreate(false)}
      />

      {/* `key={editTarget.id}` so each edit re-initialises the form via mount,
          rather than syncing via useEffect (frontend conventions doc). */}
      {editTarget !== null && (
        <EditTriggerDialog
          key={editTarget.id}
          trigger={editTarget}
          onClose={() => setEditTarget(null)}
        />
      )}

      <ConfirmDialog
        isOpen={deleteTarget !== null}
        title="Expire this trigger?"
        message="Past fires stay in the audit log; the trigger won't fire again. This cannot be undone."
        confirmLabel="Expire trigger"
        variant="danger"
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
        isLoading={deleteTrigger.isPending}
      />
    </section>
  )
}
